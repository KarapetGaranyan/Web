from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from .models import Card, Schedule
from .utils import generate_audio_for_card


@shared_task
def generate_audio_for_all_cards():
    """Генерация аудио для карточек без аудио"""
    cards_without_audio = Card.objects.filter(audio__isnull=True)

    generated_count = 0
    for card in cards_without_audio:
        audio = generate_audio_for_card(card)
        if audio:
            generated_count += 1

    return f"Сгенерировано аудио для {generated_count} карточек"


@shared_task
def update_due_cards_count():
    """Обновление счетчика карточек к повторению"""
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
    """Создание расписаний для карточек без расписания"""
    cards_without_schedule = Card.objects.filter(schedule__isnull=True)

    created_count = 0
    for card in cards_without_schedule:
        Schedule.objects.create(
            card=card,
            next_review=timezone.now() + timedelta(hours=1)
        )
        created_count += 1

    return f"Создано {created_count} расписаний"


@shared_task
def cleanup_old_sessions():
    """Очистка старых сессий изучения (старше 6 месяцев)"""
    from .models import StudySession

    six_months_ago = timezone.now() - timedelta(days=180)
    deleted_count, _ = StudySession.objects.filter(
        created_at__lt=six_months_ago
    ).delete()

    return f"Удалено {deleted_count} старых сессий"


# Тестовые задачи для проверки
@shared_task
def test_task(message):
    """Простая тестовая задача"""
    return f"Получено: {message} в {timezone.now()}"


@shared_task
def hello_world():
    """Тестовая задача Hello World"""
    return "Hello from Celery!"


@shared_task
def add_numbers(x, y):
    """Тестовая задача сложения"""
    return x + y