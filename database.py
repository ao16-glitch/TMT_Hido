from models import db, User, Todo, Habit
from datetime import date, timedelta


def init_database(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hido.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

        if User.query.count() == 0:
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

            habits = [
                Habit(user_id=admin.id, title='Утренняя зарядка', category='спорт', difficulty='средний'),
                Habit(user_id=admin.id, title='Чтение 30 минут', category='личное развитие', difficulty='средний'),
                Habit(user_id=admin.id, title='Медитация', category='умные привычки', difficulty='легкий'),
                Habit(user_id=admin.id, title='Планирование дня', category='продуктивность', difficulty='легкий'),
            ]
            for h in habits:
                db.session.add(h)

            sample_todos = [
                Todo(title='Завершить курсовую',
                     due_date=date.today() + timedelta(days=7),
                     priority=1, category='Учеба', user_id=admin.id),
                Todo(title='Купить продукты',
                     due_date=date.today() + timedelta(days=1),
                     priority=2, category='Дом', user_id=admin.id),
            ]
            for t in sample_todos:
                db.session.add(t)

            db.session.commit()
            print("✅ Тестовые данные созданы (admin / admin123)")