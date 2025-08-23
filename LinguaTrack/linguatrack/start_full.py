import os
import sys
import subprocess
import threading
import time
import platform
import signal
from pathlib import Path


class LinguaTrackRunner:
    def __init__(self):
        self.processes = []
        self.threads = []

    def run_redis(self):
        """Запуск Redis сервера"""
        print("🔴 Запуск Redis сервера...")
        try:
            if platform.system() == "Windows":
                # Для Windows - попробуйте WSL или Windows версию Redis
                redis_cmd = ["wsl", "redis-server"]
                # Альтернатива для Windows Redis:
                # redis_cmd = ["redis-server.exe"]
            else:
                redis_cmd = ["redis-server"]

            process = subprocess.Popen(
                redis_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(('Redis', process))
            print("✅ Redis сервер запущен")

        except Exception as e:
            print(f"❌ Ошибка запуска Redis: {e}")
            print("💡 Установите Redis:")
            print("   Windows: https://github.com/microsoftarchive/redis/releases")
            print("   Or use WSL: wsl --install")

    def run_django(self):
        """Запуск Django сервера"""
        print("🌐 Запуск Django сервера...")
        try:
            process = subprocess.Popen([
                sys.executable, 'manage.py', 'runserver'
            ])
            self.processes.append(('Django', process))
            print("✅ Django сервер запущен на http://127.0.0.1:8000")
        except Exception as e:
            print(f"❌ Ошибка запуска Django: {e}")

    def run_celery_worker(self):
        """Запуск Celery Worker"""
        print("⚙️ Запуск Celery Worker...")
        try:
            # Для Windows используем --pool=solo
            cmd = [
                sys.executable, '-m', 'celery',
                '-A', 'linguatrack',
                'worker',
                '--loglevel=info',
                '--pool=solo'  # Исправление для Windows
            ]

            process = subprocess.Popen(cmd)
            self.processes.append(('Celery Worker', process))
            print("✅ Celery Worker запущен (Windows режим)")
        except Exception as e:
            print(f"❌ Ошибка запуска Celery Worker: {e}")

    def run_celery_beat(self):
        """Запуск Celery Beat (планировщик)"""
        print("⏰ Запуск Celery Beat...")
        try:
            process = subprocess.Popen([
                sys.executable, '-m', 'celery',
                '-A', 'linguatrack',
                'beat',
                '--loglevel=info'
            ])
            self.processes.append(('Celery Beat', process))
            print("✅ Celery Beat запущен")
        except Exception as e:
            print(f"❌ Ошибка запуска Celery Beat: {e}")

    def run_telegram_bot(self):
        """Запуск Telegram бота"""
        print("🤖 Запуск Telegram бота...")
        try:
            # Попробуем сначала через manage.py runbot
            process = subprocess.Popen([
                sys.executable, 'manage.py', 'runbot'
            ])
            self.processes.append(('Telegram Bot', process))
            print("✅ Telegram бот запущен")
        except Exception as e:
            print(f"❌ Ошибка manage.py runbot: {e}")
            try:
                # Fallback - запуск через run_bot.py
                process = subprocess.Popen([
                    sys.executable, 'run_bot.py'
                ])
                self.processes.append(('Telegram Bot', process))
                print("✅ Telegram бот запущен через run_bot.py")
            except Exception as e2:
                print(f"❌ Ошибка запуска Telegram бота: {e2}")

    def start_all(self):
        """Запуск всех сервисов"""
        print("🚀 Запуск полной системы LinguaTrack")
        print("=" * 50)

        # 1. Redis (должен запуститься первым)
        self.run_redis()
        time.sleep(2)

        # 2. Django сервер
        self.run_django()
        time.sleep(3)

        # 3. Celery Worker
        self.run_celery_worker()
        time.sleep(2)

        # 4. Celery Beat
        self.run_celery_beat()
        time.sleep(2)

        # 5. Telegram Bot
        self.run_telegram_bot()

        print("\n" + "=" * 50)
        print("🎉 Все сервисы запущены!")
        print("🌐 Django: http://127.0.0.1:8000")
        print("🤖 Telegram: отправьте /start боту")
        print("🔴 Redis: localhost:6379")
        print("\n💡 Нажмите Ctrl+C для остановки всех сервисов")
        print("=" * 50)

    def stop_all(self):
        """Остановка всех сервисов"""
        print("\n🛑 Остановка всех сервисов...")

        for name, process in self.processes:
            try:
                print(f"🔽 Остановка {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"⚡ Принудительная остановка {name}...")
                process.kill()
            except Exception as e:
                print(f"❌ Ошибка остановки {name}: {e}")

        print("✅ Все сервисы остановлены")

    def run(self):
        """Главная функция запуска"""
        try:
            self.start_all()

            # Ожидание завершения
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            self.stop_all()
            sys.exit(0)
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            self.stop_all()
            sys.exit(1)


def check_requirements():
    """Проверка необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")

    required_packages = ['django', 'celery', 'redis', 'aiogram']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")

    if missing_packages:
        print(f"\n📦 Установите недостающие пакеты:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True


def main():
    print("🎯 LinguaTrack - Полный запуск системы")
    print("=" * 50)

    # Проверка зависимостей
    if not check_requirements():
        sys.exit(1)

    # Проверка файлов
    if not Path('manage.py').exists():
        print("❌ Файл manage.py не найден!")
        print("💡 Запустите скрипт из корневой папки проекта")
        sys.exit(1)

    # Запуск
    runner = LinguaTrackRunner()
    runner.run()


if __name__ == '__main__':
    main()