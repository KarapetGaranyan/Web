from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TelegramUser
from .bot import bot
import asyncio


@shared_task
def send_daily_reminders():
    """Send daily reminders"""
    from cards.models import Card

    # Get users with enabled notifications
    telegram_users = TelegramUser.objects.filter(
        notifications_enabled=True,
        is_active=True
    ).select_related('user')

    sent_count = 0

    for tg_user in telegram_users:
        # Check if there are cards for review
        due_cards_count = Card.objects.filter(
            user=tg_user.user,
            schedule__next_review__lte=timezone.now()
        ).count()

        if due_cards_count > 0:
            # Send reminder
            asyncio.run(send_reminder_to_user(tg_user, due_cards_count))
            sent_count += 1

    return f"Отправлено {sent_count} напоминаний"


async def send_reminder_to_user(telegram_user, due_cards_count):
    """Send reminder to specific user"""
    reminder_text = f"""
⏰ **Время изучения!**

У тебя {due_cards_count} карточек к повторению.

Потрать 5 минут на изучение слов! 🚀
"""

    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Начать изучение", callback_data="start_study")],
            [InlineKeyboardButton(text="📚 Посмотреть карточки", callback_data="today")]
        ])

        await bot.send_message(
            chat_id=telegram_user.telegram_id,
            text=reminder_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"Ошибка отправки напоминания пользователю {telegram_user.telegram_id}: {e}")


@shared_task
def send_weekly_stats():
    """Send weekly statistics"""
    from cards.models import StudySession

    telegram_users = TelegramUser.objects.filter(
        notifications_enabled=True,
        is_active=True
    ).select_related('user')

    week_ago = timezone.now() - timedelta(days=7)
    sent_count = 0

    for tg_user in telegram_users:
        # Weekly statistics
        week_sessions = StudySession.objects.filter(
            user=tg_user.user,
            created_at__gte=week_ago
        )

        if week_sessions.count() > 0:
            asyncio.run(send_weekly_stats_to_user(tg_user, week_sessions))
            sent_count += 1

    return f"Отправлена статистика {sent_count} пользователям"


async def send_weekly_stats_to_user(telegram_user, week_sessions):
    """Send weekly statistics to user"""
    total_sessions = week_sessions.count()
    correct_sessions = week_sessions.filter(result__in=['perfect', 'correct']).count()
    accuracy = round((correct_sessions / total_sessions) * 100, 1) if total_sessions > 0 else 0

    stats_text = f"""
📊 **Твоя неделя в цифрах:**

🎯 Сессий изучения: {total_sessions}
✅ Правильных ответов: {correct_sessions}
📈 Точность: {accuracy}%

{'🔥 Отличная работа!' if accuracy >= 80 else '💪 Продолжай тренироваться!'}
"""

    try:
        await bot.send_message(
            chat_id=telegram_user.telegram_id,
            text=stats_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки статистики пользователю {telegram_user.telegram_id}: {e}")