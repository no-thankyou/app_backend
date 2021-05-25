"""Модуль для работы с Carrot quest."""
import requests
from django.conf import settings


class CarrotQuest:
    """Класс для работы с сервисом Carrot quest."""

    def __init__(self, user_id: int) -> None:
        """Инициализатор класса."""
        self.user_id = f'{settings.CARROT_ID_PREFIX}-{user_id}'
        self.token = settings.AUTH_TOKEN_CQ

    def send_props(self, operations: list[dict]) -> None:
        """Запрос с данными для аналитики."""
        self.__request('props', {'operations': operations})

    def send_event(self, event: str) -> None:
        """Запрос с данными для аналитики."""
        self.__request('events', {'event': event})

    def __request(self, uri, data):
        if not self.token:
            return
        url = f'https://api.carrotquest.io/v1/users/{self.user_id}/{uri}'
        data |= {'auth_token': self.token, 'by_user_id': True}
        requests.post(url, json=data)

    def send_update(self, dict_data: dict[str, str]) -> None:
        """Формат update операции для carrot."""
        self.send_props(self._send_output_data('update_or_create', dict_data))

    @staticmethod
    def _prepare_dict(dict_data: dict[str, str]) -> dict[str, str]:
        """Обработка сериализованных данных для carrot."""
        extra_fields = {'$name': dict_data.get('name', ''),
                        '$email': dict_data.get('адрес электронной почты', ''),
                        '$phone': dict_data.get('Номер телефона', '')}
        extra = ('name', 'адрес электронной почты', 'Номер телефона')

        for field in extra:
            if field in dict_data:
                del dict_data[field]

        dict_data |= extra_fields
        return dict_data

    @staticmethod
    def _send_output_data(carrot_method: str,
                          dict_data: dict[str, str]) -> list:
        """Подготовленные к отправке данные для carrot."""
        prepared_dict = CarrotQuest._prepare_dict(dict_data)
        operations = []
        for k, v in filter(lambda tpl: tpl[1], prepared_dict.items()):
            pattern = {'op': carrot_method, 'value': str(v), 'key': str(k)}
            operations.append(pattern)
        return operations
