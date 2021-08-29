!(Build Status)[https://github.com/no-thankyou/app_backend/actions/workflows/github-actions.yml/badge?branch=dev]
# Backend мобильного приложения
Проект с бекендом мобильного приложения.

#### Запуск:
```bash
cp .env.example .env
docker-compose build
docker-compose up
```

Будет доступен по адресу http://localhost:8000

#### Применение миграций:
```bash
docker-compose run backend python manage.py migrate
```


#### Первичная инициализация
```bash
docker-compose run backend bash /app/env/init-branch.sh
```
