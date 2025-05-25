#!/bin/bash

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

FOLDER=${1:-"tg"}
REPO=${2:-"https://github.com/kalentivan/tg.git"}
NET=${3:-"tg-net"}
IMAGE=${4:-"tg-back"}

# Функция ошибки
error_exit() {
    echo -e "${RED}Ошибка: $1${NC}" >&2
    exit 1
}

echo "📦 Проверка и установка Docker и Compose V2..."

# Установка зависимостей
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release || error_exit "Не удалось установить зависимости"

# Добавление ключа и репозитория Docker, если отсутствует
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    echo "🔑 Добавление ключа Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg || error_exit "Не удалось получить ключ Docker"
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo "📄 Добавление репозитория Docker..."
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
      $(lsb_release -cs) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
fi

# Проверка и установка docker-ce и docker-compose-plugin
if ! command -v docker &>/dev/null; then
    echo "⬇️ Установка Docker..."
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || error_exit "Не удалось установить Docker"
else
    echo "✅ Docker уже установлен"
fi

# Проверка docker compose V2
if ! docker compose version &>/dev/null; then
    echo "⬇️ Установка Compose V2 (plugin)..."
    sudo apt-get install -y docker-compose-plugin || error_exit "Не удалось установить docker compose plugin"
else
    echo "✅ Docker Compose V2 уже установлен"
fi

# Запуск и enable Docker
if ! systemctl is-active --quiet docker; then
    echo "▶️ Запуск Docker..."
    sudo systemctl start docker || error_exit "Не удалось запустить Docker"
    sudo systemctl enable docker
else
    echo "✅ Docker уже запущен"
fi

# Очистка старого
echo "🧹 Очистка кеша Docker..."
docker system prune -f || error_exit "Не удалось очистить кеш"

# Папка проекта
echo "📁 Создание папки $FOLDER..."
mkdir -p "${FOLDER}" || error_exit "Не удалось создать папку"
cd "${FOLDER}" || error_exit "Не удалось перейти в папку"

# Git
if ! command -v git &>/dev/null; then
    echo "🛠 Установка Git..."
    sudo apt-get install -y git || error_exit "Не удалось установить Git"
fi

# Клонирование или обновление
if [ -d ".git" ]; then
    echo "🔄 Репозиторий уже существует, обновляем..."
    git pull origin main || error_exit "Не удалось обновить репозиторий"
else
    echo "⬇️ Клонирование репозитория..."
    git clone "$REPO" . || error_exit "Не удалось клонировать репозиторий"
fi

# Docker-сеть
echo "🌐 Создание сети $NET..."
docker network create "$NET" 2>/dev/null || echo "Сеть уже существует"

# Директории
echo "📂 Создание директорий..."
mkdir -p logs stat pgdata || error_exit "Не удалось создать директории"

# Сборка
echo "🔨 Сборка Docker-образов..."
 docker build -t ${IMAGE} . || error_exit "Не удалось собрать Docker-образы"

# Запуск
echo "🚀 Запуск контейнеров..."
docker compose up -d --force-recreate && docker compose logs -f || error_exit "Не удалось запустить контейнеры"

echo -e "${GREEN}✅ Проект успешно собран и запущен!${NC}"
echo "🔗 FastAPI доступен по адресу: http://localhost:8000"
