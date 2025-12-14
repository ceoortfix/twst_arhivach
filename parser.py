"""
Модуль для парсинга страниц Архивача
"""

import re
import os
import time
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Tuple
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

import config


@dataclass
class ThreadInfo:
    """Информация о треде"""
    url: str
    title: str
    date: str
    thread_id: str = ""
    posts_count: int = 0


@dataclass
class MediaFile:
    """Информация о медиа-файле"""
    url: str
    filename: str
    file_type: str  # 'image', 'video', 'other'


@dataclass
class ResourceFile:
    """Информация о ресурсном файле (CSS, JS)"""
    url: str
    filename: str
    resource_type: str  # 'css', 'js'


# Расширения для конвертации в JPG
CONVERTIBLE_EXTENSIONS = ['.png', '.webp', '.bmp']


def get_html_filename(filename: str) -> str:
    """
    Получить имя файла для использования в HTML
    Если конвертация включена, меняет расширение на .jpg
    """
    if not config.CONVERT_IMAGES_TO_JPG:
        return filename
    
    base, ext = os.path.splitext(filename)
    if ext.lower() in CONVERTIBLE_EXTENSIONS:
        return base + '.jpg'
    return filename


class ArhivachParser:
    """Парсер страниц Архивача"""
    
    def __init__(self, domain: str = None):
        self.domain = domain or config.ARHIVACH_DOMAIN
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT
        })
    
    def _get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Получить и распарсить страницу"""
        try:
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except requests.RequestException as e:
            print(f"Ошибка при загрузке страницы {url}: {e}")
            return None
    
    def _get_raw_page(self, url: str) -> Optional[str]:
        """Получить сырой HTML страницы"""
        try:
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Ошибка при загрузке страницы {url}: {e}")
            return None
    
    def _normalize_url(self, url: str) -> str:
        """Нормализовать URL"""
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urljoin(self.domain, url)
        elif not url.startswith('http'):
            return urljoin(self.domain, url)
        return url
    
    def _extract_thread_id(self, url: str) -> str:
        """Извлечь ID треда из URL"""
        match = re.search(r'/thread/(\d+)', url)
        return match.group(1) if match else ""
    
    def _parse_post_time_to_folder(self, date_str: str, thread_id: str) -> str:
        """
        Преобразовать дату из post_time в формат для имени папки
        Формат входной даты: "20/01/25 Пнд 16:33:14"
        Формат выходной: "20.01.25_1122323"
        """
        # Ищем паттерн ДД/ММ/ГГ
        match = re.search(r'(\d{2})/(\d{2})/(\d{2})', date_str)
        if match:
            day, month, year = match.groups()
            return f"{day}.{month}.{year}_{thread_id}"
        
        # Если формат не распознан, используем только ID
        return f"thread_{thread_id}"
    
    def get_threads_from_tag_page(self, tag_id: int, offset: int = 0) -> Tuple[List[ThreadInfo], int]:
        """
        Получить список тредов со страницы тега
        
        Пагинация на arhivach.vc работает через offset:
        - Страница 1: /?tags=14905
        - Страница 2: /index/25/?tags=14905
        - Страница 3: /index/50/?tags=14905
        
        Args:
            tag_id: ID тега
            offset: Смещение (0, 25, 50, ...)
            
        Returns:
            Tuple[List[ThreadInfo], int]: Список тредов и общее количество страниц
        """
        # Формируем URL с учётом offset
        if offset == 0:
            url = f"{self.domain}/?tags={tag_id}"
        else:
            url = f"{self.domain}/index/{offset}/?tags={tag_id}"
        
        soup = self._get_page(url)
        if not soup:
            return [], 0
        
        threads = []
        
        # Ищем таблицу с тредами
        thread_table = soup.find('table', class_='thread_list') or soup.find('table')
        
        if thread_table:
            rows = thread_table.find_all('tr')
            for row in rows:
                # Пропускаем заголовок таблицы
                if row.find('th'):
                    continue
                
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # Ищем ссылку на тред
                    link = row.find('a', href=re.compile(r'/thread/\d+'))
                    if link:
                        thread_url = self._normalize_url(link.get('href', ''))
                        thread_title = link.get_text(strip=True)[:100]
                        thread_id = self._extract_thread_id(thread_url)
                        
                        # Ищем дату в последней ячейке
                        date_cell = cells[-1]
                        date_str = date_cell.get_text(strip=True)
                        
                        threads.append(ThreadInfo(
                            url=thread_url,
                            title=thread_title,
                            date=date_str,
                            thread_id=thread_id
                        ))
        
        # Определяем количество страниц из пагинации
        # Ищем все ссылки с паттерном /index/OFFSET/?tags=
        total_pages = 1
        
        # Ищем все ссылки на странице
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Ищем паттерн /index/NUMBER/?tags=TAG_ID
            if f'tags={tag_id}' in href:
                # Паттерн /index/OFFSET/
                offset_match = re.search(r'/index/(\d+)/\?', href)
                if offset_match:
                    page_offset = int(offset_match.group(1))
                    # Страница = offset / 25 + 1
                    page_num = (page_offset // 25) + 1
                    total_pages = max(total_pages, page_num)
                
                # Также проверяем текст ссылки (номер страницы напрямую)
                link_text = link.get_text(strip=True)
                if link_text.isdigit():
                    total_pages = max(total_pages, int(link_text))
        
        return threads, total_pages
    
    def get_all_threads_from_tag(self, tag_id: int, max_pages: int = None) -> List[ThreadInfo]:
        """
        Получить все треды по тегу со всех страниц
        
        Args:
            tag_id: ID тега
            max_pages: Максимальное количество страниц для обработки (None = все)
        """
        all_threads = []
        
        # Получаем первую страницу (offset=0)
        threads, total_pages = self.get_threads_from_tag_page(tag_id, offset=0)
        all_threads.extend(threads)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"Найдено страниц: {total_pages}")
        
        # Получаем остальные страницы
        # Страница 2 = offset 25, страница 3 = offset 50, и т.д.
        for page in range(2, total_pages + 1):
            offset = (page - 1) * 25
            print(f"Загрузка страницы {page}/{total_pages}...")
            time.sleep(config.PAGE_REQUEST_DELAY)
            threads, _ = self.get_threads_from_tag_page(tag_id, offset=offset)
            all_threads.extend(threads)
        
        return all_threads
    
    def parse_thread(self, thread_url: str) -> Tuple[Optional[str], List[MediaFile], str, str, List[ResourceFile]]:
        """
        Парсинг отдельного треда
        
        Returns:
            Tuple[html_content, media_files, thread_date, thread_id, resource_files]
        """
        soup = self._get_page(thread_url)
        if not soup:
            return None, [], "", "", []
        
        media_files = []
        resource_files = []
        thread_id = self._extract_thread_id(thread_url)
        
        # Получаем дату треда из span.post_time первого поста (ОП-поста)
        thread_date = ""
        post_time_elem = soup.find('span', class_='post_time')
        if post_time_elem:
            thread_date = post_time_elem.get_text(strip=True)
        
        # Собираем CSS файлы
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href:
                full_url = self._normalize_url(href)
                filename = self._extract_resource_filename(full_url, 'css')
                resource_files.append(ResourceFile(url=full_url, filename=filename, resource_type='css'))
                # Заменяем путь на локальный
                link['href'] = f"resources/{filename}"
        
        # Собираем JS файлы
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if src:
                full_url = self._normalize_url(src)
                filename = self._extract_resource_filename(full_url, 'js')
                resource_files.append(ResourceFile(url=full_url, filename=filename, resource_type='js'))
                # Заменяем путь на локальный
                script['src'] = f"resources/{filename}"
        
        # Множество имён файлов оригиналов для быстрой проверки
        original_filenames = set()
        
        # Сначала собираем оригиналы из ссылок <a> (не превью!)
        # Оригиналы имеют путь /storage/X/XX/HASH.ext (не /storage/t/)
        # Обрабатываем ссылки на изображения и видео
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/storage/' in href and '/storage/t/' not in href:
                # Нормализуем URL (может быть i.arhivach.vc для видео)
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = self._normalize_url(href)
                
                filename = self._extract_filename(full_url)
                file_type = self._get_file_type(filename)
                
                if file_type:
                    # Проверяем что это не дубликат
                    if not any(m.url == full_url for m in media_files):
                        media_files.append(MediaFile(url=full_url, filename=filename, file_type=file_type))
                    
                    # Запоминаем имя файла оригинала
                    original_filenames.add(filename)
                    
                    # Заменяем путь на локальный
                    if file_type == 'image':
                        html_filename = get_html_filename(filename)
                    else:
                        html_filename = filename  # Видео не конвертируем
                    link['href'] = f"media/{html_filename}"
        
        # Создаём маппинг хеш -> имя файла для видео (для превью)
        video_hash_to_filename = {}
        for media in media_files:
            if media.file_type == 'video':
                # Хеш это имя файла без расширения
                hash_name = media.filename.rsplit('.', 1)[0]
                video_hash_to_filename[hash_name] = media.filename
        
        # Теперь обрабатываем все <img> - заменяем пути
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            if src and '/storage/' in src:
                # Пропускаем служебные изображения
                if any(x in src for x in ['favicon', 'logo', 'icon', 'avatar', 'button']):
                    continue
                
                # Извлекаем имя файла
                filename = self._extract_filename(src)
                
                # Если это превью (/storage/t/)
                if '/storage/t/' in src:
                    # Проверяем если это превью видео (.thumb)
                    if filename.endswith('.thumb'):
                        hash_name = filename.replace('.thumb', '')
                        if hash_name in video_hash_to_filename:
                            # Скачиваем превью видео тоже
                            full_url = self._normalize_url(src)
                            thumb_filename = f"{hash_name}_thumb.jpg"
                            if not any(m.filename == thumb_filename for m in media_files):
                                media_files.append(MediaFile(url=full_url, filename=thumb_filename, file_type='image'))
                            if img.get('src'):
                                img['src'] = f"media/{thumb_filename}"
                            if img.get('data-src'):
                                img['data-src'] = f"media/{thumb_filename}"
                            continue
                    
                    # Обычное превью изображения
                    if filename in original_filenames:
                        # Заменяем превью на локальный путь к оригиналу
                        html_filename = get_html_filename(filename)
                        if img.get('src'):
                            img['src'] = f"media/{html_filename}"
                        if img.get('data-src'):
                            img['data-src'] = f"media/{html_filename}"
                else:
                    # Это не превью, добавляем в список для скачивания если ещё нет
                    full_url = self._normalize_url(src)
                    file_type = self._get_file_type(filename)
                    if file_type and not any(m.url == full_url for m in media_files):
                        media_files.append(MediaFile(url=full_url, filename=filename, file_type=file_type))
                        original_filenames.add(filename)
                    
                    html_filename = get_html_filename(filename)
                    if img.get('src'):
                        img['src'] = f"media/{html_filename}"
                    if img.get('data-src'):
                        img['data-src'] = f"media/{html_filename}"
        
        # Находим видео из <video> тегов
        for video in soup.find_all('video'):
            src = video.get('src', '')
            if not src:
                source = video.find('source')
                if source:
                    src = source.get('src', '')
            if src and '/storage/' in src:
                full_url = self._normalize_url(src)
                filename = self._extract_filename(full_url)
                file_type = self._get_file_type(filename)
                if file_type and not any(m.url == full_url for m in media_files):
                    media_files.append(MediaFile(url=full_url, filename=filename, file_type=file_type))
                    if video.get('src'):
                        video['src'] = f"media/{filename}"
                    source = video.find('source')
                    if source and source.get('src'):
                        source['src'] = f"media/{filename}"
        
        # Находим видео из onclick событий (expand_local)
        # Формат: expand_local('16_1','https://i.arhivach.vc/storage/d/1a/filename.mp4','0','0',event)
        html_str = str(soup)
        video_urls = re.findall(r"expand_local\([^,]+,'(https?://[^']+\.(?:mp4|webm|mov))'", html_str, re.IGNORECASE)
        for video_url in video_urls:
            filename = video_url.split('/')[-1]
            if not any(m.filename == filename for m in media_files):
                media_files.append(MediaFile(url=video_url, filename=filename, file_type='video'))
        
        # ===== ОЧИСТКА HTML ОТ ВНЕШНИХ РЕСУРСОВ =====
        
        # Удаляем все скрипты с Google Analytics, Yandex и другой аналитикой
        for script in soup.find_all('script'):
            src = script.get('src', '')
            script_text = script.string or ''
            
            # Удаляем внешние скрипты аналитики
            if src and ('google' in src or 'yandex' in src or 'counter' in src or 'analytics' in src or 'cloudflare' in src):
                script.decompose()
                continue
            
            # Удаляем inline Google Analytics
            if 'GoogleAnalyticsObject' in script_text or 'google-analytics' in script_text or "ga('create'" in script_text:
                script.decompose()
                continue
        
        # Удаляем iframe
        for iframe in soup.find_all('iframe'):
            iframe.decompose()
        
        # Удаляем favicon ссылку (вызывает ошибку 404)
        for link in soup.find_all('link', rel='shortcut icon'):
            link.decompose()
        for link in soup.find_all('link', rel='icon'):
            link.decompose()
        
        # Удаляем canonical и onion-location (внешние ссылки)
        for meta in soup.find_all('meta', {'http-equiv': 'onion-location'}):
            meta.decompose()
        for link in soup.find_all('link', rel='canonical'):
            link.decompose()
        
        # Удаляем base tag
        head = soup.find('head')
        if head:
            existing_base = head.find('base')
            if existing_base:
                existing_base.decompose()
        
        # Получаем HTML как строку для дополнительных замен
        html_content = str(soup)
        
        # Блокируем AJAX запросы - заменяем URL на пустой
        html_content = re.sub(r"var ajax_url\s*=\s*'[^']*'", "var ajax_url = ''", html_content)
        
        # Заменяем ссылки на i.arhivach.vc в onclick на локальные пути
        # expand_local('16_1','https://i.arhivach.vc/storage/...',...)
        def replace_expand_local(match):
            full_url = match.group(2)
            filename = full_url.split('/')[-1]
            return f"{match.group(1)}media/{filename}{match.group(3)}"
        
        html_content = re.sub(
            r"(expand_local\([^,]+,')https?://[^']+/storage/[^']+/([^']+)('[^)]*\))",
            lambda m: f"{m.group(1)}media/{m.group(2)}{m.group(3)}",
            html_content
        )
        
        return html_content, media_files, thread_date, thread_id, resource_files
    
    def get_folder_name(self, thread_date: str, thread_id: str) -> str:
        """
        Получить имя папки для треда
        Формат: ДД.ММ.ГГ_ID (например: 20.01.25_1122323)
        """
        return self._parse_post_time_to_folder(thread_date, thread_id)
    
    def _extract_filename(self, url: str) -> str:
        """Извлечь имя файла из URL"""
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split('/')[-1]
        # Удаляем параметры запроса из имени файла
        filename = filename.split('?')[0]
        # Если имя файла пустое или невалидное, генерируем
        if not filename or len(filename) < 3:
            import hashlib
            filename = hashlib.md5(url.encode()).hexdigest()[:16]
        return filename
    
    def _extract_resource_filename(self, url: str, resource_type: str) -> str:
        """Извлечь имя файла для ресурса (CSS/JS)"""
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split('/')[-1]
        filename = filename.split('?')[0]
        
        # Если имя пустое, генерируем на основе хеша
        if not filename or len(filename) < 3:
            import hashlib
            hash_name = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"{hash_name}.{resource_type}"
        
        # Добавляем расширение если его нет
        if not filename.endswith(f'.{resource_type}'):
            if '.' not in filename:
                filename = f"{filename}.{resource_type}"
        
        return filename
    
    def _get_file_type(self, filename: str) -> Optional[str]:
        """Определить тип файла по расширению"""
        filename_lower = filename.lower()
        
        for ext in config.MEDIA_EXTENSIONS['images']:
            if filename_lower.endswith(ext):
                return 'image'
        
        for ext in config.MEDIA_EXTENSIONS['videos']:
            if filename_lower.endswith(ext):
                return 'video'
        
        for ext in config.MEDIA_EXTENSIONS['other']:
            if filename_lower.endswith(ext):
                return 'other'
        
        return None
    
    def download_resource(self, url: str, filepath: str) -> bool:
        """Скачать ресурсный файл (CSS/JS)"""
        try:
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Создаём директорию если нужно
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            return False
