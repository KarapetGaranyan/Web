# shop/management/commands/fix_cancelled_orders.py
from django.core.management.base import BaseCommand
from shop.models import Order


class Command(BaseCommand):
    help = 'Fix cancelled orders by returning items to stock'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Найти все отмененные заказы
        cancelled_orders = Order.objects.filter(status='cancelled')

        if not cancelled_orders.exists():
            self.stdout.write(self.style.SUCCESS('No cancelled orders found'))
            return

        self.stdout.write(f'Found {cancelled_orders.count()} cancelled orders')

        for order in cancelled_orders:
            self.stdout.write(f'\nProcessing order #{order.order_number}:')

            for item in order.items.all():
                old_stock = item.product.stock
                new_stock = old_stock + item.quantity

                self.stdout.write(
                    f'  - {item.product.name}: {item.quantity} units '
                    f'(stock: {old_stock} -> {new_stock})'
                )

                if not dry_run:
                    item.product.stock = new_stock
                    item.product.save()

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nDry run completed. Use without --dry-run to apply changes.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully processed {cancelled_orders.count()} cancelled orders')
            )