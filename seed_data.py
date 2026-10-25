"""Generate test data for Assignment A3."""
import random
from datetime import date, timedelta, datetime
from app import app
from models import db, User, Todo, Habit, HabitCompletion, StudyGoal, StudySession, Notification


CATEGORIES = ['Study', 'Work', 'Home', 'Health', 'Family', 'Other']
PRIORITIES = [1, 2, 3]
HABIT_TITLES = [
    'Morning exercise', 'Read 30 min', 'Meditation', 'Daily planning',
    'Walk', 'Water 2L', 'Journal', 'Learn English', 'Yoga',
    'No social media 2h', 'Breathing exercise', 'Stretching',
]
HABIT_CATEGORIES = ['sport', 'personal growth', 'smart habits', 'productivity', 'health']
DIFFICULTIES = ['easy', 'medium', 'hard']
GOAL_TITLES = ['Math', 'Programming', 'English', 'Physics', 'History']
NOTIF_TYPES = ['deadline', 'habit_reminder']


with app.app_context():
    print("Clearing old test data (except admin)...")
    User.query.filter(User.username != 'admin').delete()
    db.session.commit()
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    print("Creating users...")
    users = [admin]
    for i in range(1, 11):
        u = User(
            username=f'student{i}',
            email=f'student{i}@hido.kz',
        )
        u.set_password('pass1234')
        db.session.add(u)
        users.append(u)
    db.session.commit()
    print(f"  OK: {len(users)} users")

    print("Creating 150 tasks...")
    for i in range(150):
        u = random.choice(users)
        due = date.today() + timedelta(days=random.randint(-20, 30))
        t = Todo(
            title=f'Task #{i + 1}: {random.choice(["Do", "Finish", "Review", "Prepare"])} {random.choice(["report", "lab", "project", "presentation", "homework", "essay"])}',
            description=f'Description for task {i + 1}.',
            due_date=due,
            priority=random.choice(PRIORITIES),
            is_done=random.random() < 0.4,
            category=random.choice(CATEGORIES),
            user_id=u.id,
        )
        db.session.add(t)
    db.session.commit()
    print("  OK: 150 tasks")

    print("Creating 40 habits...")
    habits = []
    for i in range(40):
        u = random.choice(users)
        h = Habit(
            user_id=u.id,
            title=f'{random.choice(HABIT_TITLES)} ({i + 1})',
            category=random.choice(HABIT_CATEGORIES),
            difficulty=random.choice(DIFFICULTIES),
            period=random.choice(['week', 'month']),
            weekdays='all',
            is_custom=random.random() < 0.5,
        )
        db.session.add(h)
        habits.append(h)
    db.session.commit()
    print("  OK: 40 habits")

    print("Creating 60 habit completions...")
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
            note=random.choice(['', 'Great!', 'Missed yesterday', 'Keep going', '']),
        )
        db.session.add(c)
    db.session.commit()
    print("  OK: completions")

    print("Creating 30 study goals...")
    goals = []
    for i in range(30):
        u = random.choice(users)
        g = StudyGoal(
            user_id=u.id,
            title=f'{random.choice(GOAL_TITLES)} — goal {i + 1}',
            daily_target_minutes=random.choice([30, 45, 60, 90, 120]),
            period=random.choice(['daily', 'weekdays', 'weekends']),
        )
        db.session.add(g)
        goals.append(g)
    db.session.commit()
    print("  OK: 30 goals")

    print("Creating 70 study sessions...")
    for i in range(70):
        g = random.choice(goals)
        started = datetime.now() - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
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
    print("  OK: 70 sessions")

    print("Creating 50 notifications...")
    for i in range(50):
        u = random.choice(users)
        n = Notification(
            user_id=u.id,
            type=random.choice(NOTIF_TYPES),
            message=f'Test notification #{i + 1} for {u.username}',
            link='/tasks',
            is_read=random.random() < 0.5,
        )
        db.session.add(n)
    db.session.commit()
    print("  OK: 50 notifications")

    print("")
    print("TOTAL IN DATABASE:")
    print(f"  users:              {User.query.count()}")
    print(f"  todos:              {Todo.query.count()}")
    print(f"  habits:             {Habit.query.count()}")
    print(f"  habit_completions:  {HabitCompletion.query.count()}")
    print(f"  study_goals:        {StudyGoal.query.count()}")
    print(f"  study_sessions:     {StudySession.query.count()}")
    print(f"  notifications:      {Notification.query.count()}")
    print("")
    print("Done! Open hido.db in DB Browser and take screenshots.")