from django.urls import path
from . import views

app_name = 'cards'

urlpatterns = [
    # Основные страницы
    path('', views.card_list, name='card_list'),
    path('<int:pk>/', views.card_detail, name='card_detail'),
    path('create/', views.card_create, name='card_create'),
    path('<int:pk>/edit/', views.card_edit, name='card_edit'),
    path('<int:pk>/delete/', views.card_delete, name='card_delete'),

    # Изучение
    path('study/', views.study_cards, name='study_cards'),  # Старый режим
    path('study/smart/', views.smart_study, name='smart_study'),  # Новый умный режим
    path('study/next/', views.next_card, name='next_card'),
    path('study/smart/next/', views.next_smart_card, name='next_smart_card'),
    path('study/results/', views.study_results, name='study_results'),

    # Аудио
    path('<int:pk>/generate-audio/', views.generate_audio_view, name='generate_audio'),
    path('<int:pk>/play-audio/', views.play_audio, name='play_audio'),
]