"""Модуль путей приложения."""
from django.urls import path

from api.views import (CurrentUserView, SendSmsView, TokenView, EventListView,
                       UsersListView, EventDetailView, UserDetailView,
                       TagsListView, CompetenceListView, UserFavoriteListView,
                       ParticipantsListView, UserParticipationListView,
                       CitiesListView, JWTTokenRefreshView)

urlpatterns = [
    path('token/', TokenView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', JWTTokenRefreshView.as_view(),
         name='token_refresh'),
    path('send-sms/', SendSmsView.as_view()),
    # Пользователи
    path('user/', CurrentUserView.as_view()),
    path('users/', UsersListView.as_view()),
    path('users/<int:pk>/', UserDetailView.as_view()),
    # События
    path('events/<int:pk>/', EventDetailView.as_view()),
    path('events/', EventListView.as_view()),
    # Остальное
    path('competence/', CompetenceListView.as_view()),
    path('tags/', TagsListView.as_view()),
    path('favorite/', UserFavoriteListView.as_view()),
    path('cities/', CitiesListView.as_view()),
    # Участие
    path('events/<int:pk>/users/', ParticipantsListView.as_view()),
    path('users/<int:pk>/events/', UserParticipationListView.as_view()),
]
