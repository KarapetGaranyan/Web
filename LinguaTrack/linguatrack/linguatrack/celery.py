import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguatrack.settings')

app = Celery('linguatrack')

# Настройки для Windows
if sys.platform == 'win32':
    app.conf.update(
        worker_pool='solo',  # Используем solo pool для Windows
        worker_concurrency=1,
        task_always_eager=False,
        broker_connection_retry_on_startup=True,
    )

app.config_from_object('django.conf:settings', namespace='CELERY')

# ИСПРАВЛЕНИЕ: Явно указываем где искать задачи
app.autodiscover_tasks(['telegram_bot', 'cards'])

# Альтернативный способ - автодискавери всех приложений Django
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Периодические задачи
app.conf.beat_schedule = {
    # Ежедневные напоминания в 18:00
    'daily-reminders': {
        'task': 'telegram_bot.tasks.send_daily_reminders',
        'schedule': crontab(hour=18, minute=0),
    },
    # Еженедельная статистика по воскресеньям в 20:00
    'weekly-stats': {
        'task': 'telegram_bot.tasks.send_weekly_stats',
        'schedule': crontab(hour=20, minute=0, day_of_week=0),
    },
    # Создание расписаний для новых карточек каждые 30 минут
    'create-schedules': {
        'task': 'cards.tasks.create_missing_schedules',
        'schedule': crontab(minute='*/30'),
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')