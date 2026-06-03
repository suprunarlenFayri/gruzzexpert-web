import os
from app import create_app
from models import db, Workspace, User, City
from dotenv import load_dotenv

load_dotenv()
app = create_app()

with app.app_context():
    # 1. Создаем города
    cities_list = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург']
    for city_name in cities_list:
        if not City.query.filter_by(name=city_name).first():
            db.session.add(City(name=city_name))
    
    # 2. Создаем первый воркспейс
    ws = Workspace.query.filter_by(name="Главный офис").first()
    if not ws:
        ws = Workspace(name="Главный офис")
        db.session.add(ws)
        db.session.commit() # Сохраняем, чтобы получить id воркспейса

    # 3. Создаем тебя (Админа)
    admin_phone = "79991234567" 
    
    if not User.query.filter_by(phone=admin_phone).first():
        admin = User(
            phone=admin_phone,
            name="Главный Админ",
            # Мы убрали role, так как его нет в твоей модели
            workspace_id=ws.id
        )
        admin.set_password("admin123") 
        db.session.add(admin)
        print(f"Админ создан! Логин: {admin_phone}, Пароль: admin123")
    else:
        print("Админ с таким номером уже существует.")
    
    db.session.commit()
    print("Готово! База наполнена.")