# add_cities.py
from app import create_app
from models import db, City

app = create_app()
with app.app_context():
    print("Добавление городов РФ...")
    
    for city_name in City.get_defaults():
        existing = City.query.filter_by(name=city_name).first()
        if not existing:
            city = City(name=city_name)
            db.session.add(city)
            print(f"  + {city_name}")
    
    db.session.commit()
    
    # Показываем итог
    cities_count = City.query.count()
    print(f"\n✅ Всего городов в базе: {cities_count}")
    
    # Первые 10 для проверки
    print("\n📋 Примеры городов:")
    for city in City.query.limit(10).all():
        print(f"  - {city.name}")