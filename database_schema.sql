-- Схема базы данных для Jamf Pro Bootstrap API
-- PostgreSQL

-- Создание таблицы запросов
CREATE TABLE IF NOT EXISTS jamf_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) UNIQUE NOT NULL,
    crm_id VARCHAR(255) NOT NULL,
    jamf_pro_id VARCHAR(255),
    
    -- Статус и тип запроса
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    request_type VARCHAR(100) NOT NULL CHECK (request_type IN ('create', 'update', 'delete')),
    
    -- Зашифрованные данные (всегда в base64)
    payload TEXT NOT NULL,  -- Зашифрованные данные сотрудника
    encrypted_key VARCHAR(500) NOT NULL,  -- Зашифрованный ключ для расшифровки
    
    -- Метаданные
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Обработка ошибок
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Безопасность
    encryption_version VARCHAR(10) DEFAULT 'v1',
    checksum VARCHAR(64)  -- SHA256 хеш для проверки целостности
);

-- Создание индексов для производительности
CREATE INDEX IF NOT EXISTS idx_jamf_requests_crm_id ON jamf_requests(crm_id);
CREATE INDEX IF NOT EXISTS idx_jamf_requests_status ON jamf_requests(status);
CREATE INDEX IF NOT EXISTS idx_jamf_requests_created_at ON jamf_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_jamf_requests_request_type ON jamf_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_jamf_requests_processed_at ON jamf_requests(processed_at);

-- Создание индекса для очистки старых запросов
CREATE INDEX IF NOT EXISTS idx_jamf_requests_cleanup ON jamf_requests(created_at, status) 
WHERE status IN ('completed', 'failed');

-- Создание функции для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создание триггера для автоматического обновления updated_at
CREATE TRIGGER update_jamf_requests_updated_at 
    BEFORE UPDATE ON jamf_requests 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Создание представления для статистики
CREATE OR REPLACE VIEW jamf_requests_stats AS
SELECT 
    status,
    request_type,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_processing_time_seconds,
    MIN(created_at) as earliest_request,
    MAX(created_at) as latest_request
FROM jamf_requests 
GROUP BY status, request_type;

-- Создание представления для CRM статистики
CREATE OR REPLACE VIEW crm_stats AS
SELECT 
    crm_id,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_requests,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_requests,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_requests,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_processing_time_seconds
FROM jamf_requests 
GROUP BY crm_id;

-- Комментарии к таблице
COMMENT ON TABLE jamf_requests IS 'Таблица для хранения запросов к Jamf Pro';
COMMENT ON COLUMN jamf_requests.payload IS 'Зашифрованные данные сотрудника в формате base64';
COMMENT ON COLUMN jamf_requests.encrypted_key IS 'Зашифрованный ключ для расшифровки данных в формате base64';
COMMENT ON COLUMN jamf_requests.checksum IS 'SHA256 хеш оригинальных данных для проверки целостности';
COMMENT ON COLUMN jamf_requests.encryption_version IS 'Версия алгоритма шифрования';
COMMENT ON COLUMN jamf_requests.retry_count IS 'Количество попыток обработки запроса';
