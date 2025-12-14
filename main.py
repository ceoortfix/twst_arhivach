"""
twst.downloader [module] - Модуль загрузки тредов с Архивача
Интерактивный интерфейс с управлением через меню
"""

import os
import re
import sys
import json
import subprocess
import time
import importlib.metadata
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime

# Список требуемых библиотек с версиями
REQUIRED_PACKAGES = {
    'requests': '2.31.0',
    'beautifulsoup4': '4.12.2',
    'lxml': '4.9.3',
    'aiohttp': '3.9.1',
    'aiofiles': '23.2.1',
    'tqdm': '4.66.1',
    'packaging': '23.2',
    'Pillow': '10.1.0'
}

# Маппинг имён пакетов для импорта
IMPORT_NAMES = {
    'beautifulsoup4': 'bs4',
    'aiofiles': 'aiofiles',
    'aiohttp': 'aiohttp',
    'requests': 'requests',
    'lxml': 'lxml',
    'tqdm': 'tqdm',
    'packaging': 'packaging',
    'Pillow': 'PIL'
}

# Файл для хранения списка мониторинга
MONITOR_FILE = "monitor_list.json"
MAX_MONITOR_ITEMS = 20


@dataclass
class PackageInfo:
    """Информация о пакете"""
    name: str
    required_version: str
    installed_version: Optional[str] = None
    is_installed: bool = False
    needs_update: bool = False


@dataclass
class MonitorItem:
    """Элемент списка мониторинга"""
    item_type: str  # 'thread' или 'tag'
    url: str
    item_id: str
    name: str
    last_check: str = ""
    last_posts_count: int = 0
    is_active: bool = True


def clear_screen():
    """Очистить экран консоли"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Вывести заголовок приложения"""
    print("\n" + "=" * 60)
    print("   twst.downloader [module]")
    print("   Модуль загрузки тредов")
    print("=" * 60)


def print_separator():
    """Вывести разделитель"""
    print("-" * 60)


def get_package_version(package_name: str) -> Optional[str]:
    """Получить установленную версию пакета"""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def check_package(package_name: str, required_version: str) -> PackageInfo:
    """Проверить состояние пакета"""
    installed_version = get_package_version(package_name)
    is_installed = installed_version is not None
    
    needs_update = False
    if is_installed and installed_version:
        try:
            from packaging import version
            needs_update = version.parse(installed_version) < version.parse(required_version)
        except ImportError:
            needs_update = installed_version != required_version
    
    return PackageInfo(
        name=package_name,
        required_version=required_version,
        installed_version=installed_version,
        is_installed=is_installed,
        needs_update=needs_update
    )


def check_all_packages() -> Dict[str, PackageInfo]:
    """Проверить все необходимые пакеты"""
    packages = {}
    for name, version in REQUIRED_PACKAGES.items():
        packages[name] = check_package(name, version)
    return packages


def install_package(package_name: str, version: str = None) -> bool:
    """Установить или обновить пакет"""
    try:
        package_spec = f"{package_name}=={version}" if version else package_name
        print(f"  Установка {package_spec}...")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', package_spec],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  [OK] {package_name} успешно установлен")
            return True
        else:
            print(f"  [ОШИБКА] Ошибка установки: {result.stderr}")
            return False
    except Exception as e:
        print(f"  [ОШИБКА] {e}")
        return False


def ensure_dependencies() -> bool:
    """Проверить и установить недостающие зависимости"""
    print("\n[*] Проверка зависимостей...")
    print_separator()
    
    packages = check_all_packages()
    missing = [p for p in packages.values() if not p.is_installed]
    
    if not missing:
        print("[OK] Все зависимости установлены")
        return True
    
    print(f"\n[!] Найдено {len(missing)} недостающих пакетов:")
    for pkg in missing:
        print(f"  - {pkg.name} (требуется {pkg.required_version})")
    
    print("\n")
    choice = input("Установить недостающие пакеты? (y/n): ").strip().lower()
    if choice != 'y':
        print("[X] Установка отменена. Приложение не может работать без зависимостей.")
        return False
    
    print()
    success = True
    for pkg in missing:
        if not install_package(pkg.name, pkg.required_version):
            success = False
    
    return success


def show_packages_status():
    """Показать статус всех пакетов"""
    clear_screen()
    print_header()
    print("\n[*] СТАТУС БИБЛИОТЕК")
    print_separator()
    
    packages = check_all_packages()
    
    print(f"\n{'Пакет':<20} {'Установлена':<15} {'Требуется':<15} {'Статус':<15}")
    print("-" * 65)
    
    for pkg in packages.values():
        installed = pkg.installed_version or "-"
        status = "[OK]"
        if not pkg.is_installed:
            status = "[X] Не установлен"
        elif pkg.needs_update:
            status = "[!] Обновить"
        
        print(f"{pkg.name:<20} {installed:<15} {pkg.required_version:<15} {status:<15}")
    
    print_separator()
    input("\nНажмите Enter для возврата в меню...")


def update_packages_menu():
    """Меню обновления пакетов"""
    while True:
        clear_screen()
        print_header()
        print("\n[*] ОБНОВЛЕНИЕ БИБЛИОТЕК")
        print_separator()
        
        packages = check_all_packages()
        pkg_list = list(packages.values())
        
        print("\nВыберите пакет для обновления:\n")
        
        for i, pkg in enumerate(pkg_list, 1):
            installed = pkg.installed_version or "не установлен"
            status_icon = "[OK]" if pkg.is_installed and not pkg.needs_update else "[!]"
            print(f"  {i}. {status_icon} {pkg.name:<20} ({installed} -> {pkg.required_version})")
        
        print()
        print(f"  {len(pkg_list) + 1}. [*] Обновить ВСЕ пакеты")
        print("  0. [<] Назад в главное меню")
        
        print_separator()
        choice = input("\nВаш выбор: ").strip()
        
        if choice == '0':
            break
        elif choice == str(len(pkg_list) + 1):
            print("\n[*] Обновление всех пакетов...")
            for pkg in pkg_list:
                install_package(pkg.name, pkg.required_version)
            input("\nНажмите Enter для продолжения...")
        elif choice.isdigit() and 1 <= int(choice) <= len(pkg_list):
            pkg = pkg_list[int(choice) - 1]
            print(f"\n[*] Обновление {pkg.name}...")
            install_package(pkg.name, pkg.required_version)
            input("\nНажмите Enter для продолжения...")


def show_help():
    """Показать справку"""
    clear_screen()
    print_header()
    print("\n[?] СПРАВКА")
    print_separator()
    
    help_text = """
twst.downloader [module] - Модуль загрузки тредов с Архивача

==============================================================

[*] ОСНОВНОЙ ФУНКЦИОНАЛ:

  1. Загрузка отдельного треда
     - Укажите полный URL треда (например: https://arhivach.vc/thread/1277766/)
     - Скрипт сохранит HTML страницы и все медиа-файлы
     - Папка называется по дате ОП-поста: ДД.ММ.ГГ_ID
      
  2. Загрузка тредов по тегу
     - Укажите ID тега или URL страницы тега
     - Можно ограничить количество страниц для обработки
     - Скрипт обработает пагинацию автоматически
      
  3. Мониторинг тредов/тегов
     - Добавьте треды или теги в список мониторинга (до 20)
     - Скрипт периодически проверяет обновления
     - Докачивает новые посты и медиа

==============================================================

[*] СТРУКТУРА СОХРАНЁННЫХ ДАННЫХ:

  downloads/
  +-- tag_14905/                    # Папка тега
  |   +-- 20.01.25_1122323/         # Папка треда (дата_ID)
  |   |   +-- thread.html           # HTML страницы
  |   |   +-- media/                # Медиа-файлы
  |   +-- ...
  +-- 20.01.25_1277766/             # Отдельный тред

==============================================================

[*] ПОДДЕРЖИВАЕМЫЕ МЕДИА-ФАЙЛЫ:

  - Изображения: .jpg, .jpeg, .png, .gif, .webp, .bmp
  - Видео: .mp4, .webm, .mov, .avi
  - Прочее: .pdf, .zip, .rar, .7z
"""
    print(help_text)
    input("\nНажмите Enter для возврата в меню...")


def show_settings():
    """Меню настроек"""
    import config
    
    while True:
        clear_screen()
        print_header()
        print("\n[*] НАСТРОЙКИ")
        print_separator()
        
        convert_status = "ВКЛ" if config.CONVERT_IMAGES_TO_JPG else "ВЫКЛ"
        
        print(f"""
Текущие настройки:

  1. Домен Архивача:          {config.ARHIVACH_DOMAIN}
  2. Папка загрузок:          {config.OUTPUT_DIR}
  3. Одновременных загрузок:  {config.MAX_CONCURRENT_DOWNLOADS} (1-30)
  4. Таймаут запросов:        {config.REQUEST_TIMEOUT} сек.
  5. Задержка между страниц.: {config.PAGE_REQUEST_DELAY} сек.
  6. Конвертация в JPG:       {convert_status} (качество: {config.JPG_QUALITY}%)
  7. Повторов при ошибке:     {config.DOWNLOAD_RETRIES} (1-30)
  
  0. Назад в главное меню
""")
        print_separator()
        choice = input("\nВыберите параметр для изменения (0-7): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            new_val = input(f"\nВведите новый домен [{config.ARHIVACH_DOMAIN}]: ").strip()
            if new_val:
                config.ARHIVACH_DOMAIN = new_val
                print("[OK] Домен изменён")
        elif choice == '2':
            new_val = input(f"\nВведите путь к папке [{config.OUTPUT_DIR}]: ").strip()
            if new_val:
                config.OUTPUT_DIR = new_val
                print("[OK] Папка изменена")
        elif choice == '3':
            new_val = input(f"\nВведите количество (1-30) [{config.MAX_CONCURRENT_DOWNLOADS}]: ").strip()
            if new_val.isdigit() and 1 <= int(new_val) <= 30:
                config.MAX_CONCURRENT_DOWNLOADS = int(new_val)
                print("[OK] Значение изменено")
            else:
                print("[X] Значение должно быть от 1 до 30")
        elif choice == '4':
            new_val = input(f"\nВведите таймаут в секундах [{config.REQUEST_TIMEOUT}]: ").strip()
            if new_val.isdigit() and int(new_val) > 0:
                config.REQUEST_TIMEOUT = int(new_val)
                print("[OK] Таймаут изменён")
        elif choice == '5':
            new_val = input(f"\nВведите задержку в секундах [{config.PAGE_REQUEST_DELAY}]: ").strip()
            try:
                if float(new_val) >= 0:
                    config.PAGE_REQUEST_DELAY = float(new_val)
                    print("[OK] Задержка изменена")
            except ValueError:
                pass
        elif choice == '6':
            print(f"\nКонвертация изображений в JPG: {'ВКЛ' if config.CONVERT_IMAGES_TO_JPG else 'ВЫКЛ'}")
            print("  1. Включить")
            print("  2. Выключить")
            print("  3. Изменить качество JPG")
            sub_choice = input("\nВаш выбор: ").strip()
            if sub_choice == '1':
                config.CONVERT_IMAGES_TO_JPG = True
                print("[OK] Конвертация включена")
            elif sub_choice == '2':
                config.CONVERT_IMAGES_TO_JPG = False
                print("[OK] Конвертация выключена")
            elif sub_choice == '3':
                new_val = input(f"\nВведите качество JPG (1-100) [{config.JPG_QUALITY}]: ").strip()
                if new_val.isdigit() and 1 <= int(new_val) <= 100:
                    config.JPG_QUALITY = int(new_val)
                    print("[OK] Качество изменено")
                else:
                    print("[X] Значение должно быть от 1 до 100")
        elif choice == '7':
            new_val = input(f"\nВведите количество повторов (1-30) [{config.DOWNLOAD_RETRIES}]: ").strip()
            if new_val.isdigit() and 1 <= int(new_val) <= 30:
                config.DOWNLOAD_RETRIES = int(new_val)
                print("[OK] Количество повторов изменено")
            else:
                print("[X] Значение должно быть от 1 до 30")
        
        if choice in ['1', '2', '3', '4', '5', '6', '7']:
            input("\nНажмите Enter для продолжения...")


def sanitize_folder_name(name: str) -> str:
    """Очистить имя папки от недопустимых символов"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip(' .')
    return name[:200] if name else 'thread'


def download_single_thread_interactive():
    """Интерактивная загрузка отдельного треда"""
    import config
    from parser import ArhivachParser
    from downloader import download_media_sync
    
    clear_screen()
    print_header()
    print("\n[>] ЗАГРУЗКА ОТДЕЛЬНОГО ТРЕДА")
    print_separator()
    
    thread_url = input("\nВведите URL треда (или 'q' для отмены): ").strip()
    
    if thread_url.lower() == 'q':
        return
    
    if not thread_url.startswith('http'):
        print("[X] Некорректный URL. URL должен начинаться с http:// или https://")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\n[*] Загрузка треда: {thread_url}")
    print_separator()
    
    parser = ArhivachParser(domain=config.ARHIVACH_DOMAIN)
    
    # Парсим тред
    print("[*] Парсинг страницы треда...")
    html_content, media_files, thread_date, thread_id, resource_files = parser.parse_thread(thread_url)
    
    if not html_content:
        print("[X] Ошибка: не удалось загрузить тред")
        input("\nНажмите Enter для продолжения...")
        return
    
    # Формируем имя папки: ДД.ММ.ГГ_ID
    folder_name = parser.get_folder_name(thread_date, thread_id)
    folder_name = sanitize_folder_name(folder_name)
    thread_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    media_dir = os.path.join(thread_dir, 'media')
    resources_dir = os.path.join(thread_dir, 'resources')
    
    os.makedirs(thread_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)
    
    # Скачиваем ресурсы (CSS/JS)
    if resource_files:
        print(f"[*] Загрузка ресурсов ({len(resource_files)} файлов)...")
        for res in resource_files:
            res_path = os.path.join(resources_dir, res.filename)
            parser.download_resource(res.url, res_path)
    
    # Сохраняем HTML
    html_path = os.path.join(thread_dir, 'thread.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[OK] HTML сохранён: {html_path}")
    
    # Статистика медиа
    print_separator()
    print("\n[*] СТАТИСТИКА МЕДИА-ФАЙЛОВ:")
    images = sum(1 for m in media_files if m.file_type == 'image')
    videos = sum(1 for m in media_files if m.file_type == 'video')
    other = sum(1 for m in media_files if m.file_type == 'other')
    
    print(f"  Изображений: {images}")
    print(f"  Видео: {videos}")
    print(f"  Прочих файлов: {other}")
    print(f"  Всего: {len(media_files)}")
    
    if media_files:
        print_separator()
        print("\n[>] Загрузка медиа-файлов...\n")
        stats = download_media_sync(media_files, media_dir)
        
        print_separator()
        print("\n[*] РЕЗУЛЬТАТ ЗАГРУЗКИ:")
        print(f"  Загружено: {stats.completed}")
        print(f"  Пропущено (уже есть): {stats.skipped}")
        print(f"  Ошибок: {stats.failed}")
        print(f"  Загружено данных: {stats._format_bytes(stats.total_bytes)}")
    
    print_separator()
    print(f"\n[OK] Тред сохранён в: {thread_dir}")
    input("\nНажмите Enter для возврата в меню...")


def download_by_tag_interactive():
    """Интерактивная загрузка тредов по тегу"""
    import config
    from parser import ArhivachParser
    from downloader import download_media_sync
    
    clear_screen()
    print_header()
    print("\n[>] ЗАГРУЗКА ТРЕДОВ ПО ТЕГУ")
    print_separator()
    
    tag_input = input("\nВведите ID тега или URL (или 'q' для отмены): ").strip()
    
    if tag_input.lower() == 'q':
        return
    
    # Извлекаем ID тега
    tag_id = None
    if tag_input.isdigit():
        tag_id = int(tag_input)
    else:
        match = re.search(r'tags=(\d+)', tag_input)
        if match:
            tag_id = int(match.group(1))
    
    if tag_id is None:
        print("[X] Не удалось определить ID тега")
        input("\nНажмите Enter для продолжения...")
        return
    
    # Запрашиваем лимит страниц
    max_pages_input = input("\nМакс. количество страниц (Enter = все): ").strip()
    max_pages = int(max_pages_input) if max_pages_input.isdigit() else None
    
    # Выбор направления загрузки
    print("\nПорядок загрузки:")
    print("  1. С начала (старые -> новые)")
    print("  2. С конца (новые -> старые)")
    order_input = input("\nВыберите порядок (1/2, Enter = 1): ").strip()
    reverse_order = order_input == '2'
    
    print(f"\n[*] Загрузка тредов по тегу: {tag_id}")
    if max_pages:
        print(f"   Ограничение: {max_pages} страниц")
    print(f"   Порядок: {'новые -> старые' if reverse_order else 'старые -> новые'}")
    print_separator()
    
    parser = ArhivachParser(domain=config.ARHIVACH_DOMAIN)
    
    # Получаем список тредов
    print("\n[*] Получение списка тредов...")
    threads = parser.get_all_threads_from_tag(tag_id, max_pages)
    
    if not threads:
        print("[X] Треды не найдены")
        input("\nНажмите Enter для продолжения...")
        return
    
    # Реверсируем если нужно (по умолчанию список идёт от старых к новым)
    if reverse_order:
        threads = list(reversed(threads))
    
    print(f"\n[OK] Найдено тредов: {len(threads)}")
    
    confirm = input("\nНачать загрузку? (y/n): ").strip().lower()
    if confirm != 'y':
        print("[X] Загрузка отменена")
        input("\nНажмите Enter для продолжения...")
        return
    
    # Создаем папку для тега
    tag_dir = os.path.join(config.OUTPUT_DIR, f"tag_{tag_id}")
    os.makedirs(tag_dir, exist_ok=True)
    
    # Статистика
    successful = 0
    failed = 0
    total_media = 0
    total_bytes = 0
    
    print_separator()
    print("\n[>] ЗАГРУЗКА ТРЕДОВ\n")
    
    for i, thread in enumerate(threads, 1):
        print(f"\n[{i}/{len(threads)}] {thread.title[:50]}...")
        
        try:
            html_content, media_files, thread_date, thread_id, resource_files = parser.parse_thread(thread.url)
            
            if not html_content:
                print("  [X] Ошибка загрузки")
                failed += 1
                continue
            
            # Формируем имя папки: ДД.ММ.ГГ_ID
            folder_name = parser.get_folder_name(thread_date, thread_id)
            folder_name = sanitize_folder_name(folder_name)
            thread_dir = os.path.join(tag_dir, folder_name)
            media_dir = os.path.join(thread_dir, 'media')
            resources_dir = os.path.join(thread_dir, 'resources')
            
            os.makedirs(thread_dir, exist_ok=True)
            os.makedirs(media_dir, exist_ok=True)
            os.makedirs(resources_dir, exist_ok=True)
            
            # Скачиваем ресурсы (CSS/JS)
            for res in resource_files:
                res_path = os.path.join(resources_dir, res.filename)
                parser.download_resource(res.url, res_path)
            
            # Сохраняем HTML
            html_path = os.path.join(thread_dir, 'thread.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Загружаем медиа
            if media_files:
                stats = download_media_sync(media_files, media_dir)
                total_media += stats.completed
                total_bytes += stats.total_bytes
                print(f"  [OK] HTML + {stats.completed} медиа-файлов")
            else:
                print("  [OK] HTML сохранён (медиа нет)")
            
            successful += 1
            
        except Exception as e:
            print(f"  [X] Ошибка: {e}")
            failed += 1
        
        # Задержка между тредами
        if i < len(threads):
            time.sleep(config.PAGE_REQUEST_DELAY)
    
    # Итоговая статистика
    print_separator()
    print("\n[*] ИТОГОВАЯ СТАТИСТИКА:")
    print(f"  Успешно загружено: {successful}/{len(threads)} тредов")
    print(f"  Ошибок: {failed}")
    print(f"  Всего медиа-файлов: {total_media}")
    print(f"  Загружено данных: {format_bytes(total_bytes)}")
    print(f"\n[OK] Результаты сохранены в: {tag_dir}")
    
    input("\nНажмите Enter для возврата в меню...")


def format_bytes(bytes_count: int) -> str:
    """Форматировать размер в человекочитаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if bytes_count < 1024:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.2f} ТБ"


# ==================== МОНИТОРИНГ ====================

def load_monitor_list() -> List[MonitorItem]:
    """Загрузить список мониторинга из файла"""
    if not os.path.exists(MONITOR_FILE):
        return []
    try:
        with open(MONITOR_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [MonitorItem(**item) for item in data]
    except Exception:
        return []


def save_monitor_list(items: List[MonitorItem]):
    """Сохранить список мониторинга в файл"""
    try:
        with open(MONITOR_FILE, 'w', encoding='utf-8') as f:
            json.dump([asdict(item) for item in items], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[X] Ошибка сохранения списка: {e}")


def add_to_monitor():
    """Добавить тред или тег в мониторинг"""
    import config
    from parser import ArhivachParser
    
    clear_screen()
    print_header()
    print("\n[+] ДОБАВИТЬ В МОНИТОРИНГ")
    print_separator()
    
    items = load_monitor_list()
    
    if len(items) >= MAX_MONITOR_ITEMS:
        print(f"[X] Достигнут лимит мониторинга ({MAX_MONITOR_ITEMS} элементов)")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\nТекущее количество: {len(items)}/{MAX_MONITOR_ITEMS}")
    print("\nТип добавляемого элемента:")
    print("  1. Тред")
    print("  2. Тег")
    print("  0. Отмена")
    
    choice = input("\nВаш выбор: ").strip()
    
    if choice == '0':
        return
    
    if choice == '1':
        url = input("\nВведите URL треда: ").strip()
        if not url.startswith('http'):
            print("[X] Некорректный URL")
            input("\nНажмите Enter для продолжения...")
            return
        
        # Извлекаем ID треда
        match = re.search(r'/thread/(\d+)', url)
        if not match:
            print("[X] Не удалось определить ID треда")
            input("\nНажмите Enter для продолжения...")
            return
        
        thread_id = match.group(1)
        
        # Проверяем, не добавлен ли уже
        if any(i.item_id == thread_id and i.item_type == 'thread' for i in items):
            print("[X] Этот тред уже в списке мониторинга")
            input("\nНажмите Enter для продолжения...")
            return
        
        # Получаем название треда
        parser = ArhivachParser(domain=config.ARHIVACH_DOMAIN)
        html_content, _, thread_date, _, _ = parser.parse_thread(url)
        
        if html_content:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            title_elem = soup.find('h1', class_='post_subject')
            name = title_elem.get_text(strip=True)[:50] if title_elem else f"Тред {thread_id}"
        else:
            name = f"Тред {thread_id}"
        
        item = MonitorItem(
            item_type='thread',
            url=url,
            item_id=thread_id,
            name=name,
            last_check=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        items.append(item)
        save_monitor_list(items)
        print(f"[OK] Тред добавлен: {name}")
        
    elif choice == '2':
        tag_input = input("\nВведите ID тега или URL: ").strip()
        
        tag_id = None
        if tag_input.isdigit():
            tag_id = tag_input
        else:
            match = re.search(r'tags=(\d+)', tag_input)
            if match:
                tag_id = match.group(1)
        
        if not tag_id:
            print("[X] Не удалось определить ID тега")
            input("\nНажмите Enter для продолжения...")
            return
        
        # Проверяем, не добавлен ли уже
        if any(i.item_id == tag_id and i.item_type == 'tag' for i in items):
            print("[X] Этот тег уже в списке мониторинга")
            input("\nНажмите Enter для продолжения...")
            return
        
        import config
        url = f"{config.ARHIVACH_DOMAIN}/?tags={tag_id}"
        name = input("Введите название для тега (или Enter для ID): ").strip()
        if not name:
            name = f"Тег {tag_id}"
        
        item = MonitorItem(
            item_type='tag',
            url=url,
            item_id=tag_id,
            name=name,
            last_check=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        items.append(item)
        save_monitor_list(items)
        print(f"[OK] Тег добавлен: {name}")
    
    input("\nНажмите Enter для продолжения...")


def show_monitor_list():
    """Показать список мониторинга"""
    clear_screen()
    print_header()
    print("\n[*] СПИСОК МОНИТОРИНГА")
    print_separator()
    
    items = load_monitor_list()
    
    if not items:
        print("\nСписок мониторинга пуст.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\nВсего элементов: {len(items)}/{MAX_MONITOR_ITEMS}\n")
    print(f"{'#':<4} {'Тип':<8} {'Название':<30} {'Статус':<10} {'Посл. проверка':<20}")
    print("-" * 75)
    
    for i, item in enumerate(items, 1):
        item_type = "Тред" if item.item_type == 'thread' else "Тег"
        status = "[ON]" if item.is_active else "[OFF]"
        name = item.name[:28] + ".." if len(item.name) > 30 else item.name
        print(f"{i:<4} {item_type:<8} {name:<30} {status:<10} {item.last_check:<20}")
    
    print_separator()
    input("\nНажмите Enter для продолжения...")


def remove_from_monitor():
    """Удалить элемент из мониторинга"""
    clear_screen()
    print_header()
    print("\n[-] УДАЛИТЬ ИЗ МОНИТОРИНГА")
    print_separator()
    
    items = load_monitor_list()
    
    if not items:
        print("\nСписок мониторинга пуст.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nВыберите элемент для удаления:\n")
    
    for i, item in enumerate(items, 1):
        item_type = "Тред" if item.item_type == 'thread' else "Тег"
        print(f"  {i}. [{item_type}] {item.name}")
    
    print("\n  0. Отмена")
    
    choice = input("\nВаш выбор: ").strip()
    
    if choice == '0':
        return
    
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        idx = int(choice) - 1
        removed = items.pop(idx)
        save_monitor_list(items)
        print(f"[OK] Удалено: {removed.name}")
    else:
        print("[X] Некорректный выбор")
    
    input("\nНажмите Enter для продолжения...")


def run_monitor_check():
    """Запустить проверку мониторинга"""
    import config
    from parser import ArhivachParser
    from downloader import download_media_sync
    
    clear_screen()
    print_header()
    print("\n[>] ПРОВЕРКА ОБНОВЛЕНИЙ")
    print_separator()
    
    items = load_monitor_list()
    active_items = [i for i in items if i.is_active]
    
    if not active_items:
        print("\nНет активных элементов для мониторинга.")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\nПроверка {len(active_items)} элементов...\n")
    
    parser = ArhivachParser(domain=config.ARHIVACH_DOMAIN)
    
    for item in active_items:
        print(f"\n[*] Проверка: {item.name}")
        
        if item.item_type == 'thread':
            # Проверяем тред
            html_content, media_files, thread_date, thread_id, resource_files = parser.parse_thread(item.url)
            
            if html_content:
                folder_name = parser.get_folder_name(thread_date, thread_id)
                folder_name = sanitize_folder_name(folder_name)
                thread_dir = os.path.join(config.OUTPUT_DIR, folder_name)
                media_dir = os.path.join(thread_dir, 'media')
                resources_dir = os.path.join(thread_dir, 'resources')
                
                os.makedirs(thread_dir, exist_ok=True)
                os.makedirs(media_dir, exist_ok=True)
                os.makedirs(resources_dir, exist_ok=True)
                
                # Скачиваем ресурсы
                for res in resource_files:
                    res_path = os.path.join(resources_dir, res.filename)
                    if not os.path.exists(res_path):
                        parser.download_resource(res.url, res_path)
                
                # Сохраняем HTML
                html_path = os.path.join(thread_dir, 'thread.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Загружаем новые медиа
                if media_files:
                    stats = download_media_sync(media_files, media_dir)
                    if stats.completed > 0:
                        print(f"    [+] Загружено {stats.completed} новых файлов")
                    else:
                        print("    [=] Нет новых файлов")
                
                item.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                print("    [X] Ошибка загрузки")
        
        elif item.item_type == 'tag':
            # Проверяем тег - загружаем первую страницу (offset=0)
            threads, _ = parser.get_threads_from_tag_page(int(item.item_id), offset=0)
            
            if threads:
                # Создаем папку для тега
                tag_dir = os.path.join(config.OUTPUT_DIR, f"tag_{item.item_id}")
                os.makedirs(tag_dir, exist_ok=True)
                
                new_threads = 0
                for thread in threads[:5]:  # Проверяем только последние 5 тредов
                    html_content, media_files, thread_date, thread_id, resource_files = parser.parse_thread(thread.url)
                    
                    if html_content:
                        folder_name = parser.get_folder_name(thread_date, thread_id)
                        folder_name = sanitize_folder_name(folder_name)
                        thread_dir = os.path.join(tag_dir, folder_name)
                        
                        # Проверяем, новый ли это тред
                        if not os.path.exists(thread_dir):
                            new_threads += 1
                            media_dir = os.path.join(thread_dir, 'media')
                            resources_dir = os.path.join(thread_dir, 'resources')
                            os.makedirs(thread_dir, exist_ok=True)
                            os.makedirs(media_dir, exist_ok=True)
                            os.makedirs(resources_dir, exist_ok=True)
                            
                            # Скачиваем ресурсы
                            for res in resource_files:
                                res_path = os.path.join(resources_dir, res.filename)
                                parser.download_resource(res.url, res_path)
                            
                            html_path = os.path.join(thread_dir, 'thread.html')
                            with open(html_path, 'w', encoding='utf-8') as f:
                                f.write(html_content)
                            
                            if media_files:
                                download_media_sync(media_files, media_dir)
                    
                    time.sleep(0.5)
                
                if new_threads > 0:
                    print(f"    [+] Найдено {new_threads} новых тредов")
                else:
                    print("    [=] Нет новых тредов")
                
                item.last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                print("    [X] Ошибка загрузки")
        
        time.sleep(config.PAGE_REQUEST_DELAY)
    
    # Сохраняем обновлённый список
    save_monitor_list(items)
    
    print_separator()
    print("\n[OK] Проверка завершена")
    input("\nНажмите Enter для продолжения...")


def monitor_menu():
    """Меню мониторинга"""
    while True:
        clear_screen()
        print_header()
        
        items = load_monitor_list()
        active_count = sum(1 for i in items if i.is_active)
        
        print(f"\n[*] МОНИТОРИНГ ({len(items)}/{MAX_MONITOR_ITEMS}, активных: {active_count})")
        print_separator()
        
        print("""
  1. Показать список мониторинга
  2. Добавить тред/тег
  3. Удалить из мониторинга
  4. Запустить проверку обновлений
  
  0. [<] Назад в главное меню
""")
        print_separator()
        choice = input("\nВаш выбор: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            show_monitor_list()
        elif choice == '2':
            add_to_monitor()
        elif choice == '3':
            remove_from_monitor()
        elif choice == '4':
            run_monitor_check()


def show_args_help():
    """Показать справку по аргументам командной строки"""
    clear_screen()
    print_header()
    print("\n[?] СПРАВКА ПО АРГУМЕНТАМ КОМАНДНОЙ СТРОКИ")
    print_separator()
    
    args_help = """
Приложение можно запускать с аргументами командной строки для автоматизации.

ОСНОВНЫЕ АРГУМЕНТЫ:

  --thread URL, -t URL
      Загрузить отдельный тред по URL
      Пример: python main.py --thread https://arhivach.vc/thread/1277766/

  --tag TAG_ID, -g TAG_ID
      Загрузить все треды по ID тега или URL страницы тега
      Примеры:
        python main.py --tag 14905
        python main.py --tag https://arhivach.vc/?tags=14905

ДОПОЛНИТЕЛЬНЫЕ АРГУМЕНТЫ:

  --output DIR, -o DIR
      Директория для сохранения загрузок
      По умолчанию: downloads
      Пример: python main.py --tag 14905 --output ./my_downloads

  --max-pages N, -p N
      Максимальное количество страниц для обработки (только с --tag)
      Пример: python main.py --tag 14905 --max-pages 5

  --domain URL, -d URL
      Изменить домен Архивача
      По умолчанию: https://arhivach.vc
      Пример: python main.py --tag 14905 --domain https://arhivach.xyz

  --concurrent N, -c N
      Количество одновременных загрузок медиа (1-30)
      По умолчанию: 5
      Пример: python main.py --thread URL --concurrent 10

  --help-args
      Показать эту справку

ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:

  # Загрузить один тред
  python main.py -t https://arhivach.vc/thread/1234567/
  
  # Загрузить первые 10 страниц тега
  python main.py -g 14905 -p 10 -o ./neuro_fap
  
  # Загрузить с большим количеством потоков
  python main.py -g 92 -c 15

"""
    print(args_help)
    input("\nНажмите Enter для возврата в меню...")


def main_menu():
    """Главное меню приложения"""
    while True:
        clear_screen()
        print_header()
        
        # Краткий статус зависимостей
        packages = check_all_packages()
        missing = sum(1 for p in packages.values() if not p.is_installed)
        outdated = sum(1 for p in packages.values() if p.is_installed and p.needs_update)
        
        # Статус мониторинга
        monitor_items = load_monitor_list()
        active_monitor = sum(1 for i in monitor_items if i.is_active)
        
        if missing:
            print(f"\n[!] Внимание: {missing} пакет(ов) не установлено!")
        elif outdated:
            print(f"\n[!] Доступны обновления: {outdated} пакет(ов)")
        else:
            print("\n[OK] Все зависимости в порядке")
        
        print(f"""
ГЛАВНОЕ МЕНЮ

  1. Загрузить отдельный тред
  2. Загрузить треды по тегу
  3. Мониторинг ({len(monitor_items)}/{MAX_MONITOR_ITEMS}, активных: {active_monitor})

  4. Настройки
  5. Статус библиотек
  6. Обновление библиотек

  7. Справка
  8. Справка по аргументам

  0. Выход
""")
        
        choice = input("Выберите действие (0-8): ").strip()
        
        if choice == '0':
            print("\nДо свидания!\n")
            sys.exit(0)
        elif choice == '1':
            if missing:
                print("\n[X] Сначала установите недостающие зависимости (пункт 6)")
                input("\nНажмите Enter для продолжения...")
            else:
                download_single_thread_interactive()
        elif choice == '2':
            if missing:
                print("\n[X] Сначала установите недостающие зависимости (пункт 6)")
                input("\nНажмите Enter для продолжения...")
            else:
                download_by_tag_interactive()
        elif choice == '3':
            if missing:
                print("\n[X] Сначала установите недостающие зависимости (пункт 6)")
                input("\nНажмите Enter для продолжения...")
            else:
                monitor_menu()
        elif choice == '4':
            show_settings()
        elif choice == '5':
            show_packages_status()
        elif choice == '6':
            update_packages_menu()
        elif choice == '7':
            show_help()
        elif choice == '8':
            show_args_help()


def parse_command_line():
    """Обработка аргументов командной строки"""
    import argparse
    import config
    from parser import ArhivachParser
    from downloader import download_media_sync
    
    parser = argparse.ArgumentParser(
        description='twst.downloader - Модуль загрузки тредов',
        add_help=False
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--thread', '-t', metavar='URL')
    group.add_argument('--tag', '-g', metavar='TAG_ID')
    
    parser.add_argument('--output', '-o', metavar='DIR', default=config.OUTPUT_DIR)
    parser.add_argument('--max-pages', '-p', type=int, metavar='N')
    parser.add_argument('--domain', '-d', metavar='URL', default=config.ARHIVACH_DOMAIN)
    parser.add_argument('--concurrent', '-c', type=int, metavar='N', default=config.MAX_CONCURRENT_DOWNLOADS)
    parser.add_argument('--help-args', action='store_true')
    
    args = parser.parse_args()
    
    if args.help_args:
        show_args_help()
        sys.exit(0)
    
    if args.thread or args.tag:
        # Проверяем зависимости
        if not ensure_dependencies():
            sys.exit(1)
        
        config.MAX_CONCURRENT_DOWNLOADS = min(30, max(1, args.concurrent))
        config.ARHIVACH_DOMAIN = args.domain
        config.OUTPUT_DIR = args.output
        
        arhivach_parser = ArhivachParser(domain=args.domain)
        os.makedirs(args.output, exist_ok=True)
        
        if args.thread:
            print(f"\n[*] Загрузка треда: {args.thread}")
            html_content, media_files, thread_date, thread_id, resource_files = arhivach_parser.parse_thread(args.thread)
            
            if not html_content:
                print("[X] Ошибка: не удалось загрузить тред")
                sys.exit(1)
            
            folder_name = arhivach_parser.get_folder_name(thread_date, thread_id)
            folder_name = sanitize_folder_name(folder_name)
            thread_dir = os.path.join(args.output, folder_name)
            media_dir = os.path.join(thread_dir, 'media')
            resources_dir = os.path.join(thread_dir, 'resources')
            
            os.makedirs(thread_dir, exist_ok=True)
            os.makedirs(media_dir, exist_ok=True)
            os.makedirs(resources_dir, exist_ok=True)
            
            # Скачиваем ресурсы
            for res in resource_files:
                res_path = os.path.join(resources_dir, res.filename)
                arhivach_parser.download_resource(res.url, res_path)
            
            html_path = os.path.join(thread_dir, 'thread.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            if media_files:
                stats = download_media_sync(media_files, media_dir)
                print(f"\n{stats}")
            
            print(f"\n[OK] Тред сохранён в: {thread_dir}")
        
        elif args.tag:
            tag_id = None
            if args.tag.isdigit():
                tag_id = int(args.tag)
            else:
                match = re.search(r'tags=(\d+)', args.tag)
                if match:
                    tag_id = int(match.group(1))
            
            if tag_id is None:
                print(f"[X] Не удалось определить ID тега из '{args.tag}'")
                sys.exit(1)
            
            print(f"\n[*] Загрузка тредов по тегу: {tag_id}")
            threads = arhivach_parser.get_all_threads_from_tag(tag_id, args.max_pages)
            
            if not threads:
                print("[X] Треды не найдены")
                sys.exit(1)
            
            tag_dir = os.path.join(args.output, f"tag_{tag_id}")
            os.makedirs(tag_dir, exist_ok=True)
            
            successful = 0
            for i, thread in enumerate(threads, 1):
                print(f"\n[{i}/{len(threads)}] {thread.title[:50]}...")
                
                try:
                    html_content, media_files, thread_date, thread_id, resource_files = arhivach_parser.parse_thread(thread.url)
                    
                    if html_content:
                        folder_name = arhivach_parser.get_folder_name(thread_date, thread_id)
                        folder_name = sanitize_folder_name(folder_name)
                        thread_dir = os.path.join(tag_dir, folder_name)
                        media_dir = os.path.join(thread_dir, 'media')
                        resources_dir = os.path.join(thread_dir, 'resources')
                        
                        os.makedirs(thread_dir, exist_ok=True)
                        os.makedirs(media_dir, exist_ok=True)
                        os.makedirs(resources_dir, exist_ok=True)
                        
                        # Скачиваем ресурсы
                        for res in resource_files:
                            res_path = os.path.join(resources_dir, res.filename)
                            arhivach_parser.download_resource(res.url, res_path)
                        
                        html_path = os.path.join(thread_dir, 'thread.html')
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        
                        if media_files:
                            download_media_sync(media_files, media_dir)
                        
                        successful += 1
                
                except Exception as e:
                    print(f"  [X] Ошибка: {e}")
                
                if i < len(threads):
                    time.sleep(config.PAGE_REQUEST_DELAY)
            
            print(f"\n[OK] Загружено: {successful}/{len(threads)} тредов")
            print(f"[OK] Результаты: {tag_dir}")
        
        sys.exit(0)
    
    return False


def main():
    """Точка входа"""
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        parse_command_line()
    
    # Проверяем зависимости при старте
    if not ensure_dependencies():
        sys.exit(1)
    
    # Запускаем интерактивное меню
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nДо свидания!\n")
        sys.exit(0)


if __name__ == '__main__':
    main()
