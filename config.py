"""
Конфигурация приложения для загрузки тредов с Архивача
"""

# Домен Архивача (можно изменить при необходимости)
ARHIVACH_DOMAIN = "https://arhivach.vc"

# Папка для сохранения загруженных тредов
OUTPUT_DIR = "downloads"

# Максимальное количество одновременных загрузок медиа-файлов (1-30)
MAX_CONCURRENT_DOWNLOADS = 5

# Таймаут для HTTP-запросов (в секундах)
REQUEST_TIMEOUT = 30

# Задержка между запросами страниц (в секундах)
PAGE_REQUEST_DELAY = 1.0

# Конвертировать изображения в JPG для экономии места (True/False)
CONVERT_IMAGES_TO_JPG = True

# Качество JPG при конвертации (1-100)
JPG_QUALITY = 85

# Количество повторных попыток загрузки при ошибке (1-30)
DOWNLOAD_RETRIES = 5

# User-Agent для запросов
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Расширения файлов для загрузки
MEDIA_EXTENSIONS = {
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
    'videos': ['.mp4', '.webm', '.mov', '.avi'],
    'other': ['.pdf', '.zip', '.rar', '.7z']
}


