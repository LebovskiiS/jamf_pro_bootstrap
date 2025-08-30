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
  "host": "your-cloud-sql-instance-ip",
  "port": "3306",
  "name": "jamf_bootstrap_prod",
  "user": "jamf_user",
  "password": "your-database-password",
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
  "host": "your-dev-cloud-sql-instance-ip",
  "port": "3306",
  "name": "jamf_bootstrap_dev",
  "user": "jamf_user",
  "password": "your-dev-database-password",
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

## Настройка Google Cloud SQL

### Создание инстанса Cloud SQL:

```bash
# Создание инстанса MySQL
gcloud sql instances create jamf-bootstrap-db \
  --database-version=MYSQL_8_0 \
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

# Получение IP адреса
gcloud sql instances describe jamf-bootstrap-db \
  --format="value(connectionName)"
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
- `POST /api/request` - Создание запроса от CRM
- `GET /api/request/{id}` - Получение статуса запроса
- `GET /api/requests/crm/{crm_id}` - Запросы CRM
- `POST /api/process` - Обработка ожидающих запросов

## Структура запросов

### Запрос от CRM:
```json
{
  "crm_id": "crm-123",
  "request_type": "create",
  "payload": "encrypted-employee-data",
  "encrypted_key": "encrypted-key-from-vault"
}
```

### Данные сотрудника:
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
