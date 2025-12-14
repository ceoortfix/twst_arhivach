"""
Модуль для асинхронной загрузки медиа-файлов
"""

import os
import io
import asyncio
from typing import List
from dataclasses import dataclass

import aiohttp
import aiofiles
from tqdm import tqdm

import config
from parser import MediaFile


# Расширения изображений, которые можно конвертировать в JPG
CONVERTIBLE_EXTENSIONS = ['.png', '.webp', '.bmp']


@dataclass
class DownloadStats:
    """Статистика загрузки"""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    converted: int = 0
    retried: int = 0
    total_bytes: int = 0
    
    def __str__(self):
        result = (
            f"Статистика загрузки:\n"
            f"  Всего файлов: {self.total}\n"
            f"  Загружено: {self.completed}\n"
            f"  Ошибок: {self.failed}\n"
            f"  Пропущено (уже существуют): {self.skipped}\n"
            f"  Загружено байт: {self._format_bytes(self.total_bytes)}"
        )
        if self.converted > 0:
            result += f"\n  Конвертировано в JPG: {self.converted}"
        if self.retried > 0:
            result += f"\n  Повторных попыток: {self.retried}"
        return result
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Форматировать размер в человекочитаемый вид"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if bytes_count < 1024:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024
        return f"{bytes_count:.2f} ТБ"


def convert_image_to_jpg(content: bytes, quality: int = 85) -> bytes:
    """
    Конвертировать изображение в JPG
    
    Args:
        content: Бинарные данные изображения
        quality: Качество JPG (1-100)
        
    Returns:
        Бинарные данные JPG изображения
    """
    try:
        from PIL import Image
        
        # Открываем изображение из байтов
        img = Image.open(io.BytesIO(content))
        
        # Конвертируем в RGB если нужно (для PNG с прозрачностью)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаём белый фон для прозрачных изображений
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Сохраняем в JPG
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except Exception:
        # Если конвертация не удалась, возвращаем исходные данные
        return content


def get_jpg_filename(filename: str) -> str:
    """Получить имя файла с расширением .jpg"""
    base, ext = os.path.splitext(filename)
    if ext.lower() in CONVERTIBLE_EXTENSIONS:
        return base + '.jpg'
    return filename


def should_convert(filename: str) -> bool:
    """Проверить, нужно ли конвертировать файл"""
    if not config.CONVERT_IMAGES_TO_JPG:
        return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in CONVERTIBLE_EXTENSIONS


def file_exists(output_dir: str, filename: str) -> bool:
    """
    Проверить существует ли файл (с учётом возможной конвертации)
    """
    # Проверяем оригинальное имя
    if os.path.exists(os.path.join(output_dir, filename)):
        return True
    
    # Проверяем сконвертированное имя
    if should_convert(filename):
        jpg_filename = get_jpg_filename(filename)
        if os.path.exists(os.path.join(output_dir, jpg_filename)):
            return True
    
    # Проверяем обратное - если конвертация выключена, но файл был сконвертирован ранее
    base, ext = os.path.splitext(filename)
    if ext.lower() in CONVERTIBLE_EXTENSIONS:
        if os.path.exists(os.path.join(output_dir, base + '.jpg')):
            return True
    
    return False


class MediaDownloader:
    """Асинхронный загрузчик медиа-файлов"""
    
    def __init__(self, max_concurrent: int = None, max_retries: int = None):
        self.max_concurrent = max_concurrent or config.MAX_CONCURRENT_DOWNLOADS
        self.max_retries = max_retries or config.DOWNLOAD_RETRIES
        self.stats = DownloadStats()
        self.semaphore = None
        self.session = None
    
    async def _init_session(self):
        """Инициализировать HTTP-сессию"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': config.USER_AGENT}
            )
    
    async def _close_session(self):
        """Закрыть HTTP-сессию"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _download_with_retry(self, url: str) -> bytes:
        """
        Загрузить файл с повторными попытками при ошибке
        
        Returns:
            Байты файла или None при ошибке
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    elif response.status == 404:
                        # Файл не найден, повторять бессмысленно
                        return None
                    else:
                        last_error = f"HTTP {response.status}"
            except asyncio.TimeoutError:
                last_error = "Timeout"
            except aiohttp.ClientError as e:
                last_error = str(e)
            except Exception as e:
                last_error = str(e)
            
            # Если это не последняя попытка, ждём перед повтором
            if attempt < self.max_retries - 1:
                self.stats.retried += 1
                await asyncio.sleep(1 * (attempt + 1))  # Увеличивающаяся задержка
        
        return None
    
    async def _download_file(self, media: MediaFile, output_dir: str, pbar: tqdm) -> bool:
        """
        Загрузить один файл
        
        Returns:
            True если файл успешно загружен или уже существует
        """
        # Проверяем, существует ли файл (с учётом конвертации)
        if file_exists(output_dir, media.filename):
            self.stats.skipped += 1
            pbar.update(1)
            return True
        
        # Определяем финальное имя файла
        if should_convert(media.filename):
            final_filename = get_jpg_filename(media.filename)
        else:
            final_filename = media.filename
        
        filepath = os.path.join(output_dir, final_filename)
        
        async with self.semaphore:
            content = await self._download_with_retry(media.url)
            
            if content is None:
                self.stats.failed += 1
                pbar.update(1)
                return False
            
            try:
                # Конвертируем в JPG если нужно
                if should_convert(media.filename):
                    content = await asyncio.get_event_loop().run_in_executor(
                        None, convert_image_to_jpg, content, config.JPG_QUALITY
                    )
                    self.stats.converted += 1
                
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(content)
                
                self.stats.completed += 1
                self.stats.total_bytes += len(content)
                pbar.update(1)
                return True
            except Exception:
                self.stats.failed += 1
                pbar.update(1)
                return False
    
    async def download_media_files(self, media_files: List[MediaFile], output_dir: str) -> DownloadStats:
        """
        Загрузить список медиа-файлов
        
        Args:
            media_files: Список файлов для загрузки
            output_dir: Директория для сохранения
            
        Returns:
            Статистика загрузки
        """
        # Создаем директорию если её нет
        os.makedirs(output_dir, exist_ok=True)
        
        # Сбрасываем статистику
        self.stats = DownloadStats(total=len(media_files))
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        await self._init_session()
        
        try:
            # Создаем прогресс-бар
            with tqdm(total=len(media_files), desc="Загрузка медиа", unit="файл") as pbar:
                # Создаем задачи для всех файлов
                tasks = [
                    self._download_file(media, output_dir, pbar)
                    for media in media_files
                ]
                
                # Выполняем все задачи
                await asyncio.gather(*tasks)
        finally:
            await self._close_session()
        
        return self.stats


def download_media_sync(media_files: List[MediaFile], output_dir: str, max_concurrent: int = None) -> DownloadStats:
    """
    Синхронная обёртка для загрузки медиа
    
    Args:
        media_files: Список файлов для загрузки
        output_dir: Директория для сохранения
        max_concurrent: Максимальное количество одновременных загрузок
        
    Returns:
        Статистика загрузки
    """
    downloader = MediaDownloader(max_concurrent)
    return asyncio.run(downloader.download_media_files(media_files, output_dir))
