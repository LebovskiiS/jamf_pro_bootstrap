# Jamf Pro Bootstrap API

API для обработки зашифрованных запросов от CRM к Jamf Pro с интеграцией HashiCorp Vault и GCP Cloud SQL.

## 🔐 Как сервер автоматически логинится в Vault

### Простой Linux сервер

**На сервере нужно только:**

1. **Установить переменные окружения:**
```bash
export VAULT_ADDR="https://vault.your-domain.com"
export VAULT_ROLE_ID="your-role-id"
export FLASK_ENV="prod"
```

2. **Запустить через скрипт:**
```bash
./scripts/vault-auth.sh
```

**Скрипт автоматически:**
- Получает Secret ID из Vault
- Проверяет подключение
- Запускает приложение

### Systemd Service (опционально)

**На сервере создаете service файл:**

```bash
# Копируете service файл
sudo cp systemd-service.service /etc/systemd/system/

# Включаете и запускаете
sudo systemctl enable jamf-bootstrap-api
sudo systemctl start jamf-bootstrap-api
```

## Безопасная аутентификация в Vault

### Рекомендуемые методы аутентификации:

#### 1. AppRole (рекомендуется для production)
```bash
export VAULT_ADDR="https://your-vault-server.com"
export VAULT_ROLE_ID="your-role-id"
export VAULT_SECRET_ID="your-secret-id"
export FLASK_ENV="prod"
```

#### 2. Token (только для разработки)
```bash
export VAULT_ADDR="https://your-vault-server.com"
export VAULT_TOKEN="your-vault-token"
export FLASK_ENV="dev"
```

## Структура секретов в Vault

### Окружение DEV (`secret/jamf-bootstrap-dev`)

```json
{
  "secret_key": "dev-secret-key-32-chars-long",
  "flask_debug": "True",
  "database_url": "mysql+pymysql://username:password@host:3306/jamf_bootstrap_dev",
  "encryption_key": "dev-encryption-key-32-chars-long",
  "api_secret": "dev-api-secret-key"
}
```

### Окружение PROD (`secret/jamf-bootstrap-prod`)

```json
{
  "secret_key": "prod-secret-key-32-chars-long",
  "flask_debug": "False",
  "database_url": "mysql+pymysql://username:password@host:3306/jamf_bootstrap_prod",
  "encryption_key": "prod-encryption-key-32-chars-long",
  "api_secret": "prod-api-secret-key"
}
```

### Jamf Pro DEV (`secret/jamf-pro-dev`)

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

### Jamf Pro PROD (`secret/jamf-pro-prod`)

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

## Структура запросов

### Пример тела запроса от CRM:

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

### Зашифрованный запрос к API:

```json
{
  "crm_id": "crm-123",
  "request_type": "create",
  "payload": "encrypted-employee-data",
  "encrypted_key": "encrypted-key-from-vault"
}
```

## API Endpoints

### 1. Проверка здоровья API
```
GET /api/health
```

### 2. Создание запроса от CRM
```
POST /api/request
Headers: X-API-Key: your-api-secret
Body:
{
  "crm_id": "crm-123",
  "request_type": "create",
  "payload": "encrypted-payload-data",
  "encrypted_key": "encrypted-key-from-vault"
}
```

### 3. Получение статуса запроса
```
GET /api/request/{request_id}
Headers: X-API-Key: your-api-secret
```

### 4. Получение всех запросов CRM
```
GET /api/requests/crm/{crm_id}
Headers: X-API-Key: your-api-secret
```

### 5. Обработка ожидающих запросов
```
POST /api/process
Headers: X-API-Key: your-api-secret
```

## Установка и запуск

### Для разработки:
```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
export VAULT_ADDR="https://your-vault-server.com"
export VAULT_TOKEN="your-vault-token"
export FLASK_ENV="dev"

# Запуск приложения
python app.py
```

### Для production (Linux сервер):
```bash
# Установка зависимостей
sudo apt-get update
sudo apt-get install -y curl jq

# Настройка переменных окружения
export VAULT_ADDR="https://vault.your-domain.com"
export VAULT_ROLE_ID="your-role-id"
export FLASK_ENV="prod"

# Запуск через скрипт (автоматически получает Secret ID)
./scripts/vault-auth.sh
```

## Структура базы данных

### Таблица `jamf_requests`
- `id` - Primary Key
- `request_id` - Уникальный ID запроса (UUID)
- `crm_id` - ID CRM системы
- `jamf_pro_id` - ID в Jamf Pro (после обработки)
- `status` - Статус: pending, processing, completed, failed
- `request_type` - Тип запроса: create, update, delete
- `payload` - Зашифрованные данные запроса
- `encrypted_key` - Зашифрованный ключ для расшифровки
- `created_at` - Время создания
- `updated_at` - Время обновления
- `error_message` - Сообщение об ошибке
- `processed_at` - Время обработки

## Безопасность

- Все секреты хранятся в HashiCorp Vault
- Поддержка безопасных методов аутентификации (AppRole)
- API защищен ключами аутентификации
- Данные передаются в зашифрованном виде
- Поддержка двух окружений (dev/prod)
- Автоматическое создание таблиц в GCP Cloud SQL
- Идемпотентность запросов через idempotency_key

## Настройка Vault

### Создание AppRole для production:

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
EOF

# Создание AppRole
vault write auth/approle/role/jamf-bootstrap \
  token_policies="jamf-bootstrap-policy" \
  token_ttl=1h \
  token_max_ttl=4h

# Получение Role ID и Secret ID
vault read auth/approle/role/jamf-bootstrap/role-id
vault write -f auth/approle/role/jamf-bootstrap/secret-id
```
