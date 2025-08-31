# Jamf Pro Policies Configuration

## Как работают политики в Jamf Pro

### 1. Источники политик
- **Jamf Pro интерфейс** - где вы создаете политики
- **Smart Groups** - группы устройств по условиям  
- **Configuration Profiles** - профили настроек
- **Policies** - политики с действиями

### 2. Логика применения
1. **Вы создаете политики** в Jamf Pro интерфейсе
2. **API получает список** существующих политик
3. **API добавляет компьютер** в соответствующую Smart Group
4. **Jamf Pro автоматически применяет** политики к группе
5. **Устройства получают** настройки при следующем check-in

### 3. Кто отправляет настройки
- **Jamf Pro** отправляет настройки на устройства
- **Наш API** только добавляет машины в группы
- **Устройства** сами подключаются к Jamf Pro и получают политики

## Структура политик по отделам

### IT отдел
**Smart Group:** `IT_Computers`
**Политики:**
- `IT_Admin_Rights` - Административные права
- `IT_Developer_Tools` - Xcode, VS Code, Git
- `IT_Server_Access` - VPN, SSH ключи
- `IT_Advanced_Security` - Расширенные настройки безопасности

### HR отдел  
**Smart Group:** `HR_Computers`
**Политики:**
- `HR_Basic_Apps` - Office, браузеры
- `HR_Limited_Rights` - Ограниченные права пользователя
- `HR_Privacy_Policy` - Политики конфиденциальности
- `HR_Systems_Access` - Доступ к HR системам

### Finance отдел
**Smart Group:** `FINANCE_Computers`
**Политики:**
- `Finance_Encryption` - Дополнительное шифрование
- `Finance_Audit` - Аудит доступа
- `Finance_Restricted_Install` - Ограничения на установку ПО
- `Finance_Systems_Access` - Доступ к финансовым системам

### Marketing отдел
**Smart Group:** `MARKETING_Computers`
**Политики:**
- `Marketing_Creative_Apps` - Photoshop, Figma, Sketch
- `Marketing_Social_Media` - Социальные сети
- `Marketing_Design_Tools` - Дизайн-инструменты

### Sales отдел
**Smart Group:** `SALES_Computers`
**Политики:**
- `Sales_CRM_Access` - CRM системы
- `Sales_Mobile_Policy` - Мобильные политики
- `Sales_Customer_Tools` - Инструменты для работы с клиентами

### Default (все остальные)
**Smart Group:** `DEFAULT_Computers`
**Политики:**
- `Default_Basic_Security` - Базовые политики безопасности
- `Default_Office_Apps` - Стандартные приложения
- `Default_Standard_Rights` - Стандартные права

## Настройка в Jamf Pro

### 1. Создание Smart Groups

Перейдите в **Jamf Pro Console > Computer Management > Smart Computer Groups**

#### IT_Computers
```
Criteria:
- Department is "IT"
- OR Employee ID starts with "IT-"
```

#### HR_Computers  
```
Criteria:
- Department is "HR"
- OR Employee ID starts with "HR-"
```

#### FINANCE_Computers
```
Criteria:
- Department is "Finance"
- OR Employee ID starts with "FIN-"
```

### 2. Создание политик

Перейдите в **Jamf Pro Console > Computer Management > Policies**

#### Пример: IT_Admin_Rights
```
General:
- Name: IT_Admin_Rights
- Trigger: Recurring Check-in
- Execution Frequency: Once per computer

Scope:
- Target Computers: IT_Computers (Smart Group)

Payload:
- Accounts: Add user to admin group
- Scripts: Install development tools
```

#### Пример: HR_Basic_Apps
```
General:
- Name: HR_Basic_Apps
- Trigger: Recurring Check-in
- Execution Frequency: Once per computer

Scope:
- Target Computers: HR_Computers (Smart Group)

Payload:
- Packages: Microsoft Office, Chrome
- Configuration Profiles: Basic security settings
```

## API Integration

### Как API работает с политиками

1. **CRM отправляет данные** с полем `department`
2. **API создает запись** в Jamf Pro
3. **API добавляет компьютер** в соответствующую Smart Group (`{DEPARTMENT}_Computers`)
4. **Jamf Pro автоматически** применяет политики к группе
5. **Устройство получает** политики при следующем check-in

### Пример запроса от CRM

```json
{
  "employee_id": "E12345",
  "email": "sergei@pharmacyhub.com",
  "full_name": "User Name",
  "department": "IT",
  "device": {
    "serial": "C02XXXXX",
    "platform": "macOS",
    "os_version": "15.0"
  }
}
```

### Результат обработки

```json
{
  "success": true,
  "jamf_pro_id": 1234,
  "department": "IT",
  "policies_applied": [
    "it_admin_rights",
    "it_developer_tools", 
    "it_server_access"
  ],
  "message": "Computer created and 3 policies applied for IT department"
}
```

## Мониторинг политик

### Проверка применения политик

1. **Jamf Pro Console** > Computer Management > Computers
2. Найдите компьютер по serial number
3. Перейдите на вкладку **Management**
4. Проверьте **Smart Computer Groups** и **Policies**

### Логи API

API логирует применение политик:

```
INFO - Applied policy 'it_admin_rights' to computer 1234
INFO - Request abc-123 processed - Applied 3 policies for IT department
```

## Troubleshooting

### Политики не применяются

1. **Проверьте Smart Groups** - компьютер должен быть в группе
2. **Проверьте Scope политик** - группа должна быть в scope
3. **Проверьте Triggers** - политика должна иметь правильный trigger
4. **Принудительный check-in** - `sudo jamf policy`

### API не может добавить в группу

1. **Проверьте права API пользователя** в Jamf Pro
2. **Проверьте название группы** - должно быть `{DEPARTMENT}_Computers`
3. **Проверьте логи API** для ошибок

## Рекомендации

### Безопасность
- Используйте минимальные права для API пользователя
- Регулярно аудируйте применяемые политики
- Тестируйте политики на тестовых машинах

### Производительность  
- Не создавайте слишком много политик
- Используйте Recurring Check-in вместо Login/Logout
- Группируйте похожие настройки в одну политику

### Мониторинг
- Настройте уведомления о неудачных политиках
- Регулярно проверяйте статус Smart Groups
- Мониторьте логи API для ошибок применения политик
