#!/usr/bin/env python
"""Запуск Telegram бота."""
import os
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguatrack.settings')
django.setup()

from telegram_bot.bot import main

if __name__ == '__main__':
    print("🤖 Запуск Telegram бота...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")