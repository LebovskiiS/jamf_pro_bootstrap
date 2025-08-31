# Jamf Pro Bootstrap API

API для обработки зашифрованных запросов от CRM к Jamf Pro с интеграцией HashiCorp Vault и Google Cloud SQL.

## Переменные для добавления в Vault

### 1. Секрет `secret/jamf-bootstrap-prod` (НЕ ротируемые)

```json
{
  "secret_key": "prod-secret-key-32-chars-long-here",
  "flask_debug": "False",
  "encryption_key": "prod-encryption-key-32-chars-long-here",
  "api_secret": "prod-api-secret-key-here"
}
```

### 2. Секрет `secret/jamf-pro-prod` (РОТИРУЕМЫЕ)

```json
{
  "url": "https://prod-jamf-pro-instance.com",
  "username": "prod_username",
  "password": "prod_password",
  "client_id": "prod_client_id",
  "client_secret": "prod_client_secret",
  "api_key": "prod_jamf_api_key"
}
```

### 3. Секрет `secret/database-prod` (РОТИРУЕМЫЕ)

```json
{
  "port": "5432",
  "name": "jamf_bootstrap_prod",
  "user": "jamf_user",
  "password": "your-database-password",
  "ssl_mode": "require",
  "ssl_ca": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
}
```

### 4. Секрет `secret/jamf-bootstrap-dev` (НЕ ротируемые)

```json
{
  "secret_key": "dev-secret-key-32-chars-long-here",
  "flask_debug": "True",
  "encryption_key": "dev-encryption-key-32-chars-long-here",
  "api_secret": "dev-api-secret-key-here"
}
```

### 5. Секрет `secret/jamf-pro-dev` (РОТИРУЕМЫЕ)

```json
{
  "url": "https://dev-jamf-pro-instance.com",
  "username": "dev_username",
  "password": "dev_password",
  "client_id": "dev_client_id",
  "client_secret": "dev_client_secret",
  "api_key": "dev_jamf_api_key"
}
```

### 6. Секрет `secret/database-dev` (РОТИРУЕМЫЕ)

```json
{
  "port": "5432",
  "name": "jamf_bootstrap_dev",
  "user": "jamf_user",
  "password": "your-dev-database-password",
  "ssl_mode": "require",
  "ssl_ca": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
}
```

## Настройка Vault

### Создание AppRole:

```bash
# Включение AppRole auth method
vault auth enable approle

# Создание политики
vault policy write jamf-bootstrap-policy -<<EOF
path "secret/jamf-bootstrap-*" {
  capabilities = ["read"]
}
path "secret/jamf-pro-*" {
  capabilities = ["read"]
}
path "secret/database-*" {
  capabilities = ["read"]
}
EOF

# Создание AppRole
vault write auth/approle/role/jamf-bootstrap \
  token_policies="jamf-bootstrap-policy" \
  token_ttl=1h \
  token_max_ttl=4h

# Получение Role ID (запишите его!)
vault read auth/approle/role/jamf-bootstrap/role-id
```

## Настройка Google Cloud PostgreSQL

### Создание экземпляра Cloud SQL PostgreSQL:

```bash
# Создание экземпляра PostgreSQL
gcloud sql instances create jamf-bootstrap-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=your-root-password

# Создание базы данных
gcloud sql databases create jamf_bootstrap_prod \
  --instance=jamf-bootstrap-db

# Создание пользователя
gcloud sql users create jamf_user \
  --instance=jamf-bootstrap-db \
  --password=your-password

# Настройка приватного IP для внутреннего подключения
gcloud sql instances patch jamf-bootstrap-db \
  --require-ssl \
  --authorized-networks=10.0.0.0/8

# Получение внутреннего IP (обычно 10.79.160.3)
gcloud sql instances describe jamf-bootstrap-db \
  --format="value(ipAddresses[1].ipAddress)"
```

## Развертывание на GCP

### 1. Настройка GitHub Secrets

В настройках репозитория GitHub добавьте:
- `DOCKERHUB_USERNAME` - ваш логин Docker Hub
- `DOCKERHUB_TOKEN` - ваш токен Docker Hub

### 2. Автоматическая сборка

При пуше в main/develop или создании тега автоматически:
- Собирается Docker образ
- Загружается в Docker Hub
- Тегируется по версии

### 3. Настройка GCP сервера

```bash
# Подключение к GCP серверу
gcloud compute ssh your-instance-name

# Создание директории
mkdir -p /opt/jamf-bootstrap
cd /opt/jamf-bootstrap

# Создание .env файла
nano .env
```

### 4. Содержимое .env файла

```bash
VAULT_ADDR=https://vault.your-domain.com
VAULT_ROLE_ID=your-role-id-from-vault
FLASK_ENV=prod
POSTGRES_INTERNAL_IP=10.79.160.3
```

### 5. Запуск приложения

```bash
# Скачивание образа
docker pull your-username/jamf-bootstrap-api:latest

# Запуск через docker-compose
docker-compose up -d

# Проверка логов
docker logs jamf-bootstrap-api
```

## API Endpoints

- `GET /api/health` - Проверка здоровья API
- `POST /api/request` - Создание запроса от CRM (требует токен в payload)
- `GET /api/request/{id}` - Получение статуса запроса
- `GET /api/requests/crm/{crm_id}` - Запросы CRM
- `POST /api/process` - Обработка ожидающих запросов (требует токен в payload)

## Структура данных

### Запрос от CRM:
```json
{
  "crm_id": "crm-123",
  "request_type": "create",
  "payload": "encrypted-employee-data-base64",
  "encrypted_key": "encrypted-key-from-vault-base64",
  "token": "valid-token-from-vault"
}
```

### Данные сотрудника (до шифрования):
```json
{
  "employee_id": "E12345",
  "email": "user@example.com", 
  "full_name": "User Name",
  "device": {
    "serial": "C02XXXXX",
    "platform": "macOS",
    "os_version": "15.0"
  },
  "idempotency_key": "b2df428b-..."
}
```

### Структура базы данных PostgreSQL:

#### Таблица `jamf_requests`:
- `id` - Автоинкрементный первичный ключ
- `request_id` - Уникальный UUID запроса
- `crm_id` - ID CRM системы
- `jamf_pro_id` - ID записи в Jamf Pro (после обработки)
- `status` - Статус: pending, processing, completed, failed
- `request_type` - Тип: create, update, delete
- `payload` - Зашифрованные данные сотрудника (base64)
- `encrypted_key` - Зашифрованный ключ для расшифровки (base64)
- `checksum` - SHA256 хеш для проверки целостности
- `encryption_version` - Версия алгоритма шифрования
- `retry_count` - Количество попыток обработки
- `created_at`, `updated_at`, `processed_at` - Временные метки

### Шифрование и аутентификация данных:

1. **CRM получает токен** из Vault для аутентификации
2. **CRM шифрует данные сотрудника** своим ключом
3. **CRM шифрует ключ** ключом из Vault
4. **CRM отправляет запрос** с токеном в payload
5. **API проверяет токен** в payload против Vault
6. **API расшифровывает ключ** своим ключом из Vault
7. **API расшифровывает данные** полученным ключом
8. **API проверяет целостность** через checksum
9. **API обрабатывает данные** и отправляет в Jamf Pro
{
  "employee_id": "E12345",
  "email": "user@example.com",
  "full_name": "User Name",
  "device": {
    "serial": "C02XXXXX",
    "platform": "macOS",
    "os_version": "15.0"
  },
  "idempotency_key": "b2df428b-..."
}
```
