from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Category, Product, ProductImage
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Populate database with sample data'

    def handle(self, *args, **options):
        # Создаем суперпользователя если его нет
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Superuser created: admin/admin123'))

        # Создаем обычного пользователя для тестирования
        if not User.objects.filter(username='testuser').exists():
            User.objects.create_user('testuser', 'test@example.com', 'testpass123')
            self.stdout.write(self.style.SUCCESS('Test user created: testuser/testpass123'))

        # Создаем категории
        categories_data = [
            {
                'name': 'Электроника',
                'slug': 'electronics',
                'description': 'Смартфоны, ноутбуки, планшеты и другая электроника'
            },
            {
                'name': 'Одежда',
                'slug': 'clothing',
                'description': 'Мужская, женская и детская одежда'
            },
            {
                'name': 'Дом и сад',
                'slug': 'home-garden',
                'description': 'Товары для дома, сада и ремонта'
            },
            {
                'name': 'Спорт и отдых',
                'slug': 'sports',
                'description': 'Спортивные товары и товары для активного отдыха'
            },
            {
                'name': 'Книги',
                'slug': 'books',
                'description': 'Художественная и техническая литература'
            },
            {
                'name': 'Красота и здоровье',
                'slug': 'beauty-health',
                'description': 'Косметика, средства по уходу и товары для здоровья'
            },
        ]

        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'Category created: {category.name}')

        # Создаем товары
        products_data = [
            # Электроника
            {
                'name': 'iPhone 15 Pro',
                'slug': 'iphone-15-pro',
                'description': 'Новейший iPhone с улучшенными камерами, процессором A17 Pro и титановым корпусом. Доступен в четырех цветах.',
                'short_description': 'Флагманский смартфон Apple с процессором A17 Pro',
                'price': Decimal('119999.00'),
                'old_price': Decimal('129999.00'),
                'stock': 25,
                'sku': 'IP15PRO001',
                'category_slug': 'electronics',
                'rating': 4.8,
                'is_featured': True,
            },
            {
                'name': 'Samsung Galaxy S24 Ultra',
                'slug': 'samsung-galaxy-s24-ultra',
                'description': 'Мощный флагман Samsung с встроенным S Pen, камерой 200MP и экраном Dynamic AMOLED 2X.',
                'short_description': 'Флагманский смартфон Samsung с S Pen',
                'price': Decimal('109999.00'),
                'stock': 18,
                'sku': 'SGS24U001',
                'category_slug': 'electronics',
                'rating': 4.7,
                'is_featured': True,
            },
            {
                'name': 'MacBook Air M3',
                'slug': 'macbook-air-m3',
                'description': 'Ультратонкий и легкий ноутбук с процессором Apple M3, 13-дюймовым дисплеем Liquid Retina.',
                'short_description': 'Ноутбук Apple с процессором M3',
                'price': Decimal('149999.00'),
                'stock': 12,
                'sku': 'MBAM3001',
                'category_slug': 'electronics',
                'rating': 4.9,
                'is_featured': True,
            },

            # Одежда
            {
                'name': 'Джинсы Levi\'s 501 Original',
                'slug': 'levis-501-jeans',
                'description': 'Классические джинсы Levi\'s 501 с прямым кроем. Изготовлены из качественного денима.',
                'short_description': 'Классические джинсы Levi\'s прямого кроя',
                'price': Decimal('7999.00'),
                'old_price': Decimal('8999.00'),
                'stock': 45,
                'sku': 'LV501001',
                'category_slug': 'clothing',
                'rating': 4.5,
            },
            {
                'name': 'Пуховик The North Face',
                'slug': 'north-face-jacket',
                'description': 'Теплый зимний пуховик The North Face с водоотталкивающим покрытием и капюшоном.',
                'short_description': 'Зимний пуховик с водоотталкивающим покрытием',
                'price': Decimal('24999.00'),
                'stock': 20,
                'sku': 'TNF001',
                'category_slug': 'clothing',
                'rating': 4.6,
                'is_featured': True,
            },

            # Спорт
            {
                'name': 'Кроссовки Nike Air Max 270',
                'slug': 'nike-air-max-270',
                'description': 'Легкие беговые кроссовки с технологией Air Max для максимального комфорта.',
                'short_description': 'Беговые кроссовки с технологией Air Max',
                'price': Decimal('12999.00'),
                'old_price': Decimal('14999.00'),
                'stock': 35,
                'sku': 'NAM270001',
                'category_slug': 'sports',
                'rating': 4.4,
            },
            {
                'name': 'Велосипед Trek Mountain',
                'slug': 'trek-mountain-bike',
                'description': 'Горный велосипед Trek с алюминиевой рамой и 21-скоростной трансмиссией.',
                'short_description': 'Горный велосипед с алюминиевой рамой',
                'price': Decimal('45999.00'),
                'stock': 8,
                'sku': 'TMB001',
                'category_slug': 'sports',
                'rating': 4.7,
                'is_featured': True,
            },

            # Книги
            {
                'name': 'Чистый код. Роберт Мартин',
                'slug': 'clean-code-martin',
                'description': 'Руководство по разработке гибкого, читаемого и легко поддерживаемого кода.',
                'short_description': 'Руководство по написанию качественного кода',
                'price': Decimal('2299.00'),
                'stock': 150,
                'sku': 'CCM001',
                'category_slug': 'books',
                'rating': 4.8,
            },
            {
                'name': 'Python для сложных задач',
                'slug': 'python-complex-tasks',
                'description': 'Продвинутое руководство по программированию на Python для решения сложных задач.',
                'short_description': 'Продвинутое руководство по Python',
                'price': Decimal('2899.00'),
                'old_price': Decimal('3299.00'),
                'stock': 80,
                'sku': 'PCT001',
                'category_slug': 'books',
                'rating': 4.6,
            },

            # Дом и сад
            {
                'name': 'Кофемашина DeLonghi',
                'slug': 'delonghi-coffee-machine',
                'description': 'Автоматическая кофемашина DeLonghi с встроенной кофемолкой и капучинатором.',
                'short_description': 'Автоматическая кофемашина с капучинатором',
                'price': Decimal('89999.00'),
                'stock': 15,
                'sku': 'DCM001',
                'category_slug': 'home-garden',
                'rating': 4.5,
                'is_featured': True,
            },
            {
                'name': 'Набор садового инструмента',
                'slug': 'garden-tools-set',
                'description': 'Комплект садовых инструментов: лопата, грабли, секатор, совок и перчатки.',
                'short_description': 'Комплект основных садовых инструментов',
                'price': Decimal('4999.00'),
                'stock': 30,
                'sku': 'GTS001',
                'category_slug': 'home-garden',
                'rating': 4.3,
            },

            # Красота и здоровье
            {
                'name': 'Крем для лица L\'Oreal',
                'slug': 'loreal-face-cream',
                'description': 'Увлажняющий антивозрастной крем для лица с гиалуроновой кислотой.',
                'short_description': 'Увлажняющий крем с гиалуроновой кислотой',
                'price': Decimal('1899.00'),
                'stock': 60,
                'sku': 'LFC001',
                'category_slug': 'beauty-health',
                'rating': 4.2,
            },
        ]

        for prod_data in products_data:
            try:
                category = Category.objects.get(slug=prod_data['category_slug'])
                product, created = Product.objects.get_or_create(
                    slug=prod_data['slug'],
                    defaults={
                        'name': prod_data['name'],
                        'description': prod_data['description'],
                        'short_description': prod_data['short_description'],
                        'category': category,
                        'price': prod_data['price'],
                        'old_price': prod_data.get('old_price'),
                        'stock': prod_data['stock'],
                        'sku': prod_data['sku'],
                        'rating': Decimal(str(prod_data.get('rating', random.uniform(3.5, 5.0)))),
                        'is_featured': prod_data.get('is_featured', False),
                        'is_active': True,
                    }
                )
                if created:
                    self.stdout.write(f'Product created: {product.name}')
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Category {prod_data["category_slug"]} not found for product {prod_data["name"]}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDatabase populated successfully!\n'
                f'Created {Category.objects.count()} categories and {Product.objects.count()} products.\n'
                f'Admin user: admin/admin123\n'
                f'Test user: testuser/testpass123'
            )
        )