"""Модуль сериализаторов."""

from rest_framework import serializers
from rest_framework.utils import model_meta

from api.models import User, SMSAuth, Event, Competence, Tags, Favorite, City


class CompetenceSerializer(serializers.ModelSerializer):
    """Сериализатор модели компетенций."""

    class Meta:
        """Настройки класса."""

        model = Competence
        fields = ('name',)


class CitySerializer(serializers.ModelSerializer):
    """Сериализатор для валидации города."""

    class Meta:
        """Настройки класса."""

        model = City
        fields = ('name',)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор модели пользователя."""

    competences = serializers.SlugRelatedField(slug_field='name',
                                               read_only=True, many=True)
    photo = serializers.SerializerMethodField()
    city = serializers.SlugRelatedField(slug_field='name', read_only=True,
                                        many=True)

    class Meta:
        """Настройки класса."""

        model = User
        fields = ('id', 'phone', 'last_name', 'first_name', 'city',
                  'profession', 'competences', 'about', 'website', 'telegram',
                  'instagram', 'photo', 'subscription_expiration_date',
                  'date_of_registration')

    def get_photo(self, obj):
        """Метод получения полной ссылки на фото профиля."""
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)


class ChangeUserSerializer(serializers.ModelSerializer):
    """Сериализатор для изменения профиля пользователя."""

    competences = CompetenceSerializer(required=False, many=True)
    city = CitySerializer(required=False, many=True)

    class Meta:
        """Настройки класса."""

        model = User
        fields = ('last_name', 'first_name', 'city', 'profession',
                  'competences', 'about', 'website', 'telegram', 'instagram',
                  'photo')

    def to_internal_value(self, data):
        """Десериализация пришедших данных."""
        new_data = {key: value for key, value in data.items()}
        m2m_fields = self._return_m2m_list(self.instance, data)

        for attr, _ in m2m_fields:
            if attr in data:
                new_data[attr] = data[attr]
            return new_data
        return super(ChangeUserSerializer, self).to_internal_value(data)

    def update(self, instance, validated_data):
        """Десериализация пришедших данных."""
        m2m_fields = self._return_m2m_list(instance, validated_data)
        for attr, _ in m2m_fields:
            if attr in validated_data:
                field = getattr(instance, attr)
                field.set(validated_data[attr])
                del validated_data[attr]

        return super(ChangeUserSerializer, self).update(instance,
                                                        validated_data)

    def validate(self, attrs):
        """Валидация пришедших данных."""
        m2m_fields = self._return_m2m_list(self.instance, self.initial_data)
        for attr, model in m2m_fields:
            if attr in self.initial_data:
                fields = [m2m_field for m2m_field in model.objects.iterator()
                          if m2m_field.name in self.initial_data[attr]]
                attrs[attr] = fields
        return attrs

    @staticmethod
    def _return_m2m_list(instance, serializer_data):
        """Возвращает список с m2m полями."""
        info = model_meta.get_field_info(instance)
        m2m_fields = []
        for attr, _ in serializer_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                m2m_fields.append((attr, info.relations[attr].related_model))
        return m2m_fields

    def to_representation(self, instance):
        """Метод проверки возвращаемых данных."""
        data = super().to_representation(instance)

        diff = set(self.initial_data) - set(self.fields.fields)

        if diff:
            raise (serializers.ValidationError(
                {'detail': f'Полей {",".join(diff)} не существует'}))
        return data


class CarrotSerializer(serializers.ModelSerializer):
    """Сериализатор данных для carrot."""

    city = serializers.SlugRelatedField(slug_field='name', required=False,
                                        read_only=True)
    subscription_expiration_date = serializers.DateTimeField(format='%d.%m.%Y')
    date_of_registration = serializers.DateField(format='%d.%m.%Y')
    name = serializers.SerializerMethodField()

    class Meta:
        """Настройки класса."""

        model = User
        fields = ('city', 'profession', 'about', 'website', 'telegram',
                  'instagram', 'subscription_expiration_date',
                  'date_of_registration', 'email', 'phone', 'name')

    def get_field_ru_names(self) -> dict[str, str]:
        """Получение имен полей на рускком языке."""
        fields_names = {}
        for field in self.Meta.model._meta.get_fields():
            if field.name in self.fields:
                fields_names[field.name] = field.verbose_name

        return self._dict_parse(self.data, fields_names)

    def get_name(self, obj: User) -> str:
        """Получение полного имени пользователя."""
        return f'{obj.first_name} {obj.last_name}'

    @staticmethod
    def _dict_parse(base: dict, names: dict) -> dict[str, str]:
        """Метод сопоставления поля модели с его аналогом на русском языке."""
        return {names.get(key, key): val for key, val in base.items()}


class SMSSerializer(serializers.ModelSerializer):
    """Сериализатор для валидации номера."""

    class Meta:
        """Настройки класса."""

        model = SMSAuth
        fields = ('phone',)


class TagsFieldsSerializer(serializers.ModelSerializer):
    """Сериализатор модели тегов."""

    class Meta:
        """Настройки класса."""

        model = Tags
        fields = ('name',)


class EventSerializer(serializers.ModelSerializer):
    """Сериализатор модели события."""

    tags = serializers.SlugRelatedField(slug_field='name', read_only=True,
                                        many=True)
    photos = serializers.SerializerMethodField()

    class Meta:
        """Настройки класса."""

        model = Event
        fields = '__all__'

    def get_photos(self, obj):
        """Получение списка картинок события."""
        photos = []
        request = self.context.get('request')
        for photo in obj.photos.all():
            photos.append(request.build_absolute_uri(photo.photo.url))
        return photos


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор модели тегов."""

    class Meta:
        """Настройки класса."""

        model = Tags
        fields = '__all__'


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор модели избранного."""

    class Meta:
        """Настройки класса."""

        model = Favorite
        fields = ('event',)


class UserListSerializer(serializers.ModelSerializer):
    """Сериализатор для участников в событие."""

    photo = serializers.SerializerMethodField()

    class Meta:
        """Настройки класса."""

        model = User
        fields = ('first_name', 'last_name', 'photo')

    def get_photo(self, obj):
        """Метод получения полной ссылки на фото профиля."""
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
