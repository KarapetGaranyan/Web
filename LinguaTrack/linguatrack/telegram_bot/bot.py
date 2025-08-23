import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from django.conf import settings
from asgiref.sync import sync_to_async
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linguatrack.settings')
django.setup()

from cards.models import Card, StudySession, UserStats, Schedule
from telegram_bot.models import TelegramUser, BotMessage
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


class StudyStates(StatesGroup):
    waiting_for_answer = State()


def get_or_create_user_sync(telegram_data):
    try:
        telegram_user = TelegramUser.objects.select_related('user').get(
            telegram_id=telegram_data['id']
        )
        return telegram_user
    except TelegramUser.DoesNotExist:
        username = f"tg_{telegram_data['id']}"
        django_user = User.objects.create(
            username=username,
            first_name=telegram_data.get('first_name', ''),
            last_name=telegram_data.get('last_name', '')
        )

        telegram_user = TelegramUser.objects.create(
            user=django_user,
            telegram_id=telegram_data['id'],
            username=telegram_data.get('username', ''),
            first_name=telegram_data.get('first_name', ''),
            last_name=telegram_data.get('last_name', ''),
            language_code=telegram_data.get('language_code', 'ru')
        )

        return telegram_user


get_or_create_user = sync_to_async(get_or_create_user_sync)


def log_message_sync(telegram_user, msg_type, content):
    return BotMessage.objects.create(
        telegram_user=telegram_user,
        message_type=msg_type,
        content=content
    )


log_message = sync_to_async(log_message_sync)


@dp.message(CommandStart())
async def start_command(message: Message):
    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    welcome_text = f"""
🎉 Добро пожаловать в LinguaTrack!

Привет, {telegram_user.first_name or 'друг'}! Я помогу тебе изучать слова прямо в Telegram.

📚 Доступные команды:
/link - Привязать аккаунт
/today - Карточки на сегодня
/test - Быстрый тест
/progress - Твоя статистика
/cards - Список карточек
/help - Помощь

Начнем изучение? 🚀
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Карточки на сегодня", callback_data="today")],
        [InlineKeyboardButton(text="🎯 Быстрый тест", callback_data="test")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="progress")]
    ])

    await message.answer(welcome_text, reply_markup=keyboard)
    await log_message(telegram_user, "start", "Пользователь запустил бота")


@dp.message(Command("link"))
async def link_command(message: Message):
    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) < 2:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "Получите токен привязки на сайте LinguaTrack\n"
            "Формат: /link ваш_токен"
        )
        return

    token = command_parts[1].strip()

    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def link_account():
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.create_user(
                    username=f'user_{telegram_user.telegram_id}',
                    first_name=telegram_user.first_name
                )

            telegram_user.user = admin_user
            telegram_user.save()

            return admin_user, None
        except Exception as e:
            return None, str(e)

    linked_user, error = await link_account()

    if error:
        await message.answer(f"❌ Ошибка привязки: {error}")
    else:
        await message.answer(
            f"✅ Аккаунт успешно привязан!\n"
            f"Пользователь: {linked_user.username}\n\n"
            "Теперь вы можете использовать все функции бота:\n"
            "📚 /today - карточки на сегодня\n"
            "🎯 /test - быстрый тест\n"
            "📊 /progress - статистика\n"
            "📋 /cards - список карточек"
        )

    await log_message(telegram_user, "link", f"Привязка с токеном {token[:8]}...")


@dp.message(Command("today"))
async def today_command(message: Message):
    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def get_due_cards():
        due_cards = []
        cards_with_schedule = Card.objects.filter(
            user=telegram_user.user
        ).prefetch_related('schedule')

        for card in cards_with_schedule:
            try:
                if card.schedule and card.schedule.next_review <= timezone.now():
                    due_cards.append(card)
            except Schedule.DoesNotExist:
                due_cards.append(card)

        return due_cards[:10]

    due_cards = await get_due_cards()

    if not due_cards:
        await message.answer(
            "🎉 Отлично! У тебя нет карточек к повторению сегодня.\n"
            "Можешь отдохнуть или создать новые карточки на сайте!"
        )
        return

    cards_text = f"📚 У тебя {len(due_cards)} карточек к повторению:\n\n"

    for i, card in enumerate(due_cards[:5], 1):
        cards_text += f"{i}. **{card.word}** — {card.translation}\n"
        try:
            if hasattr(card, 'schedule') and card.schedule.repetitions > 0:
                cards_text += f"   Повторений: {card.schedule.repetitions}\n"
        except:
            pass

    if len(due_cards) > 5:
        cards_text += f"\n... и еще {len(due_cards) - 5} карточек"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать изучение", callback_data="start_study")],
        [InlineKeyboardButton(text="🎲 Случайный тест", callback_data="test")]
    ])

    await message.answer(cards_text, reply_markup=keyboard, parse_mode="Markdown")
    await log_message(telegram_user, "today", f"Показано {len(due_cards)} карточек")


@dp.message(Command("progress"))
async def progress_command(message: Message):
    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def get_user_stats():
        try:
            stats = UserStats.objects.get(user=telegram_user.user)
        except UserStats.DoesNotExist:
            stats = UserStats.objects.create(user=telegram_user.user)

        due_cards_count = 0
        for card in Card.objects.filter(user=telegram_user.user):
            try:
                if hasattr(card, 'schedule') and card.schedule.next_review <= timezone.now():
                    due_cards_count += 1
            except:
                due_cards_count += 1

        week_ago = timezone.now() - timedelta(days=7)
        week_sessions = StudySession.objects.filter(
            user=telegram_user.user,
            created_at__gte=week_ago
        ).count()

        return stats, due_cards_count, week_sessions

    stats, due_cards_count, week_sessions = await get_user_stats()

    progress_text = f"""
📊 **Твоя статистика:**

📚 Всего карточек: **{stats.total_cards}**
✅ Выучено: **{stats.learned_cards}**
🎯 К повторению: **{due_cards_count}**
📈 Точность: **{stats.accuracy_rate}%**

⏱️ Время изучения: **{stats.study_time_minutes} мин**
🔥 Сессий за неделю: **{week_sessions}**

🎯 **Недельная цель:** {stats.current_week_studied}/{stats.weekly_goal}
"""

    try:
        weekly_progress = stats.weekly_progress
        progress_blocks = int(weekly_progress // 10)
        remaining_blocks = 10 - progress_blocks
        progress_bar = "▓" * progress_blocks + "░" * remaining_blocks
        progress_text += f"\n[{progress_bar}] {weekly_progress}%"
    except:
        progress_text += f"\nПрогресс: {stats.current_week_studied}/{stats.weekly_goal}"

    if stats.last_study:
        progress_text += f"\n\n🕐 Последнее изучение: {stats.last_study.strftime('%d.%m.%Y %H:%M')}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Изучать сейчас", callback_data="start_study")],
        [InlineKeyboardButton(text="📚 Карточки на сегодня", callback_data="today")]
    ])

    await message.answer(progress_text, reply_markup=keyboard, parse_mode="Markdown")
    await log_message(telegram_user, "progress", "Показана статистика")


@dp.message(Command("test"))
async def test_command(message: Message, state: FSMContext):
    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def get_random_card():
        cards = Card.objects.filter(user=telegram_user.user)
        return cards.order_by('?').first() if cards.exists() else None

    card = await get_random_card()

    if not card:
        await message.answer("❌ У тебя пока нет карточек для тестирования!")
        return

    await state.update_data(
        current_card_id=card.id,
        test_mode=True,
        start_time=datetime.now().timestamp()
    )
    await state.set_state(StudyStates.waiting_for_answer)

    test_text = f"""
🎯 **Быстрый тест**

Переведи слово:
**{card.word}**
"""

    if card.example:
        test_text += f"\n_Пример: {card.example}_"

    await message.answer(test_text, parse_mode="Markdown")
    await log_message(telegram_user, "test", f"Тест: {card.word}")


@dp.message(Command("cards"))
async def cards_command(message: Message):
    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def get_cards():
        return list(Card.objects.filter(
            user=telegram_user.user
        ).order_by('-created_at')[:15])

    cards = await get_cards()

    if not cards:
        await message.answer("📚 У тебя пока нет карточек. Создай их на сайте!")
        return

    cards_text = "📚 **Твои карточки** (последние 15):\n\n"

    for card in cards:
        if card.is_learned:
            status_emoji = "✅"
        elif card.times_studied == 0:
            status_emoji = "🆕"
        else:
            status_emoji = "📖"

        cards_text += f"{status_emoji} **{card.word}** — {card.translation}\n"

        if card.times_studied > 0:
            cards_text += f"   📊 {card.times_studied} раз, {card.accuracy_rate}% точность\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Изучать", callback_data="start_study")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="progress")]
    ])

    await message.answer(cards_text, reply_markup=keyboard, parse_mode="Markdown")
    await log_message(telegram_user, "cards", f"Показано {len(cards)} карточек")


@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = """
🤖 **LinguaTrack Bot - Справка**

📚 **Основные команды:**
/link токен - Привязать аккаунт
/today - Карточки к повторению сегодня
/test - Быстрый тест (случайная карточка)
/progress - Твоя статистика обучения
/cards - Список твоих карточек
/help - Помощь

💡 **Как использовать:**
1. Создавай карточки на сайте LinguaTrack
2. Привяжи аккаунт командой /link
3. Изучай слова где угодно!

Для начала создайте несколько карточек на сайте, затем используйте команды бота.
"""

    await message.answer(help_text, parse_mode="Markdown")


@dp.message(StudyStates.waiting_for_answer)
async def handle_study_answer(message: Message, state: FSMContext):
    data = await state.get_data()

    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def process_answer(card_id, user_answer):
        try:
            card = Card.objects.get(id=card_id, user=telegram_user.user)
        except Card.DoesNotExist:
            return None, "Карточка не найдена"

        correct_answer = card.translation.strip().lower()
        user_answer_clean = user_answer.strip().lower()
        is_correct = user_answer_clean == correct_answer

        if is_correct:
            quality = 5 if user_answer.strip() == card.translation.strip() else 4
            result = 'perfect' if quality == 5 else 'correct'
            emoji = "🎉" if quality == 5 else "✅"
            result_text = "Идеально!" if quality == 5 else "Правильно!"
        else:
            similarity = len(set(user_answer_clean.split()) & set(correct_answer.split()))
            if similarity > 0:
                quality = 3
                result = 'hard'
                emoji = "⚠️"
                result_text = "Близко, но неточно"
            else:
                quality = 2
                result = 'incorrect'
                emoji = "❌"
                result_text = "Неправильно"

        StudySession.objects.create(
            card=card,
            user=telegram_user.user,
            result=result,
            quality_score=quality,
            user_answer=user_answer
        )

        card.times_studied += 1
        if is_correct:
            card.times_correct += 1

        if card.times_studied >= 5 and card.accuracy_rate >= 80:
            card.is_learned = True

        card.save()

        try:
            schedule = card.schedule
        except Schedule.DoesNotExist:
            schedule = Schedule.objects.create(
                card=card,
                next_review=timezone.now() + timedelta(days=1)
            )

        stats, _ = UserStats.objects.get_or_create(user=telegram_user.user)
        stats.total_sessions += 1
        if is_correct:
            stats.correct_answers += 1
        stats.last_study = timezone.now()
        stats.save()

        return {
            'card': card,
            'is_correct': is_correct,
            'emoji': emoji,
            'result_text': result_text,
            'quality': quality
        }, None

    result, error = await process_answer(data['current_card_id'], message.text)

    if error:
        await message.answer(f"❌ {error}")
        await state.clear()
        return

    card = result['card']
    await state.clear()

    response_text = f"""
{result['emoji']} **{result['result_text']}**

Правильный ответ: **{card.translation}**
Твой ответ: _{message.text}_

🎊 **Тест завершен!**
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Еще тест", callback_data="test")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="progress")]
    ])

    await message.answer(response_text, reply_markup=keyboard, parse_mode="Markdown")
    await log_message(telegram_user, "test_completed", f"Тест завершен: {card.word}")


@dp.callback_query(F.data == "today")
async def today_callback(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await today_command(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "progress")
async def progress_callback(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await progress_command(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "test")
async def test_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await test_command(callback.message, state)
    await callback.answer()


@dp.callback_query(F.data == "start_study")
async def start_study_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)

    telegram_data = {
        'id': callback.from_user.id,
        'username': callback.from_user.username,
        'first_name': callback.from_user.first_name,
        'last_name': callback.from_user.last_name,
        'language_code': callback.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    @sync_to_async
    def get_study_cards():
        cards = []
        for card in Card.objects.filter(user=telegram_user.user):
            try:
                if hasattr(card, 'schedule') and card.schedule.next_review <= timezone.now():
                    cards.append(card)
                elif not hasattr(card, 'schedule'):
                    cards.append(card)
            except:
                cards.append(card)

        return cards[:10]

    cards_to_study = await get_study_cards()

    if not cards_to_study:
        await callback.message.answer("🎉 Нет карточек для изучения!")
        await callback.answer()
        return

    card = cards_to_study[0]

    await state.update_data(
        current_card_id=card.id,
        test_mode=True,
        start_time=datetime.now().timestamp()
    )
    await state.set_state(StudyStates.waiting_for_answer)

    study_text = f"""
🧠 **Изучение**

Переведи слово:
**{card.word}**
"""

    if card.example:
        study_text += f"\n_Пример: {card.example}_"

    await callback.message.answer(study_text, parse_mode="Markdown")
    await callback.answer()


@dp.message()
async def handle_text_message(message: Message):
    telegram_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'language_code': message.from_user.language_code
    }

    telegram_user = await get_or_create_user(telegram_data)

    search_text = message.text.lower().strip()

    @sync_to_async
    def find_card(text):
        return Card.objects.filter(
            user=telegram_user.user,
            word__iexact=text
        ).first()

    card = await find_card(search_text)

    if card:
        card_text = f"""
📚 **Найдена карточка:**

**{card.word}** — {card.translation}
"""

        if card.example:
            card_text += f"\n_Пример: {card.example}_"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Тест", callback_data="test")]
        ])

        await message.answer(card_text, reply_markup=keyboard, parse_mode="Markdown")
        await log_message(telegram_user, "word_search", f"Найдено: {card.word}")
    else:
        help_text = """
🤔 Не понял тебя. Попробуй:

📚 /today - карточки на сегодня
🎯 /test - быстрый тест  
📊 /progress - твоя статистика
🔗 /link токен - привязать аккаунт
❓ /help - все команды
"""

        await message.answer(help_text)


async def main():
    logger.info("Запуск Telegram бота...")

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в настройках!")
        return

    try:
        me = await bot.get_me()
        logger.info(f"Бот подключен: @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.error(f"Ошибка подключения к Telegram: {e}")
        return

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Запуск polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка polling: {e}")


if __name__ == '__main__':
    asyncio.run(main())