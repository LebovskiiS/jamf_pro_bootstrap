FROM python:3.11-slim

# Установка системных зависимостей и инструментов безопасности
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    git \
    gcc \
    g++ \
    make \
    wget \
    gnupg \
    ca-certificates \
    procps \
    htop \
    net-tools \
    iotop \
    lsof \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Установка Trivy (анализатор уязвимостей)
RUN wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add - \
    && echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y trivy

# Установка инструментов анализа кода и безопасности
RUN pip install --no-cache-dir \
    bandit \
    safety \
    black \
    flake8 \
    pylint \
    mypy \
    pre-commit \
    semgrep \
    pip-audit \
    safety-checker \
    prometheus-client \
    psutil

# Создание пользователя (НЕ root!)
RUN useradd -m -u 1000 jamf-api && \
    mkdir -p /app && \
    chown jamf-api:jamf-api /app

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование конфигурационных файлов для анализаторов
COPY .bandit ./
COPY .flake8 ./
COPY .pylintrc ./
COPY pyproject.toml ./
COPY .pre-commit-config.yaml ./

# Копирование кода приложения
COPY . .

# Создание директорий для логов, отчетов и безопасности
RUN mkdir -p /app/logs /app/reports /app/security && \
    chown -R jamf-api:jamf-api /app/logs /app/reports /app/security

# Создание скрипта анализа безопасности
RUN echo '#!/bin/bash\n\
    echo "🔒 Анализ безопасности контейнера..."\n\
    \n\
    # Анализ уязвимостей контейнера\n\
    echo "🔍 Анализ уязвимостей с Trivy..."\n\
    trivy image --format json --output /app/reports/trivy-container-report.json . 2>/dev/null || true\n\
    \n\
    # Анализ зависимостей Python\n\
    echo "🔍 Анализ уязвимостей Python зависимостей..."\n\
    safety check --json --output /app/reports/safety-report.json 2>/dev/null || true\n\
    pip-audit --format json --output /app/reports/pip-audit-report.json 2>/dev/null || true\n\
    \n\
    # Анализ кода на безопасность\n\
    echo "🔍 Анализ кода на безопасность..."\n\
    bandit -r app/ -f json -o /app/reports/bandit-report.json 2>/dev/null || true\n\
    semgrep scan --config=auto --json --output /app/reports/semgrep-report.json app/ 2>/dev/null || true\n\
    \n\
    # Анализ стиля и качества кода\n\
    echo "🎨 Анализ стиля кода..."\n\
    black --check app/ --diff > /app/reports/black-report.txt 2>&1 || true\n\
    flake8 app/ --output-file=/app/reports/flake8-report.txt 2>/dev/null || true\n\
    pylint app/ --output=/app/reports/pylint-report.txt 2>/dev/null || true\n\
    mypy app/ --output-file=/app/reports/mypy-report.txt 2>/dev/null || true\n\
    \n\
    # Создание сводного отчета\n\
    echo "📋 Создание сводного отчета..."\n\
    echo "=== ОТЧЕТ ПО БЕЗОПАСНОСТИ ===" > /app/reports/security-summary.txt\n\
    echo "Дата: $(date)" >> /app/reports/security-summary.txt\n\
    echo "Контейнер: $(hostname)" >> /app/reports/security-summary.txt\n\
    echo "" >> /app/reports/security-summary.txt\n\
    \n\
    if [ -f /app/reports/trivy-container-report.json ]; then\n\
    echo "🔴 Уязвимости контейнера: $(jq -r ".Vulnerabilities | length" /app/reports/trivy-container-report.json 2>/dev/null || echo "0")" >> /app/reports/security-summary.txt\n\
    fi\n\
    \n\
    if [ -f /app/reports/safety-report.json ]; then\n\
    echo "🔴 Уязвимости Python: $(jq -r ".vulnerabilities | length" /app/reports/safety-report.json 2>/dev/null || echo "0")" >> /app/reports/security-summary.txt\n\
    fi\n\
    \n\
    if [ -f /app/reports/bandit-report.json ]; then\n\
    echo "🔴 Проблемы безопасности кода: $(jq -r ".results | length" /app/reports/bandit-report.json 2>/dev/null || echo "0")" >> /app/reports/security-summary.txt\n\
    fi\n\
    \n\
    echo "" >> /app/reports/security-summary.txt\n\
    echo "✅ Анализ завершен! Результаты в /app/reports/" >> /app/reports/security-summary.txt\n\
    cat /app/reports/security-summary.txt\n\
    ' > /app/security-scan.sh && chmod +x /app/security-scan.sh

# Переключение на пользователя (НЕ root!)
USER jamf-api

# Открытие только нужного порта
EXPOSE 5000

# Запуск приложения с анализом безопасности
CMD ["sh", "-c", "/app/security-scan.sh & python app.py"]
