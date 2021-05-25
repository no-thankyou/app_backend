"""Тесты для запросов api."""
import datetime

import pytest
import pytz
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from api.models import User, Favorite, Event, Participation, SMSAuth
from api.tests.conftest import JWTClient
from api.views import Pagination


class TestUsers(TestCase):
    client_class = JWTClient

    @classmethod
    def setUpTestData(cls):
        call_command('seed')
        for number in range(1, 7):
            phone = f'+7111111112{number}'
            User.objects.create(phone=phone, username=phone)
            Participation.objects.create(user_id=number, event_id=35)
            Favorite.objects.create(user_id=1, event_id=number)
            Participation.objects.create(user_id=1, event_id=number)

    def setUp(self) -> None:
        self.anon_client = self.client_class()
        self.login_user()

    def login_user(self):
        user = User.objects.get(pk=1)
        self.client.force_login(user)

    def test_get_current_user_without_auth(self):
        """Получение текущего пользователя без авторизации."""
        current_user = self.anon_client.get('/api/user/')
        assert current_user.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self):
        """Получение текущего пользователя с авторизацией."""
        response = self.client.get('/api/user/')
        assert response.status_code == status.HTTP_200_OK

    def test_update_profile(self):
        """Обновление профиля текущего пользователя."""
        # TODO добавить проверку фото
        data = {'last_name': 'doe', 'first_name': 'john',
                'city': [{'name': 'Москва'}], 'profession': 'ds',
                'competences': [{'name': 'IT'}], 'about': 'ds',
                'website': 'ds', 'telegram': 'ds', 'instagram': 'ds'}

        current_user = self.client.put('/api/user/', data=data,
                                       format='multipart')
        assert current_user.status_code == status.HTTP_200_OK
        del current_user.json()['photo']
        assert current_user.json() == data

        # удаляем все данные
        del_data = {key: '' for key in data}
        del_data |= {'city': [], 'competences': []}
        del_update = self.client.put('/api/user/', data=del_data)
        # cм TODO
        del del_update.json()['photo']
        assert del_update.status_code == status.HTTP_200_OK
        assert not any(bool(value) for value in del_update.json().values())

    def test_update_with_error(self):
        """Тест ошибки при обновлении полей пользователя."""
        new_data = {1: '12.03.2021'}
        current_user = self.client.put('/api/user/', data=new_data)
        assert current_user.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_users_without_auth(self):
        """Получение списка пользователей без авторизации."""
        users = self.anon_client.get('/api/users/')
        assert users.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_users(self):
        """Получение списка пользователей с авторизацией."""
        # проверка фильтрации для получения списка активных пользователей
        user = User.objects.get(pk=10)
        user.is_active = False
        user.save()
        users = self.client.get('/api/users/')
        assert users.status_code == status.HTTP_200_OK
        assert len(users.json()['results']) > 1
        users_count = User.objects.count()
        assert len(users.json()['results']) != users_count

    def test_get_users_with_photo(self):
        """Получение списка пользователей с фото."""
        # при запуске команды seed создаются 5 пользователей с фото
        users_count = User.objects.count()
        users = self.client.get('/api/users/')
        assert users.status_code == status.HTTP_200_OK
        assert len(users.json()['results']) != users_count
        assert all(user['photo'] for user in users.json()['results'])

    def test_user_events_pagination(self):
        """Тест пагинации пользователей и событий."""
        users = self.client.get('/api/users/')
        events = self.client.get('/api/events/')
        users_count = User.objects.count()
        events_count = Event.objects.count()
        assert len(users.json()['results']) == Pagination.page_size
        assert len(users.json()['results']) != users_count
        assert len(events.json()['results']) == Pagination.page_size
        assert len(events.json()['results']) != events_count

    def test_other_pagination(self):
        """Тест пагинации для списков: избранного, участников, событий."""
        # список событий, в которых учавствует пользователь
        events = self.client.get('/api/users/1/events/')
        assert len(events.json()['results']) == Pagination.page_size
        # список участников
        participants = self.client.get('/api/events/35/users/')
        assert len(participants.json()['results']) == Pagination.page_size

    def test_filter_users(self):
        """Получение отфильтрованного списка пользователей."""
        users = self.client.get('/api/users/')
        users_by_competence = self.client.get('/api/users/?competences=IT')

        assert users_by_competence.status_code == status.HTTP_200_OK
        assert (len(users.json()['results']) >
                len(users_by_competence.json()['results']))
        # Выбираем пользователя без фото, указываем компетенции
        user = User.objects.get(pk=10)
        user.competences.add(2, 3)
        file = ContentFile('text', 'name')
        user.photo = file
        user.save()
        # проверяется, есть ли такая компетенция у пользователей
        assert all(user for user in users_by_competence.json()['results'] if
                   'IT' in user['competences'])
        users_by_competences_empty = self.client.get(
            '/api/users/?competences=IT,Маркетинг,Финансы')
        assert len(users_by_competences_empty.json()['results']) == 0
        users_by_competences = self.client.get(
            '/api/users/?competences=IT,Финансы')
        assert len(users_by_competences.json()['results']) > 0

        assert all(user for user in users_by_competence.json()['results']
                   if user['competences'] == ['IT', 'Финансы'])

    def test_order_users(self):
        """Получение отфильтрованного по дате списка пользователей."""
        user = User.objects.get(pk=2)
        user.date_of_registration = '2021-01-02'
        user.save()
        order_asc = self.client.get(
            '/api/users/?ordering=date_of_registration')
        order_des = self.client.get(
            '/api/users/?ordering=-date_of_registration')
        assert order_asc.status_code == status.HTTP_200_OK
        assert order_des.status_code == status.HTTP_200_OK
        assert order_asc.json()['results'][0] != order_des.json()['results'][0]

    def test_get_user_without_auth(self):
        """Получение пользователя без авторизации."""
        user = self.anon_client.get('/api/users/6/')
        assert user.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user(self):
        """Получение пользователя."""
        user_db = User.objects.get(pk=1)
        user = self.client.get('/api/users/1/')
        assert user.status_code == status.HTTP_200_OK
        assert user.json()['phone'] == user_db.phone

    # События

    def test_get_events_without_auth(self):
        """Получение списка событий без авторизации."""
        events = self.anon_client.get('/api/events/')
        assert events.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_events(self):
        """Получение списка событий с авторизацией."""
        events = self.client.get('/api/events/')
        assert events.status_code == status.HTTP_200_OK
        assert len(events.json()['results']) > 0

    def test_get_filter_events(self):
        """Получение списка событий с учетом их актуальности."""
        events = self.client.get('/api/events/')
        assert events.status_code == status.HTTP_200_OK
        assert len(events.json()['results']) > 0
        # Уменьшаем у всех событий дату, чтобы фильтр никто не прошел
        for event in Event.objects.iterator():
            event.start_date -= datetime.timedelta(days=1000)
            event.save()
        empty_events = self.client.get('/api/events/')

        assert len(empty_events.json()['results']) == 0
        # Возвращаем даты к актуальным у 4 событий
        for number in range(1, 5):
            event = Event.objects.get(pk=number)
            event.start_date += datetime.timedelta(days=1000)
            event.save()
        not_empty_events = self.client.get('/api/events/')
        assert len(not_empty_events.json()['results']) == 4

    def test_get_event_without_auth(self):
        """Получение события без авторизации."""
        event = self.anon_client.get('/api/events/1/')
        assert event.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_event(self):
        """Получение события с авторизацией."""
        event = self.client.get('/api/events/1/')
        assert event.status_code == status.HTTP_200_OK
        assert len(event.json()) > 0
        assert event.json()['title'] == 'Событие 0'

    def test_get_missing_event(self):
        """Получение отсутсвующего события."""
        missing_event = self.client.get('/api/events/1000/')
        assert missing_event.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_events_by_tags(self):
        """Получение отфильтрованных по тегу событий."""
        events = self.client.get('/api/events/?tags=Спорт')

        assert all(event for event in events.json()['results'] if
                   'Спорт' in event['tags'])
        assert events.status_code == status.HTTP_200_OK
        assert len(events.json()['results']) > 0
        events_tags = self.client.get('/api/events/?tags=Спорт,Кино')
        assert events.status_code == status.HTTP_200_OK
        assert all(
            event for event in events_tags.json()['results']
            if event['tags'] == ['Спорт', 'Кино'])
        events_tags_empty = self.client.get(
            '/api/events/?tags=Спорт,'
            'Кино,Путешествие')
        assert len(events_tags_empty.json()['results']) == 0

    def test_filter_events_by_date(self):
        """Получение отфильтрованных по дате событий."""
        events_asc = self.client.get('/api/events/?ordering=start_date')
        events_des = self.client.get('/api/events/?ordering=-start_date')

        assert events_asc.status_code == status.HTTP_200_OK
        assert events_des.status_code == status.HTTP_200_OK
        assert (events_asc.json()['results'][0] !=
                events_des.json()['results'][0])

        events_asc_tags = self.client.get(
            '/api/events/?tags=Спорт&ordering=start_date')
        events_des_tags = self.client.get(
            '/api/events/?tags=Спорт&ordering=-start_date')
        assert (events_asc_tags.json()['results'][0]['start_date'] !=
                events_des_tags.json()['results'][0]['start_date'])
        assert (events_asc_tags.json()['results'][0]['tags'][0] ==
                events_des_tags.json()['results'][0]['tags'][0])
        events_empty = self.client.get(
            '/api/events/?tags=Спорт,Финансы&ordering=start_date')
        assert len(events_empty.json()['results']) == 0

    def test_request_for_participation(self):
        """Post запрос на участие в событии."""
        participation = self.client.post('/api/events/40/')
        assert participation.status_code == status.HTTP_201_CREATED
        repeat_request = self.client.post('/api/events/40/')
        assert repeat_request.status_code == status.HTTP_400_BAD_REQUEST
        neg_result = self.client.post('/api/events/200/')
        assert neg_result.status_code == status.HTTP_404_NOT_FOUND

    def test_unsubscribe_from_participation(self):
        """Отписка от участия."""
        subscription = self.client.post('/api/events/30/')
        assert subscription.status_code == status.HTTP_201_CREATED
        unsubscription = self.client.delete('/api/events/30/')
        assert unsubscription.status_code == status.HTTP_204_NO_CONTENT
        # список участников в событии
        participants = self.client.get('/api/events/30/users/')
        assert len(participants.json()['results']) == 0

    def test_get_tags(self):
        """Получение списка тегов."""
        tags = self.client.get('/api/tags/')
        assert tags.status_code == status.HTTP_200_OK
        assert len(tags.json()) > 0

    def test_get_cities(self):
        """Получение списка городов."""
        cities = self.client.get('/api/cities/')
        assert cities.status_code == status.HTTP_200_OK
        assert len(cities.json()) > 0

    def test_get_competences(self):
        """Получение списка компетенций."""
        competences = self.client.get('/api/competence/')
        assert competences.status_code == status.HTTP_200_OK
        assert len(competences.json()) > 0

    def test_get_participants(self):
        """Запрос на список участников."""
        participants = self.client.get('/api/events/1/users/')
        assert participants.status_code == status.HTTP_200_OK
        assert len(participants.json()) > 0

    def test_participation_list(self):
        """Тест фильтрации событий по актуальной дате."""
        # Берем пользователя без событий
        user_pk = User.objects.last().pk
        user_empty_events = self.client.get(f'/api/users/{user_pk}/events/')
        assert user_empty_events.status_code == status.HTTP_200_OK
        assert len(user_empty_events.json()['results']) == 0
        # Подписываем на участие в актуальном событии
        Participation.objects.create(event_id=user_pk, user_id=user_pk)
        # Подписываем на участие в событии c неактуальной датой
        event = Event.objects.last()
        event.start_date -= datetime.timedelta(days=1000)
        event.save()
        Participation.objects.create(event=event, user_id=user_pk)
        user_filter_by_events = self.client.get(f'/api/users/{user_pk}/events/')
        # Подписались на два, а отображаться должны только актуальные
        assert len(user_filter_by_events.json()['results']) == 1
        assert user_filter_by_events.json()['results'][0]['id'] == user_pk

    def test_get_events_by_participate(self):
        """Запрос на список событий, в которых учавствует пользователь."""
        events_by_participate = self.client.get('/api/users/1/events/')
        assert events_by_participate.status_code == status.HTTP_200_OK
        assert len(events_by_participate.json()) > 0

    # TODO тест часовых поясов
    @pytest.mark.skip(reason='переделать')
    def test_local_time(self):
        """Тест локального времени."""
        current_user = self.client.get('/api/user/')
        user_pk = current_user.json()[0]['id']
        Participation.objects.filter(user_id=user_pk).delete()
        # Устанавливаем актуальную дату по дню
        event = Event.objects.last()
        event.start_date = datetime.datetime.now(pytz.timezone('US/Pacific'))
        event.save()
        # # Проверяем, что событие устарело по времени
        # assert event.start_date < localtime()
        Participation.objects.create(user_id=user_pk, event=event)
        events_by_participate = self.client.get(f'/api/users/{user_pk}/events/')
        # assert len(events_by_participate.json()['results']) == 0
        # Меняем часовой пояс
        # default_tz_time = localtime()
        timezone.activate(pytz.timezone('Pacific/Honolulu'))
        # setup_tz_time = localtime()

        user_events = self.client.get(f'/api/users/{user_pk}/events/')
        assert len(user_events.json()['results']) == 1
        # assert default_tz_time != setup_tz_time


class TestFavorite(TestCase):
    client_class = JWTClient

    @classmethod
    def setUpTestData(cls):
        call_command('seed')
        user = User.objects.get(phone='+71112223344')
        event = Event.objects.get(pk=51)
        Favorite.objects.create(event=event, user=user)

    def setUp(self) -> None:
        self.anon_client = self.client_class()
        self.login_user()

    def login_user(self):
        user = User.objects.get(phone='+71112223344')
        self.client.force_login(user)

    def test_get_favorite(self):
        """Запрос на список избранного."""
        favorite = self.client.get('/api/favorite/')
        assert favorite.status_code == status.HTTP_200_OK
        assert len(favorite.json()) > 0

    def test_create_favorite(self):
        """Запрос на создание избранного."""
        favorite = self.client.post('/api/favorite/', data={'event': 52})
        assert favorite.status_code == status.HTTP_201_CREATED
        favorite_negative = self.client.post('/api/favorite/',
                                             data={'event': 1000})
        assert favorite_negative.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_favorite(self):
        """Запрос на удаление избранного."""
        favorite = self.client.delete('/api/favorite/', data={'event_id': 51})
        fav = self.client.get('/api/favorite/')
        assert favorite.status_code == status.HTTP_204_NO_CONTENT
        assert len(fav.json()) == 0
        fav_negative = self.client.delete('/api/favorite/',
                                          data={'event_id': 200})
        assert fav_negative.status_code == status.HTTP_404_NOT_FOUND


class TestAuth(TestCase):
    """Тест регистрации и получения токенов."""

    client_class = JWTClient

    def setUp(self) -> None:
        """Предуставнленные данные."""
        settings.DEBUG = True
        self.anon_client = self.client_class()

    def test_get_auth_sms(self):
        """Создание пользователя при отправке смс."""
        data = {'phone': '+7111111112'}
        anon_user = self.anon_client.post('/api/send-sms/', data=data)
        created_user = User.objects.filter(phone='+7111111112')
        assert anon_user.status_code == status.HTTP_200_OK
        assert created_user.exists()
        assert created_user[0].password
        password = created_user[0].password
        SMSAuth.objects.filter(phone=data['phone']).delete()
        repeated_request = self.anon_client.post('/api/send-sms/', data=data)
        assert repeated_request.status_code == status.HTTP_200_OK
        user = User.objects.get(phone='+7111111112')
        assert user.password == password

    def test_repeated_sms_auth_request(self):
        """Повторный запрос на регистрацию по смс."""
        data = {'phone': '+7111111115', "password": "1111"}
        self.anon_client.post('/api/send-sms/', data=data)
        repeated_request = self.anon_client.post('/api/send-sms/', data=data)
        assert repeated_request.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_auth_token(self):
        """Получение токена."""
        data = {'phone': '+7111111113', "password": "1111"}
        self.anon_client.post('/api/send-sms/', data=data)
        token = self.anon_client.post('/api/token/', data=data)
        assert token.status_code == status.HTTP_200_OK
        assert 'refresh' and 'access' in token.json()

    def test_bad_token_request(self):
        """Запрос токена без отправки смс."""
        data = {'phone': '+7111111114', "password": "1111"}
        bad_request = self.anon_client.post('/api/token/', data=data)
        assert bad_request.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token_request(self):
        """Запрос на обновление токена."""
        data = {'phone': '+7111111114', "password": "1111"}
        bad_request = self.anon_client.post('/api/token/refresh/', data=data,
                                            format='multipart')
        # попытка получить новую пару токенов до отправки смс и получения токена
        assert bad_request.status_code == status.HTTP_400_BAD_REQUEST
        data = {'phone': '+7111111113', "password": "1111"}
        self.anon_client.post('/api/send-sms/', data=data)
        token = self.anon_client.post('/api/token/', data=data)
        good_request = self.anon_client.post('/api/token/refresh/', data=data,
                                             format='multipart')
        assert token.cookies.get('refresh')
        assert good_request.json()['refresh'] != token.json()['refresh']
