# shop/management/commands/analyze_performance.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import override_settings
from shop.models import Product, Category, Order
import time


class Command(BaseCommand):
    help = 'Analyze database performance and suggest optimizations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-queries',
            action='store_true',
            help='Test query performance',
        )

    def handle(self, *args, **options):
        if options['test_queries']:
            self.test_query_performance()

        self.analyze_database()

    def test_query_performance(self):
        """Тестирование производительности запросов"""
        self.stdout.write('\n=== ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ ЗАПРОСОВ ===\n')

        # Тест 1: Загрузка товаров без оптимизации
        start_time = time.time()
        products_unoptimized = list(Product.objects.filter(is_active=True)[:20])
        for product in products_unoptimized:
            _ = product.category.name  # Вызовет дополнительные запросы
            _ = product.images.first()  # Еще больше запросов
        unoptimized_time = time.time() - start_time

        # Тест 2: Загрузка товаров с оптимизацией
        start_time = time.time()
        products_optimized = list(
            Product.objects.filter(is_active=True)
            .select_related('category')
            .prefetch_related('images')[:20]
        )
        for product in products_optimized:
            _ = product.category.name
            _ = product.images.first()
        optimized_time = time.time() - start_time

        self.stdout.write(f'Неоптимизированный запрос: {unoptimized_time:.4f}s')
        self.stdout.write(f'Оптимизированный запрос: {optimized_time:.4f}s')

        if unoptimized_time > 0:
            improvement = (unoptimized_time - optimized_time) / unoptimized_time * 100
            self.stdout.write(
                self.style.SUCCESS(f'Улучшение производительности: {improvement:.1f}%')
            )

    def analyze_database(self):
        """Анализ структуры базы данных"""
        self.stdout.write('\n=== АНАЛИЗ БАЗЫ ДАННЫХ ===\n')

        # Статистика по таблицам
        with connection.cursor() as cursor:
            # Для SQLite
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name LIKE 'shop_%'
            """)
            tables = cursor.fetchall()

            for table_name, sql in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                self.stdout.write(f'{table_name}: {count} записей')

        # Проверка индексов
        self.stdout.write('\n=== АНАЛИЗ ИНДЕКСОВ ===\n')

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='index' AND name LIKE '%shop_%'
            """)
            indexes = cursor.fetchall()

            self.stdout.write(f'Найдено индексов: {len(indexes)}')
            for index_name, sql in indexes:
                if sql:  # Пропускаем автоматические индексы
                    self.stdout.write(f'  - {index_name}')

        # Рекомендации
        self.stdout.write('\n=== РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ ===\n')

        # Проверяем товары без изображений
        products_without_images = Product.objects.filter(images__isnull=True).count()
        if products_without_images > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Найдено {products_without_images} товаров без изображений'
                )
            )

        # Проверяем неактивные товары
        inactive_products = Product.objects.filter(is_active=False).count()
        total_products = Product.objects.count()
        if inactive_products > total_products * 0.3:
            self.stdout.write(
                self.style.WARNING(
                    f'Много неактивных товаров ({inactive_products}/{total_products}). '
                    'Рассмотрите архивирование.'
                )
            )

        # Проверяем заказы без товаров
        empty_orders = Order.objects.filter(items__isnull=True).count()
        if empty_orders > 0:
            self.stdout.write(
                self.style.ERROR(
                    f'Найдено {empty_orders} заказов без товаров. Требуется очистка.'
                )
            )

        self.stdout.write('\n=== ЗАВЕРШЕНО ===\n')