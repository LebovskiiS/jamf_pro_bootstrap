FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN useradd -m -u 1000 jamf-api && \
    mkdir -p /app && \
    chown jamf-api:jamf-api /app

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs && chown jamf-api:jamf-api /app/logs

# Переключение на пользователя
USER jamf-api

# Открытие порта
EXPOSE 5000

# Запуск приложения
CMD ["python", "app.py"]
