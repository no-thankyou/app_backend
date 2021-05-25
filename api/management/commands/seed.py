"""Команда для заполнения базы тестовыми данными."""
import random
from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from api.models import City, Competence, Event, Tags, User


class Command(BaseCommand):
    """Команда заполнения БД."""

    help = 'seed database for testing and development.'  # noqa: A003

    def handle(self, *args, **options):
        """Точка входа команды."""
        self.stdout.write('seeding data...')
        self.create_cities()
        self.create_competence()
        self.create_tags()

        self.create_users()
        self.create_events()

        self.stdout.write('done.')

    def create_cities(self):
        """Создание городов."""
        City.objects.all().delete()
        cities = ['Москва', 'Волгоград', 'Санкт-Петербург', 'Краснодар']
        self.cities = []
        for city in cities:
            self.cities.append(City.objects.create(name=city))
        self.stdout.write('Cities created')

    def create_competence(self):
        """Создание компетенций."""
        Competence.objects.all().delete()
        competences = ['Маркетинг', 'IT', 'Финансы', 'История', 'Образование',
                       'Дизайн']
        self.competences = []
        for competence in competences:
            self.competences.append(Competence.objects.create(name=competence))
        self.stdout.write('Competences created')

    def create_tags(self):
        """Создание тегов."""
        Tags.objects.all().delete()
        tags = [('Спорт', None), ('Кино', None), ('Путешествие ', None),
                ('В Москве', 'Москва')]
        self.tags = []
        for name, city in tags:
            name = Tags.objects.create(name=name)
            if city:
                name.city = [obj for obj in self.cities if obj.name == city][0]
            name.save()
            self.tags.append(name)
        self.stdout.write('Tags created')

    def create_users(self):
        """Создание пользователей."""
        User.objects.filter(is_superuser=False).delete()
        file = ContentFile('text', 'name')
        users = [('Константин Константинов', '20.12.2021',
                  '+71231231212'),
                 ('Станислав Станиславов', '22.10.2021', '+71112223344'),
                 ('Ольга Орлова', '12.06.2021', '+72221112323'),
                 ('Александр Александров', '11.11.2021', '+72121212121'),
                 ('Маргарита Нечаева', '11.12.2020', '+73334443344')]
        self.users = []
        for name, date_end, phone in users:
            user = User(phone=phone, username=phone, photo=file)
            user.subscription_expiration_date = (
                make_aware(datetime.strptime(date_end, '%d.%m.%Y')))
            name, surname = name.split(' ')
            user.first_name = name
            user.last_name = surname
            user.save()
            user.competences.set(random.sample(self.competences, 2))
            self.users.append(user)
        self.stdout.write('Users created')

    def create_events(self):
        """Создание событий."""
        events = [(f'Событие {n}', f'Адрес {n}') for n in range(50)]
        date_now = datetime.now()
        self.events = []
        for title, address in events:
            event = Event(title=title, address=address)
            event.start_date = make_aware(date_now + timedelta(
                days=random.randint(0, 14)))  # noqa: S311
            event.save()
            event.tags.set(random.sample(self.tags, 2))
            self.events.append(event)
        self.stdout.write('Events created')
