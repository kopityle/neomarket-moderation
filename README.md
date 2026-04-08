# NeoMarket Moderation Service

Сервис модерации товаров: проверка, одобрение, блокировка.

## Требования
- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Git

## Быстрый старт

### 1. Клонировать репозиторий
```bash
git clone https://github.com/Anactasia/neomarket-moderation.git
cd moderation
```

### 2 Запустить с помощью Docker (рекомендуется)
```
# Поднять базу данных
docker-compose up -d postgres

# Применить миграции
docker-compose run --rm moderation-service alembic upgrade head

# Запустить сервис
docker-compose up moderation-service
```

### Переменные окружения

Создай файл .env (папка moderation) и добавь туда переменные окружения из .env.example.:


### 3. Заполнить причины блокировки

Ознакомиться с ними можно в scripts/seed_blocking_reasons.py

```
# Запустить скрипт заполнения справочника
docker-compose run --rm moderation-service python scripts/seed_blocking_reasons.py
```


## 🛠 Основные эндпоинты

### Модерация

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/product-moderation/get-next` | Получить следующий товар на модерацию |
| POST | `/api/v1/product-moderation/products/{id}/approve` | Одобрить товар |
| POST | `/api/v1/product-moderation/products/{id}/decline` | Заблокировать товар |
| GET | `/api/v1/product-moderation/product-blocking-reasons` | Список причин блокировки |

### Внутренние эндпоинты

| Метод | Путь | Описание | Вызывается |
|-------|------|----------|------------|
| POST | `/api/v1/internal/sync-product/{id}` | Синхронизировать товар из B2B | B2B сервис |



### Статусы задач модерации

```
PENDING → IN_PROGRESS → APPROVED (одобрен)
                    ↘ DECLINED (отклонён)

```
PENDING — задача в очереди, ожидает модератора

IN_PROGRESS — модератор взял в работу

APPROVED — товар одобрен

DECLINED — товар заблокирован с указанием причины


## Структура проекта

```
moderation/
├── app/
│   ├── api/                 # Эндпоинты
│   │   ├── moderation.py    # Основные эндпоинты модерации
│   │   └── internal.py      # Внутренние эндпоинты
│   ├── models/              # SQLAlchemy модели
│   │   ├── task.py          # ModerationTask
│   │   ├── snapshot.py      # ProductSnapshot
│   │   ├── decision.py      # ModerationDecision
│   │   ├── reason.py        # BlockingReason
│   │   └── comment.py       # ModerationComment
│   ├── schemas/             # Pydantic схемы
│   │   ├── task.py
│   │   ├── snapshot.py
│   │   ├── decision.py
│   │   ├── reason.py
│   │   ├── comment.py
│   │   └── b2b.py
│   ├── services/            # Бизнес-логика
│   │   ├── moderation_service.py
│   │   └── b2b_client.py    # HTTP клиент для B2B
│   ├── core/                # Утилиты
│   │   ├── database.py
│   │   └── config.py
│   └── main.py              # Точка входа
├── scripts/
│   └── seed_blocking_reasons.py  # Скрипт заполнения причин
├── migrations/              # Alembic миграции
├── tests/                   # Тесты
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Модели данных

### ModerationTask (задача на модерацию)
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | первичный ключ |
| `product_id` | UUID | ID товара из B2B |
| `seller_id` | UUID | ID продавца из B2B |
| `priority` | INT | 0=обычный, 1=высокий |
| `status` | VARCHAR | PENDING/IN_PROGRESS/APPROVED/DECLINED |
| `assigned_to` | UUID | ID модератора из Auth (опционально) |
| `completed_at` | TIMESTAMP | дата завершения |
| `created_at` | TIMESTAMP | дата создания |
| `updated_at` | TIMESTAMP | дата обновления |

### BlockingReason (причина блокировки) — справочник
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | SERIAL | первичный ключ (INTEGER) |
| `code` | VARCHAR | уникальный код (например, 'wrong_photos') |
| `name` | VARCHAR | название причины |
| `description` | TEXT | описание |
| `is_active` | BOOLEAN | активна ли причина |
| `created_at` | TIMESTAMP | дата создания |
| `updated_at` | TIMESTAMP | дата обновления |

### ProductSnapshot (снимок товара)
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | первичный ключ |
| `task_id` | UUID | ссылка на задачу (внешний ключ) |
| `product_data` | JSON | полная копия товара + SKU из B2B |
| `version` | INT | версия снимка |
| `is_initial` | BOOLEAN | первая версия или после изменений |
| `created_at` | TIMESTAMP | дата создания |
| `updated_at` | TIMESTAMP | дата обновления |

### ModerationDecision (решение модератора)
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | первичный ключ |
| `task_id` | UUID | ссылка на задачу (внешний ключ) |
| `moderator_id` | UUID | ID модератора из Auth |
| `decision` | VARCHAR | APPROVED/DECLINED |
| `blocking_reason_id` | INT | ссылка на причину (если DECLINED) |
| `comment` | TEXT | комментарий |
| `created_at` | TIMESTAMP | дата создания |
| `updated_at` | TIMESTAMP | дата обновления |

### ModerationComment (комментарий)
| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | первичный ключ |
| `task_id` | UUID | ссылка на задачу (внешний ключ) |
| `user_id` | UUID | автор (модератор или продавец) |
| `message` | TEXT | текст комментария |
| `is_from_moderator` | BOOLEAN | true = от модератора, false = от продавца |
| `created_at` | TIMESTAMP | дата создания |
| `updated_at` | TIMESTAMP | дата обновления |

## Сводка по типам ID

| Таблица | ID поле | Внешние ключи |
|---------|---------|---------------|
| `moderation_tasks` | UUID | `product_id` (UUID), `seller_id` (UUID) |
| `product_snapshots` | UUID | `task_id` (UUID) |
| `moderation_decisions` | UUID | `task_id` (UUID) |
| `moderation_comments` | UUID | `task_id` (UUID) |
| `blocking_reasons` | INTEGER | — (справочник) |



---

# Тестирование

## Запуск тестов

```
# Запуск всех тестов
docker-compose exec moderation-service pytest tests/ -v

# Тесты причин блокировки
docker-compose exec moderation-service pytest tests/test_blocking_reasons.py -v

# Тесты задач модерации
docker-compose exec moderation-service pytest tests/test_moderation_tasks.py -v
```


---  
  
# Интеграция с другими сервисами
(настройка связи скоро появится)

## B2B Service 
* Получение товара: Moderation запрашивает товар через GET /api/v1/products/{id}

* Отправка результата: Moderation отправляет результат через POST /api/v1/internal/moderation-callback
