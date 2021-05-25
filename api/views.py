"""Обработчики запросов."""
import secrets
import string
from datetime import datetime, timedelta

from django.conf import settings
from django.http import Http404, QueryDict
from django.utils.timezone import localtime
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from api.carrot_crm_service import CarrotQuest
from api.filters import CompetenceFilter, TagsFilter
from api.models import (SMSAuth, User, Event, Competence, Tags, Favorite,
                        Participation, City)
from api.serializers import (SMSSerializer, UserSerializer, EventSerializer,
                             TagsSerializer, FavoriteSerializer,
                             UserListSerializer, ChangeUserSerializer,
                             CompetenceSerializer, CitySerializer)
from api.sms_service import SmsTraffic, SmsException


def make_secret_password() -> str:
    """Создание временного пароля."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(20))


class Pagination(PageNumberPagination):
    """Пагинация для списков."""

    page_size = settings.PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = settings.PAGE_SIZE


class AuthMixin:
    """Общие методы для авторизации."""

    def get_error(self, error_msg):
        """Получить объект с ошибкой для ответа."""
        return Response({'error': error_msg},
                        status=status.HTTP_400_BAD_REQUEST)

    def get_last_sms(self, phone):
        """Получить последний актуальный код."""
        send_border = (datetime.now()
                       - timedelta(minutes=settings.SMS_TIME_LIMIT))
        return SMSAuth.objects.filter(phone=phone, send_at__gte=send_border,
                                      is_used=False)

    def _set_cookie(self, request, *args, **kwargs):
        """Создание куки с refresh токеном."""
        response = super().post(request, *args, **kwargs)
        response.set_cookie('refresh', response.data['refresh'],
                            httponly=True)
        return response


class SendSmsView(AuthMixin, APIView):
    """Обработчик отправки смс для авторизации."""

    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=SMSSerializer)
    def post(self, request):
        """Отправка смс с кодом."""
        serializer = SMSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        phone = serializer.data['phone']
        # проверяем кол-во попыток запроса
        total_send_border = (datetime.now()
                             - timedelta(minutes=settings.SMS_LIMIT))
        total_last_sms = SMSAuth.objects.filter(
            phone=phone, send_at__gte=total_send_border)
        if total_last_sms.count() >= settings.SMS_COUNT:
            return self.get_error('превышено кол-во попыток')

        last_sms = self.get_last_sms(phone)
        if last_sms:
            return self.get_error('код можно запросить через минуту')

        # отключаем старые коды
        SMSAuth.objects.filter(phone=phone).update(is_used=True)

        code = 1111
        if not settings.DEBUG:
            code = 1000 + secrets.randbelow(8999)

        SMSAuth.objects.create(phone=phone, code=code)

        user, _ = User.objects.get_or_create(phone=phone, username=phone)
        if not user.password:
            secret_password = make_secret_password()
            user.set_password(str(secret_password))
            user.save()
        try:
            self.send_sms(phone, code)
        except SmsException:
            return self.get_error('Невозможно отправить смс. Попробуйте позже')

        return Response(status=status.HTTP_200_OK)

    def send_sms(self, phone, code):
        """Метод отправки смс через сервис."""
        message = f'Код для авторизации: {code}'
        if settings.DEBUG:
            return
        SmsTraffic().send_sms(phone, message)


class TokenView(AuthMixin, TokenObtainPairView):
    """Расширенная логика выдачи токена."""

    def post(self, request, *args, **kwargs):
        """Проверка кода из смс перед выдачей токена."""
        serializer = SMSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.data['phone']

        last_sms = self.get_last_sms(phone)
        if not last_sms:
            return self.get_error('время кода истекло')

        last_sms = last_sms.first()
        if last_sms.attempts >= settings.CODE_COUNT:
            return self.get_error('кол-во попыток ввода превышено, запросите'
                                  ' код еще раз')

        last_sms.attempts += 1
        if last_sms.code != request.data['password']:
            last_sms.save()
            return self.get_error('код введен неверно')

        last_sms.is_used = True
        last_sms.save()

        user = User.objects.get(phone=phone)
        password = user.password
        user.set_password(str(last_sms.code))
        user.save()

        response = self._set_cookie(request, *args, **kwargs)
        user.password = password
        user.save()
        return response


class JWTTokenRefreshView(AuthMixin, TokenRefreshView):
    """Проверка refresh токена из кук."""

    def post(self, request, *args, **kwargs):
        """Переопределение метода для передачи токена из куков в тело."""
        if 'refresh' not in request.COOKIES:
            return Response({'error': 'token not found'}, status=400)

        if not isinstance(request.data, QueryDict):
            request.data['refresh'] = request.COOKIES['refresh']
            return self._set_cookie(request, *args, **kwargs)

        request.data._mutable = True
        request.data['refresh'] = request.COOKIES['refresh']
        request.data._mutable = False

        return self._set_cookie(request, *args, **kwargs)


# Логика для пользователей
class CurrentUserView(APIView):
    """Получение текущего пользователя."""

    @swagger_auto_schema(responses={200: UserSerializer(many=True)})
    def get(self, request):
        """Get запрос, получения текущего пользователя."""
        user = (User.objects.prefetch_related('competences')
                .get(pk=self.request.user.id))
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(request_body=ChangeUserSerializer)
    def put(self, request):
        """Put запрос, обновления профиля пользователя."""
        user = User.objects.get(pk=self.request.user.id)
        serializer = ChangeUserSerializer(user, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class UsersListView(generics.ListAPIView):
    """Получение списка пользователей."""

    serializer_class = UserSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = CompetenceFilter
    ordering_fields = ['date_of_registration']
    pagination_class = Pagination

    def get_queryset(self):
        """Список только активных пользователей с фото."""
        return (User.objects.prefetch_related('competences')
                .filter(is_active=True).exclude(photo=''))


class UserDetailView(generics.RetrieveAPIView):
    """Получение пользователя."""

    queryset = User.objects.all()
    serializer_class = UserSerializer


# Логика для событий
class EventListView(generics.ListAPIView):
    """Получение списка событий."""

    serializer_class = EventSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = TagsFilter
    ordering_fields = ['start_date']
    pagination_class = Pagination

    def get_queryset(self):
        """Список актуальных событий."""
        today = localtime()
        return (Event.objects.prefetch_related('tags', 'photos')
                .filter(start_date__gte=today).distinct())


class EventDetailView(APIView):
    """Получение события."""

    def get(self, request, pk):
        """Get запрос события."""
        event = Event.objects.filter(pk=pk).prefetch_related('photos').first()
        if not event:
            return Response({'detail': 'Такого события нет'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = EventSerializer(event, context={'request': request})
        analytics = CarrotQuest(user_id=request.user.id)
        analytics.send_event(f'просмотр события {event.title}')
        return Response(serializer.data)

    def post(self, request, pk):
        """Post запрос на участие в событие."""
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({'detail': 'Такого события нет'},
                            status=status.HTTP_404_NOT_FOUND)

        _, created = Participation.objects.get_or_create(event=event,
                                                         user=request.user)
        if not created:
            return Response({'detail': 'Вы уже учавствуете в этом событии'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        """Отписка от участия в событии."""
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({'detail': 'Такого события нет'},
                            status=status.HTTP_404_NOT_FOUND)

        participation = Participation.objects.get(event=event,
                                                  user=request.user)
        participation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompetenceListView(generics.ListAPIView):
    """Получение списка компетенций."""

    queryset = Competence.objects.all()
    serializer_class = CompetenceSerializer


class TagsListView(generics.ListAPIView):
    """Получение списка тегов."""

    queryset = Tags.objects.all()
    serializer_class = TagsSerializer


class CitiesListView(generics.ListAPIView):
    """Получение списка городов."""

    queryset = City.objects.all()
    serializer_class = CitySerializer


class UserFavoriteListView(APIView):
    """Получение списка избранного."""

    def get(self, request):
        """Get запрос, списка избранного пользователя."""
        user = Favorite.objects.filter(user_id=self.request.user.id)
        serializer = FavoriteSerializer(user, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=FavoriteSerializer)
    def post(self, request):
        """Post запрос, создания избранного пользователя."""
        favorite = (Favorite.objects
                    .filter(user_id=self.request.user.id,
                            event_id=request.data['event']).exists())
        serializer = FavoriteSerializer(data=request.data)
        if favorite:
            return Response({'detail': 'Уже добавлено в избранное'},
                            status=status.HTTP_400_BAD_REQUEST)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('event_id', openapi.FORMAT_DECIMAL,
                          type='event_id')])
    def delete(self, request):
        """Delete запрос, для удаления избранного пользователя."""
        try:
            favorite = (Favorite.objects.get(event_id=self.request.data[
                'event_id'], user=self.request.user))
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            raise Http404


class ParticipantsListView(APIView):
    """Запрос на список участников."""

    def get(self, request, pk):
        """Get запрос на список участников."""
        participants = Participation.objects.filter(event_id=pk)
        users = [part.user for part in participants]
        paginator = Pagination()
        result_page = paginator.paginate_queryset(users, request)
        serializer = (UserListSerializer(result_page,
                                         context={'request': request},
                                         many=True))
        return paginator.get_paginated_response(serializer.data)


class UserParticipationListView(APIView):
    """Запрос на список событий, в которых учавствует пользователь."""

    @swagger_auto_schema(responses={200: EventSerializer(many=True)})
    def get(self, request, pk):
        """Получение списка событий, в которых учавствует user."""
        today = localtime()
        participants = (Participation.objects
                        .filter(user_id=pk, event__start_date__gte=today)
                        .order_by('event__start_date'))
        event = [part.event for part in participants]
        paginator = Pagination()
        result_page = paginator.paginate_queryset(event, request)
        serializer = EventSerializer(result_page, context={'request': request},
                                     many=True)
        return paginator.get_paginated_response(serializer.data)
