import multiprocessing

# Количество рабочих процессов
workers = multiprocessing.cpu_count() * 2 + 1

# Тип рабочих процессов
worker_class = 'sync'

# Время ожидания для рабочих процессов
timeout = 120

# Максимальное количество запросов на рабочий процесс
max_requests = 1000
max_requests_jitter = 50

# Привязка к сокету
bind = 'unix:/run/django-shop.sock'

# Логирование
accesslog = '/var/log/django-shop/access.log'
errorlog = '/var/log/django-shop/error.log'
loglevel = 'info'

# Пользователь и группа для запуска
user = 'www-data'
group = 'www-data'

# Предзагрузка приложения
preload_app = True

# Перезапуск при сбое
graceful_timeout = 30 