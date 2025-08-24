from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
import time
from .models import Card, Schedule, StudySession, UserStats, AudioFile
from .forms import CardForm, StudyForm

from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

import openpyxl
from django.contrib import messages
from .forms import ExcelImportForm

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан для {username}!')

            # Автоматический вход после регистрации
            login(request, user)
            return redirect('cards:card_list')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {username}!')
            return redirect('cards:card_list')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')

    return render(request, 'registration/login.html')


# Импорт с обработкой ошибок для Telegram
try:
    from telegram_bot.models import TelegramUser

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from .utils import get_cards_for_review, update_card_statistics, generate_audio_for_card
except ImportError:
    # Базовые функции если utils не доступен
    def get_cards_for_review(user, limit=20):
        return Card.objects.filter(user=user).order_by('?')[:limit]


    def update_card_statistics(card, is_correct, response_time=None):
        card.times_studied += 1
        if is_correct:
            card.times_correct += 1
        card.save()


    def generate_audio_for_card(card):
        return None


@login_required
def card_list(request):
    # Фильтрация
    difficulty = request.GET.get('difficulty', '')
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    cards = Card.objects.filter(user=request.user).select_related('schedule')

    if difficulty:
        cards = cards.filter(difficulty=difficulty)

    if search:
        cards = cards.filter(
            Q(word__icontains=search) |
            Q(translation__icontains=search)
        )

    if status == 'new':
        cards = cards.filter(times_studied=0)
    elif status == 'learning':
        cards = cards.filter(times_studied__gt=0, is_learned=False)
    elif status == 'learned':
        cards = cards.filter(is_learned=True)

    # Карточки к повторению сегодня
    due_cards_count = Card.objects.filter(
        user=request.user,
        schedule__next_review__lte=timezone.now()
    ).count()

    # Получаем или создаем статистику
    stats, created = UserStats.objects.get_or_create(user=request.user)
    if created or stats.total_cards != cards.count():
        stats.total_cards = cards.count()
        stats.learned_cards = Card.objects.filter(user=request.user, is_learned=True).count()
        stats.save()

    context = {
        'cards': cards,
        'stats': stats,
        'due_cards_count': due_cards_count,
        'difficulty_filter': difficulty,
        'status_filter': status,
        'search_query': search,
        'difficulty_choices': Card.DIFFICULTY_CHOICES,
        'status_choices': [
            ('', 'Все'),
            ('new', 'Новые'),
            ('learning', 'Изучаются'),
            ('learned', 'Выученные'),
        ]
    }

    return render(request, 'cards/card_list.html', context)


@login_required
def card_detail(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)

    # Последние 10 сессий для этой карточки
    recent_sessions = StudySession.objects.filter(
        card=card, user=request.user
    )[:10]

    # Информация о расписании
    try:
        schedule = card.schedule
        next_review = schedule.next_review
        is_due = schedule.next_review <= timezone.now()
    except Schedule.DoesNotExist:
        schedule = None
        next_review = None
        is_due = True

    context = {
        'card': card,
        'recent_sessions': recent_sessions,
        'schedule': schedule,
        'next_review': next_review,
        'is_due': is_due,
        'has_audio': hasattr(card, 'audio') and card.audio.audio_file,
    }

    return render(request, 'cards/card_detail.html', context)


@login_required
def card_create(request):
    if request.method == 'POST':
        form = CardForm(request.POST)
        if form.is_valid():
            card = form.save(commit=False)
            card.user = request.user
            card.save()

            # Создаем расписание для новой карточки
            Schedule.objects.create(
                card=card,
                next_review=timezone.now() + timedelta(hours=1)
            )

            # Генерируем аудио (если доступно)
            try:
                generate_audio_for_card(card)
                messages.success(request, 'Карточка создана! Аудио генерируется...')
            except:
                messages.success(request, 'Карточка создана!')

            return redirect('cards:card_detail', pk=card.pk)
    else:
        form = CardForm()

    return render(request, 'cards/card_form.html', {
        'form': form,
        'title': 'Создать карточку'
    })


@login_required
def card_edit(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)

    if request.method == 'POST':
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, 'Карточка обновлена!')
            return redirect('cards:card_detail', pk=card.pk)
    else:
        form = CardForm(instance=card)

    return render(request, 'cards/card_form.html', {
        'form': form,
        'title': 'Редактировать карточку',
        'card': card
    })


@login_required
def card_delete(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)

    if request.method == 'POST':
        card.delete()
        messages.success(request, 'Карточка удалена!')
        return redirect('cards:card_list')

    return render(request, 'cards/card_confirm_delete.html', {'card': card})


@login_required
def study_cards(request):
    return redirect('cards:smart_study')


@login_required
def next_card(request):
    return redirect('cards:smart_study')


@login_required
def smart_study(request):
    cards_to_study = get_cards_for_review(request.user, limit=20)

    if not cards_to_study:
        messages.info(request, 'Нет карточек для повторения! Отлично работаете! 🎉')
        return redirect('cards:card_list')

    # Текущая карточка из сессии
    current_card_id = request.session.get('smart_study_card_id')
    studied_cards = request.session.get('smart_studied_cards', [])
    session_start_time = request.session.get('session_start_time')

    if not session_start_time:
        request.session['session_start_time'] = time.time()

    if not current_card_id or current_card_id in studied_cards:
        # Выбираем следующую карточку
        remaining_cards = [c.id for c in cards_to_study if c.id not in studied_cards]

        if not remaining_cards:
            # Сессия завершена
            session_time = time.time() - request.session.get('session_start_time', time.time())
            total_studied = len(studied_cards)

            # Очищаем сессию
            request.session.pop('smart_study_card_id', None)
            request.session.pop('smart_studied_cards', None)
            request.session.pop('session_start_time', None)

            # Обновляем время изучения
            stats, _ = UserStats.objects.get_or_create(user=request.user)
            stats.study_time_minutes += round(session_time / 60)
            stats.current_week_studied += total_studied
            stats.save()

            messages.success(request,
                             f'🎉 Сессия завершена! Изучено: {total_studied} карточек за {round(session_time / 60, 1)} мин')
            return redirect('cards:study_results')

        current_card_id = remaining_cards[0]
        request.session['smart_study_card_id'] = current_card_id

    card = get_object_or_404(Card, id=current_card_id, user=request.user)

    if request.method == 'POST':
        form = StudyForm(request.POST)
        if form.is_valid():
            user_answer = form.cleaned_data['answer'].strip().lower()
            correct_answer = card.translation.strip().lower()

            is_correct = user_answer == correct_answer

            # Определяем качество ответа для SM-2
            if is_correct:
                if user_answer == card.translation.strip():  # Точное совпадение
                    quality = 5  # perfect
                    result = 'perfect'
                else:
                    quality = 4  # correct
                    result = 'correct'
            else:
                # Проверяем частичное совпадение
                similarity = len(set(user_answer.split()) & set(correct_answer.split()))
                if similarity > 0:
                    quality = 3  # hard
                    result = 'hard'
                else:
                    quality = 2  # incorrect
                    result = 'incorrect'

            # Создаем сессию изучения
            StudySession.objects.create(
                card=card,
                user=request.user,
                result=result,
                quality_score=quality,
                user_answer=form.cleaned_data['answer']
            )

            # Обновляем статистику карточки
            update_card_statistics(card, is_correct)

            # Обновляем расписание по алгоритму SM-2
            schedule, created = Schedule.objects.get_or_create(
                card=card,
                defaults={
                    'next_review': timezone.now() + timedelta(days=1)
                }
            )
            schedule.calculate_next_review(quality)

            # Добавляем в изученные
            if 'smart_studied_cards' not in request.session:
                request.session['smart_studied_cards'] = []
            request.session['smart_studied_cards'].append(card.id)
            request.session.modified = True

            context = {
                'card': card,
                'user_answer': form.cleaned_data['answer'],
                'is_correct': is_correct,
                'quality_score': quality,
                'next_review': schedule.next_review,
                'show_result': True,
                'studied_count': len(request.session['smart_studied_cards']),
                'total_count': len(cards_to_study)
            }

            return render(request, 'cards/smart_study.html', context)
    else:
        form = StudyForm()

    context = {
        'card': card,
        'form': form,
        'show_result': False,
        'studied_count': len(studied_cards),
        'total_count': len(cards_to_study)
    }

    return render(request, 'cards/smart_study.html', context)


@login_required
def next_smart_card(request):
    current_card_id = request.session.get('smart_study_card_id')
    if current_card_id:
        studied_cards = request.session.get('smart_studied_cards', [])
        if current_card_id not in studied_cards:
            studied_cards.append(current_card_id)
            request.session['smart_studied_cards'] = studied_cards
        request.session.pop('smart_study_card_id', None)

    return redirect('cards:smart_study')


@login_required
def study_results(request):
    # Последние сессии
    recent_sessions = StudySession.objects.filter(
        user=request.user
    ).select_related('card')[:20]

    # Статистика за неделю
    week_ago = timezone.now() - timedelta(days=7)
    week_sessions = StudySession.objects.filter(
        user=request.user,
        created_at__gte=week_ago
    )

    week_stats = {
        'total': week_sessions.count(),
        'correct': week_sessions.filter(result__in=['perfect', 'correct']).count(),
        'cards_studied': week_sessions.values('card').distinct().count()
    }

    # Карточки к повторению
    due_cards = Card.objects.filter(
        user=request.user,
        schedule__next_review__lte=timezone.now()
    ).count()

    stats, _ = UserStats.objects.get_or_create(user=request.user)

    # Добавьте вычисления
    cards_left_to_goal = max(0, stats.weekly_goal - stats.current_week_studied)

    context = {
        'recent_sessions': recent_sessions,
        'week_stats': week_stats,
        'due_cards': due_cards,
        'stats': stats,
        'cards_left_to_goal': cards_left_to_goal,  # Новое поле
    }

    return render(request, 'cards/study_results.html', context)

@login_required
def generate_audio_view(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)

    try:
        audio = generate_audio_for_card(card)
        if audio:
            messages.success(request, 'Аудио успешно сгенерировано!')
        else:
            messages.error(request, 'Ошибка генерации аудио')
    except Exception as e:
        messages.error(request, f'Ошибка: {e}')

    return redirect('cards:card_detail', pk=pk)


@login_required
def play_audio(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)

    try:
        audio = card.audio
        if audio.audio_file:
            response = HttpResponse(audio.audio_file.read(), content_type='audio/mpeg')
            response['Content-Disposition'] = f'inline; filename="{card.word}.mp3"'
            return response
    except AudioFile.DoesNotExist:
        pass

    return JsonResponse({'error': 'Аудио не найдено'}, status=404)


# Telegram статистика (если доступна)
if TELEGRAM_AVAILABLE:
    @login_required
    def telegram_stats(request):
        try:
            telegram_user = request.user.telegram_profile

            # Сообщения бота за последнюю неделю
            week_ago = timezone.now() - timedelta(days=7)
            recent_messages = telegram_user.messages.filter(
                sent_at__gte=week_ago
            ).order_by('-sent_at')[:20]

            # Статистика по типам сообщений
            message_stats = {}
            for msg in recent_messages:
                message_stats[msg.message_type] = message_stats.get(msg.message_type, 0) + 1

            context = {
                'telegram_user': telegram_user,
                'recent_messages': recent_messages,
                'message_stats': message_stats,
            }

            return render(request, 'telegram_bot/stats.html', context)

        except TelegramUser.DoesNotExist:
            messages.info(request, 'Сначала подключите Telegram аккаунт')
            return redirect('/telegram/link/')

@login_required
def import_excel(request):
    if request.method == 'POST':
        form = ExcelImportForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']

            try:
                # Читаем Excel файл
                workbook = openpyxl.load_workbook(excel_file)
                sheet = workbook.active

                created_count = 0
                skipped_count = 0

                # Читаем строки, начиная со второй (пропускаем заголовок)
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if len(row) >= 2 and row[0] and row[1]:
                        word = str(row[0]).strip()
                        translation = str(row[1]).strip()

                        # Проверяем, существует ли уже такая карточка
                        if not Card.objects.filter(user=request.user, word__iexact=word).exists():
                            Card.objects.create(
                                user=request.user,
                                word=word,
                                translation=translation,
                                example=str(row[2]).strip() if len(row) > 2 and row[2] else '',
                                difficulty='beginner'
                            )
                            created_count += 1
                        else:
                            skipped_count += 1

                messages.success(
                    request,
                    f'✅ Импорт завершен! Создано: {created_count}, пропущено: {skipped_count}'
                )

            except Exception as e:
                messages.error(request, f'❌ Ошибка импорта: {str(e)}')

            return redirect('cards:card_list')
    else:
        form = ExcelImportForm()

    return render(request, 'cards/import_excel.html', {'form': form})


@login_required
def bulk_delete_cards(request):
    """Массовое удаление выбранных карточек"""
    if request.method == 'POST':
        card_ids = request.POST.getlist('selected_cards')

        if card_ids:
            # Удаляем только карточки текущего пользователя
            deleted_count = Card.objects.filter(
                id__in=card_ids,
                user=request.user
            ).count()

            Card.objects.filter(
                id__in=card_ids,
                user=request.user
            ).delete()

            messages.success(
                request,
                f'✅ Удалено {deleted_count} карточек'
            )
        else:
            messages.warning(request, '⚠️ Не выбрано ни одной карточки')

    return redirect('cards:card_list')
