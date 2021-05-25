"""Обработка сигналов."""
import logging

from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver

from api.carrot_crm_service import CarrotQuest
from api.models import User, Event, Favorite, Participation, Competence
from api.serializers import CarrotSerializer

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=User.competences.through)
def change_user_competences(instance, **kwargs):
    """Сигнал на изменение компетенций пользователя."""
    user_competences = kwargs['pk_set']
    competences = (Competence.objects.filter(id__in=user_competences)
                   .values_list('name', flat=True))
    analytics = CarrotQuest(user_id=instance.pk)
    dict_data = {'Компетенции': ', '.join(competences)}
    analytics.send_update(dict_data)


@receiver(post_save, sender=User)
def create_new_user(instance, **kwargs):
    """Сигнал на создание пользователя."""
    user_data = CarrotSerializer(instance)
    user_fields = user_data.get_field_ru_names()
    analytics = CarrotQuest(user_id=instance.pk)
    analytics.send_update(user_fields)


@receiver(post_save, sender=Favorite)
def create_new_favorite(created, instance, **kwargs):
    """Сигнал на добавление в избранное."""
    if not created:
        return
    event = f'добавить избранное {instance.event.title}'
    analytics = CarrotQuest(user_id=instance.user.id)
    analytics.send_event(event)
    send_notification(**kwargs)


@receiver(post_delete, sender=Favorite)
def delete_favorite(instance, **kwargs):
    """Сигнал на удаление из избранного."""
    event = f'удалить избранное {instance.event.title}'

    analytics = CarrotQuest(user_id=instance.user.id)
    analytics.send_event(event)
    send_notification(**kwargs)


@receiver(post_save, sender=Participation)
def create_new_participation(created, instance, **kwargs):
    """Сигнал на участие в событие."""
    if not created or not hasattr(instance, 'event'):
        return

    event = f'участие в событии {instance.event.title}'
    analytics = CarrotQuest(user_id=instance.user.id)
    analytics.send_event(event)
    send_notification(**kwargs)
