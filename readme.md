![Build Status](https://github.com/no-thankyou/app_backend/actions/workflows/github-actions.yml/badge.svg?branch=dev)
# Backend mobile app

#### Run:
```bash
cp .env.example .env
docker-compose build
docker-compose up
```


#### Applying migrations:
```bash
docker-compose run backend python manage.py migrate
```


#### Initialisation
```bash
docker-compose run backend bash /app/env/init-branch.sh
```
