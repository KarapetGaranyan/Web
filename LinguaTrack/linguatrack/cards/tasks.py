from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from .models import Card, Schedule
from .utils import generate_audio_for_card


@shared_task
def generate_audio_for_all_cards():
    cards_without_audio = Card.objects.filter(audio__isnull=True)

    generated_count = 0
    for card in cards_without_audio:
        audio = generate_audio_for_card(card)
        if audio:
            generated_count += 1

    return f"Сгенерировано аудио для {generated_count} карточек"


@shared_task
def update_due_cards_count():
    users = User.objects.all()

    for user in users:
        due_count = Card.objects.filter(
            user=user,
            schedule__next_review__lte=timezone.now()
        ).count()

        # Здесь можно отправить уведомление пользователю
        if due_count > 0:
            print(f"У пользователя {user.username} {due_count} карточек к повторению")

    return "Обновление завершено"


@shared_task
def create_missing_schedules():
    cards_without_schedule = Card.objects.filter(schedule__isnull=True)

    created_count = 0
    for card in cards_without_schedule:
        Schedule.objects.create(
            card=card,
            next_review=timezone.now() + timedelta(hours=1)
        )
        created_count += 1

    return f"Создано {created_count} расписаний"