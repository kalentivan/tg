#!/bin/bash

# Активация виртуального окружения
source ./venv/bin/activate

# Запуск Uvicorn (не в фоне, оставляем последним)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
