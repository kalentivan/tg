#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

FOLDER=$1
REPO=$2
NET=$3

REPO=${REPO:-"https://github.com/kalentivan/tg.git"}
NET=${NET:-"tg-net"}

# Функция для вывода ошибок и завершения
error_exit() {
    echo -e "${RED}Ошибка: $1${NC}" >&2
    exit 1
}

# 0. Установка Docker, если он ещё не установлен
if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    sudo apt-get update && sudo apt-get install -y docker.io || error_exit "Не удалось установить Docker"
else
    echo "Docker уже установлен"
fi

# 0.1. Запуск и включение Docker-демона, если он ещё не запущен
if ! systemctl is-active --quiet docker; then
    echo "Запуск Docker-демона..."
    sudo systemctl daemon-reload  # Перезагрузка конфигурации службы
    sudo rm -f /var/run/docker.sock  # Удаление старого сокета, если он заблокирован
    sudo systemctl start docker || error_exit "Не удалось запустить Docker-демон"
    sudo systemctl enable docker || error_exit "Не удалось включить автозапуск Docker"
else
    echo "Docker-демон уже запущен"
fi

# 0.2. Проверка, что Docker-демон запущен
if ! docker info >/dev/null 2>&1; then error_exit "Docker-демон не запущен" fi

# 0.3. Установка docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Установка Docker compose..."
    sudo apt-get update && sudo apt-get install -y docker-compose || error_exit "Не удалось установить Docker compose"
else
    echo "Docker compose уже установлен"
fi

# 1. Очистка кеша Docker
echo "Очистка кеша Docker..."
docker system prune -f || error_exit "Не удалось очистить кеш Docker"

# 2. Создание папки tg
echo "Создание папки tg..."
mkdir -p ${FOLDER} || error_exit "Не удалось создать папку tg"

# Переходим в папку tg
cd ${FOLDER} || error_exit "Не удалось перейти в папку tg"

# 3. Проверка и установка Git
if ! command -v git &> /dev/null; then
    echo "Git не установлен. Устанавливаем Git..."
    sudo apt-get update && sudo apt-get install -y git || error_exit "Не удалось установить Git"
fi

# Клонирование репозитория
echo "Клонирование репозитория ${REPO}..."
if [ -d ".git" ]; then
    echo "Репозиторий уже существует, обновляем..."
    git pull origin main || error_exit "Не удалось обновить репозиторий"
else
    git clone ${REPO} . || error_exit "Не удалось клонировать репозиторий"
fi

# 4. Создание сети Docker, если она не существует
echo "Создание сети ${NET}..."
docker network create ${NET} 2>/dev/null || echo "Сеть ${NET} уже существует"

# 5. Проверка и создание необходимых директорий
echo "Создание необходимых директорий..."
mkdir -p logs stat pgdata || error_exit "Не удалось создать директории logs, stat, pgdata"

# 6. Сборка и запуск Docker
echo "Сборка и запуск Docker..."
docker-compose up --build -d || error_exit "Не удалось собрать и запустить Docker"

echo -e "${GREEN}Проект успешно собран и запущен!${NC}"
echo "FastAPI доступен по адресу: http://localhost:8000"
