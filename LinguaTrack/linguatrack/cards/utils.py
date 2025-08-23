from gtts import gTTS
import os
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from io import BytesIO
from .models import Card


def get_cards_for_review(user, limit=20):
    """Синхронная версия для использования с sync_to_async"""
    from django.utils import timezone
    from .models import Card, Schedule

    # Карточки, которые пора повторять
    due_cards = list(Card.objects.filter(
        user=user,
        schedule__next_review__lte=timezone.now()
    ).select_related('schedule').order_by('schedule__next_review')[:limit // 2])

    # Новые карточки (без расписания)
    new_cards = list(Card.objects.filter(
        user=user,
        schedule__isnull=True
    )[:limit // 2])

    # Объединяем и ограничиваем
    all_cards = due_cards + new_cards
    return all_cards[:limit]


def update_card_statistics(card, is_correct, response_time=None):
    """Обновление статистики карточки"""
    card.times_studied += 1
    if is_correct:
        card.times_correct += 1

    # Отмечаем как выученную если точность > 80% и изучено > 5 раз
    if card.times_studied >= 5 and card.accuracy_rate >= 80:
        card.is_learned = True

    card.save()

    # Обновляем статистику пользователя
    from .models import UserStats
    stats, _ = UserStats.objects.get_or_create(user=card.user)
    stats.total_sessions += 1
    if is_correct:
        stats.correct_answers += 1
    stats.last_study = timezone.now()
    stats.learned_cards = Card.objects.filter(user=card.user, is_learned=True).count()
    stats.total_cards = Card.objects.filter(user=card.user).count()
    stats.save()


def generate_audio_for_card(card):
    """Генерация аудио для карточки"""
    try:
        from gtts import gTTS
        from django.conf import settings
        from django.core.files.base import ContentFile
        from io import BytesIO
        from .models import AudioFile

        # Получаем настройки TTS
        tts_language = getattr(settings, 'TTS_LANGUAGE', 'en')
        tts_slow = getattr(settings, 'TTS_SLOW', False)

        # Создаем TTS объект
        tts = gTTS(
            text=card.word,
            lang=tts_language,
            slow=tts_slow
        )

        # Сохраняем в память
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        # Создаем или обновляем аудио файл
        audio_obj, created = AudioFile.objects.get_or_create(
            card=card,
            defaults={'language': tts_language}
        )

        # Сохраняем файл
        filename = f"card_{card.id}_{card.word[:20]}.mp3"
        audio_obj.audio_file.save(
            filename,
            ContentFile(fp.read()),
            save=True
        )

        return audio_obj

    except Exception as e:
        print(f"Ошибка генерации аудио для {card.word}: {e}")
        return None