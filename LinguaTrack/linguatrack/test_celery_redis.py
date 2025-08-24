# 1. Создайте файл test_celery_redis.py в корне проекта:

# !/usr/bin/env python
"""Тестирование Celery и Redis"""
import os
import django
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguatrack.settings')
django.setup()


def test_redis():
    """Проверка Redis подключения"""
    print("🔴 Тестирование Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)

        # Тестируем запись/чтение
        test_key = 'linguatrack_test'
        test_value = f'test_value_{datetime.now().timestamp()}'

        r.set(test_key, test_value)
        stored_value = r.get(test_key)

        if stored_value and stored_value.decode() == test_value:
            print("✅ Redis работает корректно")
            r.delete(test_key)  # Очищаем тестовые данные
            return True
        else:
            print("❌ Redis не сохраняет данные")
            return False

    except Exception as e:
        print(f"❌ Ошибка Redis: {e}")
        return False


def test_celery_basic():
    """Проверка базовой работы Celery"""
    print("\n⚙️ Тестирование Celery...")
    try:
        from celery import current_app

        # Проверяем статус Celery
        inspect = current_app.control.inspect()
        stats = inspect.stats()

        if stats:
            print("✅ Celery Worker активен")
            print(f"   Активных worker'ов: {len(stats)}")
            return True
        else:
            print("❌ Celery Worker не отвечает")
            return False

    except Exception as e:
        print(f"❌ Ошибка Celery: {e}")
        return False


def test_celery_task():
    """Проверка выполнения задач Celery"""
    print("\n🔧 Тестирование выполнения задач...")
    try:
        # Создаем тестовую задачу
        from celery import shared_task

        @shared_task
        def test_task(message):
            return f"Получено: {message} в {datetime.now()}"

        # Выполняем задачу синхронно (для теста)
        result = test_task.apply_async(args=['Тестовое сообщение'])

        # Ждем результат (максимум 10 секунд)
        try:
            task_result = result.get(timeout=10)
            print(f"✅ Задача выполнена: {task_result}")
            return True
        except Exception as e:
            print(f"❌ Задача не выполнилась: {e}")
            return False

    except Exception as e:
        print(f"❌ Ошибка выполнения задачи: {e}")
        return False


def test_scheduled_tasks():
    """Проверка планировщика задач"""
    print("\n⏰ Тестирование Celery Beat...")
    try:
        from celery import current_app

        # Проверяем активные периодические задачи
        inspect = current_app.control.inspect()
        scheduled = inspect.scheduled()

        if scheduled:
            print("✅ Celery Beat работает")
            total_tasks = sum(len(tasks) for tasks in scheduled.values())
            print(f"   Запланированных задач: {total_tasks}")
        else:
            print("⚠️ Celery Beat запущен, но нет активных задач")

        # Проверяем конфигурацию периодических задач
        beat_schedule = current_app.conf.beat_schedule
        if beat_schedule:
            print(f"✅ Настроено периодических задач: {len(beat_schedule)}")
            for task_name in beat_schedule.keys():
                print(f"   - {task_name}")
        else:
            print("⚠️ Нет настроенных периодических задач")

        return True

    except Exception as e:
        print(f"❌ Ошибка Celery Beat: {e}")
        return False


def test_telegram_tasks():
    """Проверка Telegram задач"""
    print("\n🤖 Тестирование Telegram задач...")
    try:
        # Пробуем импортировать задачи
        from telegram_bot.tasks import send_daily_reminders, send_weekly_stats

        print("✅ Telegram задачи импортированы")

        # Проверяем модели
        from telegram_bot.models import TelegramUser
        users_count = TelegramUser.objects.count()
        print(f"   Telegram пользователей: {users_count}")

        return True

    except Exception as e:
        print(f"❌ Ошибка Telegram задач: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование LinguaTrack компонентов")
    print("=" * 50)

    results = []

    # Тестируем компоненты
    results.append(("Redis", test_redis()))
    results.append(("Celery Basic", test_celery_basic()))
    results.append(("Celery Tasks", test_celery_task()))
    results.append(("Celery Beat", test_scheduled_tasks()))
    results.append(("Telegram Tasks", test_telegram_tasks()))

    # Выводим итоги
    print("\n" + "=" * 50)
    print("📊 Результаты тестирования:")

    passed = 0
    for name, result in results:
        status = "✅ ПРОШЕЛ" if result else "❌ ПРОВАЛЕН"
        print(f"   {name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 Итого: {passed}/{len(results)} тестов прошли успешно")

    if passed == len(results):
        print("🎉 Все компоненты работают корректно!")
    else:
        print("⚠️ Некоторые компоненты требуют внимания")


if __name__ == '__main__':
    main()

# 2. Создайте файл test_tasks.py для простой проверки задач:

# !/usr/bin/env python
"""Простое тестирование задач"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguatrack.settings')
django.setup()

from celery import shared_task


@shared_task
def hello_world():
    return "Hello from Celery!"


@shared_task
def add_numbers(x, y):
    return x + y


if __name__ == '__main__':
    print("Тестирование простых задач...")

    # Запуск задач
    result1 = hello_world.delay()
    result2 = add_numbers.delay(4, 6)

    print(f"Задача 1 ID: {result1.id}")
    print(f"Задача 2 ID: {result2.id}")

    # Получение результатов (с таймаутом)
    try:
        print(f"Результат 1: {result1.get(timeout=10)}")
        print(f"Результат 2: {result2.get(timeout=10)}")
        print("✅ Все задачи выполнены успешно!")
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")

# 3. Команда Django для проверки (создайте cards/management/commands/test_celery.py):

from django.core.management.base import BaseCommand
from celery import current_app
from django.conf import settings
import redis


class Command(BaseCommand):
    help = 'Проверка состояния Celery и Redis'

    def handle(self, *args, **options):
        self.stdout.write("🔧 Проверка системы...")

        # Проверка Redis
        try:
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            self.stdout.write(self.style.SUCCESS("✅ Redis доступен"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Redis недоступен: {e}"))

        # Проверка Celery
        try:
            inspect = current_app.control.inspect()
            stats = inspect.stats()

            if stats:
                self.stdout.write(self.style.SUCCESS(f"✅ Celery активен ({len(stats)} worker)"))

                # Проверяем активные задачи
                active = inspect.active()
                total_active = sum(len(tasks) for tasks in active.values()) if active else 0
                self.stdout.write(f"   Активных задач: {total_active}")

                # Проверяем зарегистрированные задачи
                registered = inspect.registered()
                if registered:
                    total_registered = sum(len(tasks) for tasks in registered.values())
                    self.stdout.write(f"   Зарегистрированных задач: {total_registered}")

            else:
                self.stdout.write(self.style.ERROR("❌ Celery worker недоступен"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка Celery: {e}"))