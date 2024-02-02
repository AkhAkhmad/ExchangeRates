# Официальный образ Python
FROM python:3.8

# Установление рабочей директории в контейнере
WORKDIR /app

# Копирование зависимостей проекта в рабочую директорию
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходный код проекта в рабочую директорию
COPY . .
