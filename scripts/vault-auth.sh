#!/bin/bash

# Скрипт для автоматической аутентификации в Vault и запуска приложения

set -e

# Конфигурация
VAULT_ADDR=${VAULT_ADDR:-"https://vault.your-domain.com"}
VAULT_ROLE_ID=${VAULT_ROLE_ID:-"your-role-id"}
FLASK_ENV=${FLASK_ENV:-"prod"}

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    if ! command -v curl &> /dev/null; then
        log_error "curl не установлен"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq не установлен"
        exit 1
    fi
}

# Получение Secret ID из Vault
get_secret_id() {
    log_info "Получение Secret ID из Vault..."
    
    # Если Secret ID уже есть в переменной окружения, используем его
    if [ -n "$VAULT_SECRET_ID" ]; then
        log_info "Используем существующий Secret ID"
        return 0
    fi
    
    # Получаем новый Secret ID
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"role_id\": \"$VAULT_ROLE_ID\"}" \
        "$VAULT_ADDR/v1/auth/approle/role/$VAULT_ROLE_ID/secret-id")
    
    if [ $? -ne 0 ]; then
        log_error "Ошибка получения Secret ID"
        exit 1
    fi
    
    # Извлекаем Secret ID из ответа
    local secret_id=$(echo "$response" | jq -r '.data.secret_id')
    
    if [ "$secret_id" = "null" ] || [ -z "$secret_id" ]; then
        log_error "Не удалось получить Secret ID из ответа Vault"
        log_error "Ответ: $response"
        exit 1
    fi
    
    export VAULT_SECRET_ID="$secret_id"
    log_info "Secret ID получен успешно"
}

# Проверка подключения к Vault
test_vault_connection() {
    log_info "Проверка подключения к Vault..."
    
    local health_response=$(curl -s "$VAULT_ADDR/v1/sys/health")
    
    if [ $? -ne 0 ]; then
        log_error "Не удается подключиться к Vault"
        exit 1
    fi
    
    local initialized=$(echo "$health_response" | jq -r '.initialized')
    local sealed=$(echo "$health_response" | jq -r '.sealed')
    
    if [ "$initialized" != "true" ]; then
        log_error "Vault не инициализирован"
        exit 1
    fi
    
    if [ "$sealed" != "false" ]; then
        log_error "Vault запечатан"
        exit 1
    fi
    
    log_info "Vault доступен и готов к работе"
}

# Проверка доступа к секретам
test_secret_access() {
    log_info "Проверка доступа к секретам..."
    
    local token_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"role_id\": \"$VAULT_ROLE_ID\", \"secret_id\": \"$VAULT_SECRET_ID\"}" \
        "$VAULT_ADDR/v1/auth/approle/login")
    
    if [ $? -ne 0 ]; then
        log_error "Ошибка аутентификации в Vault"
        exit 1
    fi
    
    local token=$(echo "$token_response" | jq -r '.auth.client_token')
    
    if [ "$token" = "null" ] || [ -z "$token" ]; then
        log_error "Не удалось получить токен аутентификации"
        exit 1
    fi
    
    # Проверяем доступ к секрету
    local secret_response=$(curl -s -H "X-Vault-Token: $token" \
        "$VAULT_ADDR/v1/secret/jamf-bootstrap-$FLASK_ENV")
    
    if [ $? -ne 0 ] || [ "$(echo "$secret_response" | jq -r '.errors')" != "null" ]; then
        log_error "Нет доступа к секретам"
        exit 1
    fi
    
    log_info "Доступ к секретам подтвержден"
}

# Запуск приложения
start_application() {
    log_info "Запуск приложения..."
    
    # Экспортируем переменные окружения
    export VAULT_ADDR
    export VAULT_ROLE_ID
    export VAULT_SECRET_ID
    export FLASK_ENV
    
    # Запускаем приложение
    exec python app.py
}

# Основная функция
main() {
    log_info "Запуск Jamf Pro Bootstrap API с автоматической аутентификацией в Vault"
    
    check_dependencies
    test_vault_connection
    get_secret_id
    test_secret_access
    start_application
}

# Обработка сигналов
trap 'log_info "Получен сигнал завершения, останавливаем приложение..."; exit 0' SIGTERM SIGINT

# Запуск
main "$@"
