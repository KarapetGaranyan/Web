from django.core.management.base import BaseCommand
from cards.models import Card
from cards.utils import generate_audio_for_card


class Command(BaseCommand):
    help = 'Генерация аудио для всех карточек'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username для генерации аудио только для этого пользователя',
        )

    def handle(self, *args, **options):
        cards = Card.objects.filter(audio__isnull=True)

        if options['user']:
            cards = cards.filter(user__username=options['user'])

        generated = 0
        for card in cards:
            self.stdout.write(f'Генерируем аудио для: {card.word}')
            audio = generate_audio_for_card(card)
            if audio:
                generated += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Аудио создано для "{card.word}"')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Ошибка для "{card.word}"')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Завершено! Сгенерировано {generated} аудио файлов')
        )