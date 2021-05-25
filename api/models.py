"""Модели приложения."""
from datetime import date

from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Модель пользователя."""

    phone = models.CharField(verbose_name='Номер телефона', max_length=12,
                             unique=True)
    city = models.ManyToManyField('City', verbose_name='Город', blank=True)
    profession = models.CharField('Род деятельности', max_length=400,
                                  blank=True)
    competences = models.ManyToManyField('Competence',
                                         verbose_name='Компетенции',
                                         blank=True)
    about = models.TextField(verbose_name='О себе', blank=True)
    website = models.CharField(verbose_name='Сайт',
                               max_length=100, blank=True)
    telegram = models.CharField(verbose_name='Телеграм',
                                max_length=100, blank=True)
    instagram = models.CharField(verbose_name='Инстаграм',
                                 max_length=100, blank=True)
    photo = models.ImageField(verbose_name='Фото', blank=True,
                              validators=[FileExtensionValidator(
                                  allowed_extensions=['jpg', 'png', 'jpeg'])])
    subscription_expiration_date = models.DateTimeField(
        null=True, verbose_name='Дата окончания подписки')
    date_of_registration = models.DateField(verbose_name='Дата регистрации',
                                            default=date.today)

    USERNAME_FIELD = 'phone'

    def __str__(self):
        """Строкове представление модели."""
        return self.phone


class City(models.Model):
    """Модель города."""

    name = models.CharField(verbose_name='Город', max_length=100, unique=True)

    def __str__(self):
        """Строкове представление модели."""
        return self.name

    class Meta:
        """Настройки модели."""

        verbose_name = 'Город'
        verbose_name_plural = 'Города'


class Competence(models.Model):
    """Модель компетенций."""

    name = models.CharField(verbose_name='Компетенции',
                            max_length=100, unique=True)

    def __str__(self):
        """Строкове представление модели."""
        return self.name

    class Meta:
        """Настройки модели."""

        verbose_name = 'Компетенции'
        verbose_name_plural = 'Компетенции'


class Event(models.Model):
    """Модель события."""

    title = models.CharField(verbose_name='Заголовок', max_length=250)
    description = models.TextField(verbose_name='Описание', blank=True)
    start_date = models.DateTimeField(verbose_name='Дата начала '
                                                   'события')
    end_date = models.DateTimeField(verbose_name='Дата окончания события',
                                    blank=True, null=True)
    address = models.CharField(verbose_name='Адрес', max_length=600)
    tags = models.ManyToManyField('Tags', verbose_name='Теги', blank=True)

    def __str__(self):
        """Строкове представление модели."""
        return self.title

    class Meta:
        """Настройки модели."""

        verbose_name = 'Событие'
        verbose_name_plural = 'События'


class Tags(models.Model):
    """Модель тегов."""

    name = models.CharField(verbose_name='Имя тега', unique=True,
                            max_length=100)
    city = models.ForeignKey('City', verbose_name='Город', blank=True,
                             null=True, on_delete=models.CASCADE)

    def __str__(self):
        """Строкове представление модели."""
        return self.name

    class Meta:
        """Настройки модели."""

        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'


class EventPhoto(models.Model):
    """Модель фото события."""

    photo = models.ImageField(verbose_name='Фото события')
    event = models.ForeignKey(Event, verbose_name='Событие',
                              on_delete=models.SET_NULL, null=True,
                              related_name='photos')

    class Meta:
        """Настройки модели."""

        verbose_name = 'Фото события'
        verbose_name_plural = 'Фото событий'


class SMSAuth(models.Model):
    """Модель смс авторизации."""

    phone = models.CharField(verbose_name='Номер телефона', max_length=12)
    code = models.CharField(verbose_name='Код', max_length=6)
    attempts = models.IntegerField(verbose_name='Попытки', default=0)
    send_at = models.DateTimeField(verbose_name='Дата и время', auto_now=True)
    is_used = models.BooleanField(verbose_name='Использован', default=False)

    class Meta:
        """Настройки модели."""

        verbose_name = 'Смс для авторизации'
        verbose_name_plural = 'Смс для авторизаций'

    def __str__(self):
        """Строковое представление для пользователя."""
        return f'{self.phone} - {self.code}'


class Participation(models.Model):
    """Модель участия пользователя."""

    user = models.ForeignKey(User, verbose_name='Пользователь',
                             on_delete=models.CASCADE, blank=True, null=True)
    event = models.ForeignKey(Event, verbose_name='Событие',
                              on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        """Настройки модели."""

        verbose_name = ''
        verbose_name_plural = 'Участники'

    def __str__(self):
        """Строковое представление для пользователя."""
        return (f'{self.user.first_name} {self.user.last_name}'
                f' {self.user.phone}')


class Favorite(models.Model):
    """Модель избранного."""

    user = models.ForeignKey(User, verbose_name='Пользователь',
                             on_delete=models.CASCADE, blank=True, null=True)
    event = models.ForeignKey(Event, verbose_name='Событие',
                              on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        """Настройки модели."""

        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


from api.signals import *  # noqa: F401, E402, F403
