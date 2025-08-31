# 🔒 Безопасность контейнера

## 🛠️ Инструменты безопасности в контейнере

### **Анализаторы безопасности:**
- ✅ **Trivy** - анализ уязвимостей контейнера
- ✅ **Bandit** - анализ безопасности Python кода
- ✅ **Semgrep** - статический анализ кода
- ✅ **Safety** - проверка уязвимостей зависимостей
- ✅ **pip-audit** - аудит Python пакетов

### **Анализаторы качества кода:**
- ✅ **Black** - форматирование кода
- ✅ **Flake8** - проверка стиля
- ✅ **Pylint** - анализ качества
- ✅ **MyPy** - проверка типов

### **Безопасность контейнера:**
- ✅ **НЕ запускается от root** - пользователь jamf-api (UID 1000)
- ✅ **Ограниченные capabilities** - только необходимые права
- ✅ **no-new-privileges** - запрет повышения привилегий
- ✅ **Автоматический анализ безопасности** при запуске

## 📊 Метрики приложения

### **Доступные метрики на `/metrics`:**
```
http_requests_total{method="POST",endpoint="create_request",status="200"}
http_request_duration_seconds
http_requests_active
container_cpu_usage_percent
container_memory_usage_percent
container_disk_usage_percent
```

## 🚀 Запуск контейнера

### **1. Создание директорий:**
```bash
mkdir -p logs reports security
```

### **2. Запуск контейнера:**
```bash
docker-compose up -d
```

### **3. Проверка логов:**
```bash
# Логи приложения
docker-compose logs -f jamf-bootstrap-api

# Логи безопасности
tail -f logs/security-scan.log
```

## 📋 Отчеты безопасности

### **Автоматически создаются в `/app/reports/`:**
- `trivy-container-report.json` - уязвимости контейнера
- `safety-report.json` - уязвимости Python зависимостей
- `bandit-report.json` - проблемы безопасности кода
- `semgrep-report.json` - статический анализ
- `black-report.txt` - форматирование кода
- `flake8-report.txt` - стиль кода
- `pylint-report.txt` - качество кода
- `mypy-report.txt` - проверка типов
- `security-summary.txt` - сводный отчет

### **Просмотр отчетов:**
```bash
# Сводный отчет
cat reports/security-summary.txt

# Детальные отчеты
ls -la reports/
```

## 🔍 Проверка безопасности

### **Ручной запуск анализа:**
```bash
# Внутри контейнера
docker exec jamf-bootstrap-api /app/security-scan.sh

# Просмотр результатов
docker exec jamf-bootstrap-api cat /app/reports/security-summary.txt
```

### **Проверка пользователя:**
```bash
# Убедиться что контейнер НЕ запущен от root
docker exec jamf-bootstrap-api whoami
# Должно быть: jamf-api

# Проверка UID
docker exec jamf-bootstrap-api id
# Должно быть: uid=1000(jamf-api)
```

## 🚨 Критические метрики

### **Мониторинг безопасности:**
- Количество уязвимостей контейнера
- Количество уязвимостей Python зависимостей
- Количество проблем безопасности в коде
- Количество ошибок приложения

### **Мониторинг производительности:**
- CPU > 80%
- Memory > 85%
- Disk > 90%
- HTTP ошибки > 10/min

## 🔧 Устранение неполадок

### **Проблемы с безопасностью:**
```bash
# Проверка отчетов безопасности
docker exec jamf-bootstrap-api ls -la /app/reports/

# Запуск анализа вручную
docker exec jamf-bootstrap-api /app/security-scan.sh

# Просмотр логов безопасности
docker exec jamf-bootstrap-api tail -f /app/logs/security-scan.log
```

### **Проблемы с правами:**
```bash
# Проверка пользователя
docker exec jamf-bootstrap-api whoami

# Проверка прав на файлы
docker exec jamf-bootstrap-api ls -la /app/
```

## 📋 Чек-лист безопасности

- [ ] Контейнер запущен от пользователя jamf-api (НЕ root)
- [ ] Анализ безопасности выполняется автоматически
- [ ] Отчеты безопасности доступны в /app/reports/
- [ ] Метрики приложения доступны на /metrics
- [ ] Ограниченные capabilities (cap_drop: ALL)
- [ ] no-new-privileges включен
- [ ] Логи безопасности проверяются регулярно
