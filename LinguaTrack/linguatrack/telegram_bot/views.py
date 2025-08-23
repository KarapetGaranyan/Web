from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import secrets
from .models import TelegramUser
from .bot import bot, dp


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import secrets
import string

# Импорты моделей
from .models import TelegramUser, BotMessage
from cards.models import Card


@csrf_exempt
@require_POST
async def webhook(request):
    try:
        update_data = json.loads(request.body)
        from aiogram.types import Update

        update = Update(**update_data)
        await dp.feed_update(bot, update)

        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


async def set_webhook(request):
    if not settings.WEBHOOK_URL:
        return JsonResponse({'error': 'WEBHOOK_URL не настроен'})

    webhook_url = f"{settings.WEBHOOK_URL}telegram/webhook/"

    try:
        result = await bot.set_webhook(webhook_url)
        return JsonResponse({
            'status': 'success' if result else 'failed',
            'webhook_url': webhook_url
        })
    except Exception as e:
        return JsonResponse({'error': str(e)})


async def bot_info(request):
    try:
        me = await bot.get_me()
        webhook_info = await bot.get_webhook_info()

        stats = {
            'bot_username': me.username,
            'bot_id': me.id,
            'webhook_url': webhook_info.url,
            'pending_updates': webhook_info.pending_update_count,
            'users_count': await TelegramUser.objects.acount(),
            'active_users': await TelegramUser.objects.filter(is_active=True).acount(),
        }

        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def link_telegram(request):
    # Проверяем, не привязан ли уже аккаунт
    try:
        telegram_user = request.user.telegram_profile
        return render(request, 'telegram_bot/already_linked.html', {
            'telegram_user': telegram_user
        })
    except TelegramUser.DoesNotExist:
        pass

    # Генерируем токен для привязки
    token = secrets.token_urlsafe(32)
    request.session['link_token'] = token
    request.session['link_expires'] = (timezone.now() + timedelta(minutes=10)).timestamp()

    bot_username = "your_bot_username"  # Заменить на реальное имя бота

    context = {
        'token': token,
        'bot_username': bot_username,
        'link_command': f"/link {token}"
    }

    return render(request, 'telegram_bot/link_account.html', context)


def confirm_link(request, token):
    session_token = request.session.get('link_token')
    expires = request.session.get('link_expires')

    if not session_token or session_token != token:
        messages.error(request, 'Неверный токен привязки')
        return redirect('cards:card_list')

    if not expires or datetime.now().timestamp() > expires:
        messages.error(request, 'Токен истек. Попробуйте еще раз')
        return redirect('telegram_bot:link_telegram')

    # Токен валиден, ждем подтверждения из Telegram
    messages.success(request, 'Токен подтвержден! Теперь отправьте команду боту в Telegram')
    return redirect('cards:card_list')