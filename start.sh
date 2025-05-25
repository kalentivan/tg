#!/bin/bash


# Активация виртуального окружения
source ./venv/bin/activate

# Ждем, пока Postgres не станет доступен
until pg_isready -h $DB_HOST -p $TG_DB_PORT -U $POSTGRES_USER; do
  echo "Waiting for postgres..."
  sleep 2
done

# Создаем базу, если ее нет (предполагается, что есть пользователь с нужными правами)
psql -h $DB_HOST -p $TG_DB_PORT -U $POSTGRES_USER -tc "SELECT 1 FROM pg_database WHERE datname = '${POSTGRES_DB}'" | grep -q 1 || \
psql -h $DB_HOST -p $TG_DB_PORT -U $POSTGRES_USER -c "CREATE DATABASE ${POSTGRES_DB}"

# Применяем миграции alembic
alembic upgrade head

# Запуск Uvicorn (не в фоне, оставляем последним)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
