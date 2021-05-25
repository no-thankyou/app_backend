# Backend мобильного приложения
Проект с бекендом мобильного приложения.

#### Запуск:
```bash
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
