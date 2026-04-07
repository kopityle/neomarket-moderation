#!/usr/bin/env python
"""
Скрипт для заполнения справочника причин блокировки
Запуск: python scripts/seed_blocking_reasons.py
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.reason import BlockingReason


def seed_blocking_reasons():
    """Заполнить таблицу blocking_reasons начальными данными"""
    
    db = SessionLocal()
    
    reasons = [
        {
            "code": "wrong_photos",
            "name": "Неверные фотографии",
            "description": "Фотографии не соответствуют товару, низкое качество, отсутствуют обязательные ракурсы"
        },
        {
            "code": "incorrect_category",
            "name": "Неверная категория",
            "description": "Товар размещён в неподходящей категории"
        },
        {
            "code": "wrong_price",
            "name": "Неверная цена",
            "description": "Цена явно завышена или занижена относительно рыночной"
        },
        {
            "code": "prohibited_goods",
            "name": "Запрещённый товар",
            "description": "Товар запрещён к продаже на маркетплейсе"
        },
        {
            "code": "poor_description",
            "name": "Плохое описание",
            "description": "Описание неполное, неинформативное или содержит ошибки"
        },
        {
            "code": "copyright_violation",
            "name": "Нарушение авторских прав",
            "description": "Использование чужих фотографий, товарных знаков или брендов без разрешения"
        },
        {
            "code": "misleading_title",
            "name": "Вводящее в заблуждение название",
            "description": "Название товара не соответствует действительности или вводит покупателя в заблуждение"
        },
        {
            "code": "incomplete_specs",
            "name": "Неполные характеристики",
            "description": "Отсутствуют обязательные характеристики товара"
        },
        {
            "code": "out_of_stock",
            "name": "Товар отсутствует на складе",
            "description": "Товар помечен как активный, но остаток на складе нулевой длительное время"
        },
        {
            "code": "wrong_brand",
            "name": "Неверный бренд",
            "description": "Указан неверный бренд производителя"
        },
    ]
    
    added = 0
    skipped = 0
    
    for reason_data in reasons:
        # Проверяем, нет ли уже такой причины
        existing = db.query(BlockingReason).filter(
            BlockingReason.code == reason_data["code"]
        ).first()
        
        if existing:
            print(f"⚠️ Пропущено (уже существует): {reason_data['code']} - {reason_data['name']}")
            skipped += 1
            continue
        
        reason = BlockingReason(
            code=reason_data["code"],
            name=reason_data["name"],
            description=reason_data["description"],
            is_active=True
        )
        db.add(reason)
        added += 1
        print(f"✅ Добавлено: {reason_data['code']} - {reason_data['name']}")
    
    db.commit()
    db.close()
    
    print(f"\n📊 Итог: добавлено {added}, пропущено {skipped}")
    return added


if __name__ == "__main__":
    seed_blocking_reasons()