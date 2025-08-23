from django.core.management.base import BaseCommand
from telegram_bot.bot import main
import asyncio


class Command(BaseCommand):
    help = 'Запуск Telegram бота'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🤖 Запуск Telegram бота...')
        )

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('🛑 Бот остановлен пользователем')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка запуска бота: {e}')
            )