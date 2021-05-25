FROM python:3.9-slim

RUN mkdir /app && pip install pipenv
WORKDIR /app

ADD Pipfile /app/Pipfile
ADD Pipfile.lock /app/Pipfile.lock

RUN pipenv install --system --dev

ADD . /app

ENTRYPOINT bash -c "./env/init-branch.sh; python manage.py runserver 0:8000"
