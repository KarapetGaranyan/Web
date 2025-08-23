from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import os


class Card(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Начальный'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    word = models.CharField('Слово', max_length=200)
    translation = models.CharField('Перевод', max_length=200)
    example = models.TextField('Пример использования', blank=True, null=True)
    note = models.TextField('Примечание', blank=True, null=True)
    difficulty = models.CharField('Уровень сложности', max_length=20,
                                  choices=DIFFICULTY_CHOICES, default='beginner')

    # Поля для интервального повторения
    is_learned = models.BooleanField('Выучено', default=False)
    times_studied = models.IntegerField('Количество изучений', default=0)
    times_correct = models.IntegerField('Правильных ответов', default=0)

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата изменения', auto_now=True)

    class Meta:
        verbose_name = 'Карточка'
        verbose_name_plural = 'Карточки'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.word} - {self.translation}"

    @property
    def accuracy_rate(self):
        if self.times_studied == 0:
            return 0
        return round((self.times_correct / self.times_studied) * 100, 1)

    @property
    def is_due_for_review(self):
        # ИСПРАВЛЕНИЕ: Более безопасная проверка
        try:
            schedule = Schedule.objects.get(card=self)
            return schedule.next_review <= timezone.now()
        except Schedule.DoesNotExist:
            return True
        except:
            return True


class Schedule(models.Model):
    card = models.OneToOneField(Card, on_delete=models.CASCADE, related_name='schedule')
    next_review = models.DateTimeField('Следующее повторение', default=timezone.now)
    interval = models.IntegerField('Интервал (дни)', default=1)
    repetitions = models.IntegerField('Количество повторений', default=0)
    ease_factor = models.FloatField('Коэффициент легкости', default=2.5)
    last_reviewed = models.DateTimeField('Последнее изучение', null=True, blank=True)

    class Meta:
        verbose_name = 'Расписание'
        verbose_name_plural = 'Расписания'

    def __str__(self):
        return f"Расписание для {self.card.word}"

    def calculate_next_review(self, quality):
        if quality < 3:
            self.repetitions = 0
            self.interval = 1
        else:
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease_factor)

            self.repetitions += 1

        # Обновляем коэффициент легкости
        self.ease_factor = max(1.3, self.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

        # Устанавливаем следующую дату
        self.next_review = timezone.now() + timedelta(days=self.interval)
        self.last_reviewed = timezone.now()
        self.save()


class StudySession(models.Model):
    RESULT_CHOICES = [
        ('perfect', 'Идеально'),
        ('correct', 'Правильно'),
        ('hard', 'Сложно'),
        ('incorrect', 'Неправильно'),
        ('failed', 'Провал'),
    ]

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    result = models.CharField('Результат', max_length=20, choices=RESULT_CHOICES)
    quality_score = models.IntegerField('Оценка качества (0-5)', default=3)
    response_time = models.IntegerField('Время ответа (сек)', null=True, blank=True)
    user_answer = models.CharField('Ответ пользователя', max_length=500, blank=True)

    created_at = models.DateTimeField('Дата сессии', auto_now_add=True)

    class Meta:
        verbose_name = 'Сессия изучения'
        verbose_name_plural = 'Сессии изучения'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.card.word} - {self.result}"


class UserStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    total_cards = models.IntegerField('Всего карточек', default=0)
    learned_cards = models.IntegerField('Выученных карточек', default=0)
    total_sessions = models.IntegerField('Всего сессий', default=0)
    correct_answers = models.IntegerField('Правильных ответов', default=0)

    last_study = models.DateTimeField('Последнее изучение', null=True, blank=True)
    streak_days = models.IntegerField('Дней подряд', default=0)

    study_time_minutes = models.IntegerField('Время изучения (мин)', default=0)
    weekly_goal = models.IntegerField('Недельная цель (карточек)', default=50)
    current_week_studied = models.IntegerField('Изучено на этой неделе', default=0)

    class Meta:
        verbose_name = 'Статистика пользователя'
        verbose_name_plural = 'Статистика пользователей'

    def __str__(self):
        return f"Статистика {self.user.username}"

    @property
    def accuracy_rate(self):
        if self.total_sessions == 0:
            return 0
        return round((self.correct_answers / self.total_sessions) * 100, 1)

    @property
    def weekly_progress(self):
        if self.weekly_goal == 0:
            return 0
        return min(100, round((self.current_week_studied / self.weekly_goal) * 100, 1))


class AudioFile(models.Model):
    card = models.OneToOneField(Card, on_delete=models.CASCADE, related_name='audio')
    audio_file = models.FileField('Аудио файл', upload_to='audio/')
    language = models.CharField('Язык', max_length=10, default='en')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Аудио файл'
        verbose_name_plural = 'Аудио файлы'

    def __str__(self):
        return f"Аудио для {self.card.word}"

    def delete(self, *args, **kwargs):
        if self.audio_file and os.path.isfile(self.audio_file.path):
            os.remove(self.audio_file.path)
        super().delete(*args, **kwargs)