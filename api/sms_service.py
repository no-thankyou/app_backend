"""Класс для отправки смс через сервис smstraffic."""

import xml.etree.ElementTree as ET  # noqa: N817, S405

import requests
from django.conf import settings


class SmsException(Exception):
    """Ошибка при отправке смс."""


class SmsTraffic:
    """Класс для отправки смс через сервис smstraffic."""

    def __init__(self):
        """Инициализатор класса."""
        self.login = settings.SMS_TRAFFIC_LOGIN
        self.password = settings.SMS_TRAFFIC_PASSWORD

    def send_sms(self, phone: str, message: str) -> None:
        """Метод для отправки смс на сервис."""
        data = {'login': self.login, 'password': self.password, 'rus': 5,
                'phones': phone, 'message': message}
        if not settings.DEBUG:
            data['originator'] = settings.SMS_TRAFFIC_ORIGINATOR
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        res = requests.post(settings.SMS_TRAFFIC_API, data=data,
                            headers=headers)
        if self._get_code(res.text):
            raise SmsException('Возникла ошибка при отправке смс')

    @staticmethod
    def _get_code(xml_str):
        """Метод для обработки кода успешного ответа от smstraffic."""
        root = ET.fromstring(xml_str)  # noqa: S314
        code = (child.text for child in root if child.tag == 'code')
        return int(''.join(code))
