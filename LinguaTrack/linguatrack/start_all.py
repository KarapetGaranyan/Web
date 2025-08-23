import os
import django
import asyncio
import threading
import subprocess
import sys
from pathlib import Path

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguatrack.settings')
django.setup()


def run_django_server():
    """Запуск Django сервера"""
    print("🌐 Запуск Django сервера...")
    os.system("python manage.py runserver")


def run_telegram_bot():
    """Запуск Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    from telegram_bot.bot import main
    asyncio.run(main())


def main():
    print("🚀 Запуск LinguaTrack")
    print("Django: http://127.0.0.1:8000")
    print("Bot: проверьте в Telegram")
    print("\nДля остановки нажмите Ctrl+C\n")

    # Запуск Django в отдельном потоке
    django_thread = threading.Thread(target=run_django_server, daemon=True)
    django_thread.start()

    # Небольшая пауза
    import time
    time.sleep(3)

    # Запуск бота в основном потоке
    try:
        run_telegram_bot()
    except KeyboardInterrupt:
        print("\n✋ Остановка сервисов...")


if __name__ == '__main__':
    main()