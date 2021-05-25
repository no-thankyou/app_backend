"""Фильтры."""
from django_filters import rest_framework
from api.models import User, Event


class ManyToManyFilter(rest_framework.BaseInFilter,
                       rest_framework.CharFilter):
    """Фильтрующие поле."""

    def filter(self, qs, value):  # noqa: A003
        """Метод фильтрации get параметров."""
        if not value:
            return qs

        for val in value:
            qs = qs.filter(**{self.field_name: val})
        return qs


class CompetenceFilter(rest_framework.FilterSet):
    """Фильтр по компетенциям (имя с lookup__in) у пользователя."""

    competences = ManyToManyFilter(field_name='competences__name')

    class Meta:
        """Настройки класса."""

        model = User
        fields = ['competences']


class TagsFilter(rest_framework.FilterSet):
    """Фильтр по тегам (имя с lookup__in) у события."""

    tags = ManyToManyFilter(field_name='tags__name')

    class Meta:
        """Настройки класса."""

        model = Event
        fields = ['tags']
