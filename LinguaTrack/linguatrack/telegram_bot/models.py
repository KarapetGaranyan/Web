from django.db import models
from django.contrib.auth.models import User


class TelegramUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram_profile')
    telegram_id = models.BigIntegerField('Telegram ID', unique=True)
    username = models.CharField('Telegram Username', max_length=100, blank=True)
    first_name = models.CharField('Имя', max_length=100, blank=True)
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    language_code = models.CharField('Язык', max_length=10, default='ru')

    # Настройки уведомлений
    notifications_enabled = models.BooleanField('Уведомления включены', default=True)
    reminder_time = models.TimeField('Время напоминаний', default='18:00')
    timezone = models.CharField('Часовой пояс', max_length=50, default='Europe/Moscow')

    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    last_interaction = models.DateTimeField('Последнее взаимодействие', auto_now=True)

    class Meta:
        verbose_name = 'Telegram пользователь'
        verbose_name_plural = 'Telegram пользователи'

    def __str__(self):
        return f"@{self.username or self.telegram_id} ({self.user.username})"


class BotMessage(models.Model):
    telegram_user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField('Тип сообщения', max_length=50)
    content = models.TextField('Содержимое')
    sent_at = models.DateTimeField('Отправлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение бота'
        verbose_name_plural = 'Сообщения бота'
        ordering = ['-sent_at']