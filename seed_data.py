"""Генерация тестовых данных для сдачи задания A3."""
import random
from datetime import date, timedelta, datetime
from app import app
from models import db, User, Todo, Habit, HabitCompletion, StudyGoal, StudySession, Notification


CATEGORIES = ['Учеба', 'Работа', 'Дом', 'Здоровье', 'Семья', 'Другое']
PRIORITIES = [1, 2, 3]
HABIT_TITLES = [
    'Утренняя зарядка', 'Чтение 30 минут', 'Медитация', 'Планирование дня',
    'Прогулка', 'Вода 2л', 'Дневник', 'Изучение английского', 'Йога',
    'Отказ от соцсетей 2ч', 'Дыхательная гимнастика', 'Растяжка',
]
HABIT_CATEGORIES = ['спорт', 'личное развитие', 'умные привычки', 'продуктивность', 'здоровье']
DIFFICULTIES = ['легкий', 'средний', 'тяжелый']
GOAL_TITLES = ['Математика', 'Программирование', 'Английский', 'Физика', 'История']
NOTIF_TYPES = ['deadline', 'habit_reminder']


with app.app_context():
    print("Очистка старых тестовых данных (кроме admin)...")
    User.query.filter(User.username != 'admin').delete()
    db.session.commit()
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    print("Создаём пользователей...")
    users = [admin]
    for i in range(1, 11):
        u = User(
            username=f'student{i}',
            email=f'student{i}@hido.kz',
            coins=random.randint(0, 500),
            productivity_streak=random.randint(0, 30),
        )
        u.set_password('pass1234')
        db.session.add(u)
        users.append(u)
    db.session.commit()
    print(f"  OK: {len(users)} пользователей")

    print("Создаём 150 задач...")
    for i in range(150):
        u = random.choice(users)
        due = date.today() + timedelta(days=random.randint(-20, 30))
        t = Todo(
            title=f'Задача #{i + 1}: {random.choice(["Сделать", "Завершить", "Проверить", "Подготовить"])} {random.choice(["отчёт", "лабораторную", "проект", "презентацию", "домашку", "эссе"])}',
            description=f'Описание задачи {i + 1}.',
            due_date=due,
            priority=random.choice(PRIORITIES),
            is_done=random.random() < 0.4,
            category=random.choice(CATEGORIES),
            user_id=u.id,
        )
        db.session.add(t)
    db.session.commit()
    print("  OK: 150 задач")

    print("Создаём 40 привычек...")
    habits = []
    for i in range(40):
        u = random.choice(users)
        h = Habit(
            user_id=u.id,
            title=f'{random.choice(HABIT_TITLES)} ({i + 1})',
            category=random.choice(HABIT_CATEGORIES),
            difficulty=random.choice(DIFFICULTIES),
            period=random.choice(['неделя', 'месяц']),
            weekdays='all',
            is_custom=random.random() < 0.5,
        )
        db.session.add(h)
        habits.append(h)
    db.session.commit()
    print("  OK: 40 привычек")

    print("Создаём 60 записей о выполнении привычек...")
    existing_keys = set()
    for i in range(60):
        h = random.choice(habits)
        d = date.today() - timedelta(days=random.randint(0, 30))
        key = (h.id, d)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        c = HabitCompletion(
            habit_id=h.id,
            user_id=h.user_id,
            date=d,
            note=random.choice(['', 'Отлично!', 'Пропустил вчера', 'Продолжаю', '']),
        )
        db.session.add(c)
    db.session.commit()
    print("  OK: выполнений")

    print("Создаём 30 учебных целей...")
    goals = []
    for i in range(30):
        u = random.choice(users)
        g = StudyGoal(
            user_id=u.id,
            title=f'{random.choice(GOAL_TITLES)} — цель {i + 1}',
            daily_target_minutes=random.choice([30, 45, 60, 90, 120]),
            period=random.choice(['daily', 'weekdays', 'weekends']),
        )
        db.session.add(g)
        goals.append(g)
    db.session.commit()
    print("  OK: 30 целей")

    print("Создаём 70 учебных сессий...")
    for i in range(70):
        g = random.choice(goals)
        started = datetime.now() - timedelta(days=random.randint(0, 14),
                                             hours=random.randint(0, 23))
        dur = random.choice([600, 1200, 1500, 1800, 2400])
        s = StudySession(
            user_id=g.user_id,
            goal_id=g.id,
            start_time=started,
            end_time=started + timedelta(seconds=dur),
            duration_seconds=dur,
            was_interrupted=dur < 1500,
            completed_full=dur >= 1500,
            date=started.date(),
        )
        db.session.add(s)
    db.session.commit()
    print("  OK: 70 сессий")

    print("Создаём 50 уведомлений...")
    for i in range(50):
        u = random.choice(users)
        n = Notification(
            user_id=u.id,
            type=random.choice(NOTIF_TYPES),
            message=f'Тестовое уведомление #{i + 1} для {u.username}',
            link='/tasks',
            is_read=random.random() < 0.5,
        )
        db.session.add(n)
    db.session.commit()
    print("  OK: 50 уведомлений")

    print("")
    print("ИТОГО В БАЗЕ:")
    print(f"  users:              {User.query.count()}")
    print(f"  todos:              {Todo.query.count()}")
    print(f"  habits:             {Habit.query.count()}")
    print(f"  habit_completions:  {HabitCompletion.query.count()}")
    print(f"  study_goals:        {StudyGoal.query.count()}")
    print(f"  study_sessions:     {StudySession.query.count()}")
    print(f"  notifications:      {Notification.query.count()}")
    print("")
    print("Готово! Открывайте todos.db в DB Browser и делайте скриншоты.")
