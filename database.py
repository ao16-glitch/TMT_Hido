from models import db, User, Todo, Habit, HabitCompletion, StudyGoal, StudySession, Notification
from datetime import datetime, timedelta, date


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
            print("Test user created: admin / admin123")

            default_habits = [
                ('Morning exercise', 'sport', 'medium', 'week', 'all', False),
                ('Read 30 minutes', 'personal growth', 'medium', 'week', 'all', False),
                ('Meditation', 'smart habits', 'easy', 'week', 'all', False),
                ('Daily planning', 'productivity', 'easy', 'week', 'all', False),
                ('Save 500 KZT', 'finance', 'hard', 'month', 'all', False),
                ('Cleaning', 'housework', 'medium', 'week', 'all', False),
                ('Walk', 'health', 'easy', 'week', 'all', False),
            ]
            for title, cat, diff, period, days, custom in default_habits:
                h = Habit(
                    user_id=admin.id,
                    title=title,
                    category=cat,
                    difficulty=diff,
                    period=period,
                    weekdays=days,
                    is_custom=custom
                )
                db.session.add(h)

            db.session.commit()
            print("Test habits added")

            sample_todos = [
                Todo(title="Finish coursework", description="Write the conclusion",
                     due_date=date.today() + timedelta(days=7), priority=1,
                     category="Study", user_id=admin.id),
                Todo(title="Buy groceries", due_date=date.today() + timedelta(days=1),
                     priority=2, category="Home", user_id=admin.id),
            ]
            for todo in sample_todos:
                db.session.add(todo)
            db.session.commit()