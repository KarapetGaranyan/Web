from django.contrib import admin
from .models import Card, Schedule, StudySession, UserStats

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['word', 'translation', 'difficulty', 'user', 'created_at']
    list_filter = ['difficulty', 'created_at']
    search_fields = ['word', 'translation']
    list_per_page = 50

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['card', 'next_review', 'interval', 'repetitions']
    list_filter = ['next_review']

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ['card', 'user', 'result', 'created_at']
    list_filter = ['result', 'created_at']

@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_cards', 'learned_cards', 'accuracy_rate', 'last_study']
    readonly_fields = ['accuracy_rate']