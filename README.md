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



# Тестирование

## Запуск тестов

```
# Запуск всех тестов
docker-compose exec moderation-service pytest tests/ -v
# Только US-MOD-01 (B2B события)
docker-compose exec moderation-service pytest tests/test_US-MOD-01.py -v

# Только US-MOD-02 (Очередь)
docker-compose exec moderation-service pytest tests/test_US-MOD-02.py -v

# Только US-MOD-03 (Одобрение)
docker-compose exec moderation-service pytest tests/test_US-MOD-03.py -v

# Только US-MOD-04 (Мягкая блокировка)
docker-compose exec moderation-service pytest tests/test_US-MOD-04.py -v

# Только US-MOD-05 (Жёсткая блокировка)
docker-compose exec moderation-service pytest tests/test_US-MOD-05.py -v

# Только US-MOD-06 (Справочник причин)
docker-compose exec moderation-service pytest tests/test_US-MOD-06.py -v

# Только US-MOD-07 (CRUD причин, ADMIN)
docker-compose exec moderation-service pytest tests/test_US-MOD-07.py -v
```

