from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date, timedelta
from functools import wraps
from models import (db, User, Todo, Habit, HabitCompletion,
                    StudyGoal, StudySession, Notification)
from database import init_database
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import os
import atexit
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-me')
init_database(app)


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def is_authenticated():
    return 'user_id' in session


def get_current_user():
    return User.query.get(session.get('user_id'))


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def create_notification(user_id, ntype, message, link=None):
    """Создаёт уведомление в БД. Дубликаты за день не создаются."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    exists = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.type == ntype,
        Notification.message == message,
        Notification.created_at >= today_start
    ).first()
    if exists:
        return None
    n = Notification(user_id=user_id, type=ntype, message=message, link=link)
    db.session.add(n)
    db.session.commit()
    return n


# ---------- АУТЕНТИФИКАЦИЯ ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('tasks'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['coins'] = user.coins
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(request.args.get('next') or url_for('tasks'))
        else:
            flash('Неверное имя или пароль', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_authenticated():
        return redirect(url_for('tasks'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        errors = []
        if len(username) < 3:
            errors.append('Имя не менее 3 символов')
        if User.query.filter_by(username=username).first():
            errors.append('Имя уже существует')
        if User.query.filter_by(email=email).first():
            errors.append('Email уже используется')
        if password != confirm:
            errors.append('Пароли не совпадают')
        if errors:
            for err in errors:
                flash(err, 'danger')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна! Теперь войдите.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    total = Todo.query.filter_by(user_id=user.id).count()
    completed = Todo.query.filter_by(user_id=user.id, is_done=True).count()
    active = total - completed
    rate = round(completed / total * 100) if total > 0 else 0
    stats = {'total': total, 'active': active, 'completed': completed, 'rate': rate}
    return render_template('profile.html', stats=stats, user=user)


# ---------- ЗАДАЧИ ----------
@app.route('/')
def index():
    return redirect(url_for('tasks'))


@app.route('/tasks')
@login_required
def tasks():
    user = get_current_user()
    if user is None:
        session.clear()
        return redirect(url_for('login'))
    filter_by = request.args.get('filter', 'all')
    category = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'due_date')
    query = Todo.query.filter_by(user_id=user.id)
    if filter_by == 'active':
        query = query.filter_by(is_done=False)
    elif filter_by == 'done':
        query = query.filter_by(is_done=True)
    elif filter_by == 'overdue':
        query = query.filter(Todo.due_date < date.today(), Todo.is_done == False)
    if category != 'all':
        query = query.filter_by(category=category)
    if sort_by == 'priority':
        query = query.order_by(Todo.priority.asc(), Todo.due_date.asc())
    elif sort_by == 'title':
        query = query.order_by(Todo.title.asc())
    else:
        query = query.order_by(db.case((Todo.due_date.is_(None), 1), else_=0), Todo.due_date.asc())
    todos = query.all()
    categories = db.session.query(Todo.category).filter_by(user_id=user.id).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    return render_template('tasks.html', todos=todos, categories=categories,
                           today=date.today(),
                           current_filter=filter_by,
                           current_category=category,
                           current_sort=sort_by)


@app.route('/add', methods=['POST'])
@login_required
def add_todo():
    title = request.form.get('title', '').strip()
    if not title:
        flash('Введите название задачи', 'warning')
        return redirect(url_for('tasks'))
    todo = Todo(
        title=title,
        description=request.form.get('description', '').strip(),
        priority=int(request.form.get('priority', 3)),
        category=request.form.get('category', 'Общие'),
        user_id=session['user_id']
    )
    due = request.form.get('due_date')
    if due:
        todo.due_date = datetime.strptime(due, '%Y-%m-%d').date()
    db.session.add(todo)
    db.session.commit()
    flash('Задача добавлена', 'success')
    return redirect(url_for('tasks'))


@app.route('/toggle/<int:todo_id>')
@login_required
def toggle_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('tasks'))
    todo.is_done = not todo.is_done
    db.session.commit()
    return redirect(url_for('tasks'))


@app.route('/edit/<int:todo_id>', methods=['POST'])
@login_required
def edit_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('tasks'))
    todo.title = request.form.get('title', todo.title)
    todo.description = request.form.get('description', todo.description)
    todo.priority = int(request.form.get('priority', todo.priority))
    todo.category = request.form.get('category', todo.category)
    due = request.form.get('due_date')
    if due:
        todo.due_date = datetime.strptime(due, '%Y-%m-%d').date()
    else:
        todo.due_date = None
    db.session.commit()
    flash('Задача обновлена', 'success')
    return redirect(url_for('tasks'))


@app.route('/delete/<int:todo_id>')
@login_required
def delete_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('tasks'))
    db.session.delete(todo)
    db.session.commit()
    flash('Задача удалена', 'success')
    return redirect(url_for('tasks'))


# ---------- ПРИВЫЧКИ ----------
@app.route('/habits')
@login_required
def habits():
    user = get_current_user()
    user_habits = Habit.query.filter_by(user_id=user.id).all()
    categories = {
        'умные привычки': ['Медитация', 'Дыхательная гимнастика', 'Визуализация целей', 'Благодарность'],
        'продуктивность': ['Планирование дня', 'Метод помидора (25 мин)', 'Завершить важную задачу', 'Разбор почты'],
        'личное развитие': ['Чтение 30 мин', 'Изучение языка', 'Онлайн курс', 'Просмотр лекции'],
        'спорт': ['Зарядка', 'Йога', 'Бег', 'Тренировка'],
        'финансы': ['Экономия', 'Учет расходов', 'Откладывание 10%', 'Инвестиции'],
        'домашние дела': ['Уборка', 'Стирка', 'Приготовить еду', 'Полив цветов'],
        'здоровье': ['Прогулка', 'Здоровый завтрак', 'Вода 2л', 'Сон 8ч']
    }
    return render_template('habits.html', habits=user_habits, categories=categories, today=date.today())


@app.route('/add_habit_predefined', methods=['POST'])
@login_required
def add_habit_predefined():
    title = request.form.get('title')
    category = request.form.get('category')
    difficulty = request.form.get('difficulty', 'средний')
    period = request.form.get('period', 'неделя')
    if not Habit.query.filter_by(user_id=session['user_id'], title=title).first():
        habit = Habit(
            user_id=session['user_id'],
            title=title,
            category=category,
            difficulty=difficulty,
            period=period,
            weekdays='all',
            is_custom=False
        )
        db.session.add(habit)
        db.session.commit()
        flash('Привычка добавлена', 'success')
    else:
        flash('Привычка уже есть', 'warning')
    return redirect(url_for('habits'))


@app.route('/add_custom_habit', methods=['POST'])
@login_required
def add_custom_habit():
    title = request.form.get('title')
    category = request.form.get('category')
    difficulty = request.form.get('difficulty')
    period = request.form.get('period')
    weekdays = request.form.get('weekdays', 'all')
    habit = Habit(
        user_id=session['user_id'],
        title=title,
        category=category,
        difficulty=difficulty,
        period=period,
        weekdays=weekdays,
        is_custom=True
    )
    db.session.add(habit)
    db.session.commit()
    flash('Привычка создана', 'success')
    return redirect(url_for('habits'))


@app.route('/complete_habit/<int:habit_id>', methods=['POST'])
@login_required
def complete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('habits'))
    today_date = date.today()
    existing = HabitCompletion.query.filter_by(habit_id=habit.id, date=today_date).first()
    if existing:
        flash('Вы уже отмечали эту привычку сегодня', 'warning')
        return redirect(url_for('habits'))
    completion = HabitCompletion(
        habit_id=habit.id,
        user_id=session['user_id'],
        date=today_date,
        note=request.form.get('note', '')
    )
    db.session.add(completion)
    user = get_current_user()
    reward = habit.get_coins_reward()
    user.coins += reward
    session['coins'] = user.coins
    db.session.commit()
    flash(f'Привычка выполнена! +{reward} монет', 'success')
    return redirect(url_for('habits'))


@app.route('/delete_habit/<int:habit_id>')
@login_required
def delete_habit(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('habits'))
    db.session.delete(habit)
    db.session.commit()
    flash('Привычка удалена', 'success')
    return redirect(url_for('habits'))


# ---------- СТАТИСТИКА ----------
@app.route('/habits_stats')
@login_required
def habits_stats():
    user_id = session['user_id']
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    habit_stats = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        cnt = HabitCompletion.query.filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.date == day
        ).count()
        habit_stats.append({'date': day.strftime('%a'), 'completions': cnt})

    total_habit_completed = HabitCompletion.query.filter(
        HabitCompletion.user_id == user_id,
        HabitCompletion.date >= start_date
    ).count()
    total_habits = Habit.query.filter_by(user_id=user_id).count()
    habit_missed = (total_habits * 7) - total_habit_completed if total_habits > 0 else 0
    habit_percent = (total_habit_completed / (total_habits * 7) * 100) if total_habits > 0 else 0

    task_stats = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        done_count = Todo.query.filter(
            Todo.user_id == user_id,
            Todo.is_done == True,
            Todo.created_at >= day,
            Todo.created_at < day + timedelta(days=1)
        ).count()
        task_stats.append({'date': day.strftime('%a'), 'completed': done_count})

    total_tasks_done = Todo.query.filter(
        Todo.user_id == user_id,
        Todo.is_done == True,
        Todo.created_at >= start_date
    ).count()
    total_tasks = Todo.query.filter_by(user_id=user_id).count()
    task_not_done = total_tasks - total_tasks_done if total_tasks > 0 else 0
    task_percent = (total_tasks_done / total_tasks * 100) if total_tasks > 0 else 0

    study_stats = []
    for i in range(7):
        day = start_date + timedelta(days=i)
        total_seconds = db.session.query(db.func.sum(StudySession.duration_seconds)).filter(
            StudySession.user_id == user_id,
            StudySession.date == day
        ).scalar() or 0
        study_stats.append({'date': day.strftime('%a'), 'minutes': total_seconds // 60})

    total_study_seconds = db.session.query(db.func.sum(StudySession.duration_seconds)).filter(
        StudySession.user_id == user_id,
        StudySession.date >= start_date
    ).scalar() or 0
    total_study_minutes = total_study_seconds // 60

    study_goals = StudyGoal.query.filter_by(user_id=user_id).all()
    total_target_minutes = sum(g.daily_target_minutes for g in study_goals)

    full_sessions = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.date >= start_date,
        StudySession.completed_full == True
    ).count()
    interrupted_sessions = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.date >= start_date,
        StudySession.was_interrupted == True
    ).count()
    base_level = 3
    level_shift = full_sessions - interrupted_sessions
    level_num = max(0, min(5, base_level + level_shift))
    level_letters = ['F', 'E', 'D', 'C', 'B', 'A']
    general_level = level_letters[level_num]

    study_percent = (total_study_minutes / total_target_minutes * 100) if total_target_minutes > 0 else 0

    return render_template(
        'stats.html',
        habit_stats=habit_stats,
        total_habit_completed=total_habit_completed,
        habit_missed=habit_missed,
        habit_percent=round(habit_percent, 1),
        total_habits=total_habits,
        task_stats=task_stats,
        total_tasks_done=total_tasks_done,
        task_not_done=task_not_done,
        task_percent=round(task_percent, 1),
        total_tasks=total_tasks,
        timer_stats=study_stats,
        total_timer_minutes=total_study_minutes,
        total_target_minutes=total_target_minutes,
        general_level=general_level,
        study_percent=round(study_percent, 1),
        full_sessions=full_sessions,
        total_goals=len(study_goals)
    )


# ---------- API ----------
@app.route('/api/todos')
@login_required
def api_todos():
    user = get_current_user()
    todos = Todo.query.filter_by(user_id=user.id).all()
    result = []
    for t in todos:
        result.append({
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else None,
            'priority': t.priority,
            'is_done': t.is_done,
            'category': t.category,
            'is_overdue': t.is_overdue
        })
    return jsonify(result)


@app.route('/api/weekly_productivity')
@login_required
def weekly_productivity():
    user_id = session['user_id']
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    days = []
    completions = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        days.append(d.strftime('%a'))
        cnt = HabitCompletion.query.filter(
            HabitCompletion.user_id == user_id,
            HabitCompletion.date == d
        ).count()
        completions.append(cnt)
    return jsonify({'days': days, 'completions': completions})


# ---------- КАЛЕНДАРЬ ЗАДАЧ ----------
@app.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html')


# ---------- ТАЙМЕР ----------
@app.route('/timer')
@login_required
def timer():
    user_id = session['user_id']
    goals = StudyGoal.query.filter_by(user_id=user_id).all()
    today = date.today()

    total_study_seconds = db.session.query(db.func.sum(StudySession.duration_seconds)).filter(
        StudySession.user_id == user_id,
        StudySession.date == today
    ).scalar() or 0
    total_study_minutes = total_study_seconds // 60

    total_target_minutes = sum(g.daily_target_minutes for g in goals)

    goal_percentages = []
    for goal in goals:
        completed_seconds = db.session.query(db.func.sum(StudySession.duration_seconds)).filter(
            StudySession.user_id == user_id,
            StudySession.goal_id == goal.id,
            StudySession.date == today
        ).scalar() or 0
        percent = min(100, (completed_seconds / 60 / goal.daily_target_minutes * 100)) if goal.daily_target_minutes > 0 else 0
        goal_percentages.append(percent)
    avg_percent = sum(goal_percentages) / len(goal_percentages) if goals else 0

    full_sessions = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.date == today,
        StudySession.completed_full == True
    ).count()
    interrupted_sessions = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.date == today,
        StudySession.was_interrupted == True
    ).count()
    base_level = 3
    level_shift = full_sessions - interrupted_sessions
    level_num = max(0, min(5, base_level + level_shift))
    level_letters = ['F', 'E', 'D', 'C', 'B', 'A']
    general_level = level_letters[level_num]

    goals_data = []
    for goal in goals:
        completed_seconds = db.session.query(db.func.sum(StudySession.duration_seconds)).filter(
            StudySession.user_id == user_id,
            StudySession.goal_id == goal.id,
            StudySession.date == today
        ).scalar() or 0
        percent = min(100, (completed_seconds / 60 / goal.daily_target_minutes * 100)) if goal.daily_target_minutes > 0 else 0

        goal_full = StudySession.query.filter(
            StudySession.user_id == user_id,
            StudySession.goal_id == goal.id,
            StudySession.date == today,
            StudySession.completed_full == True
        ).count()
        goal_interrupted = StudySession.query.filter(
            StudySession.user_id == user_id,
            StudySession.goal_id == goal.id,
            StudySession.date == today,
            StudySession.was_interrupted == True
        ).count()
        goal_level_num = max(0, min(5, base_level + (goal_full - goal_interrupted)))
        goal_level = level_letters[goal_level_num] if (goal_full + goal_interrupted) > 0 else '?'

        goals_data.append({
            'id': goal.id,
            'title': goal.title,
            'daily_target_minutes': goal.daily_target_minutes,
            'completed_minutes': completed_seconds // 60,
            'percent': round(percent, 1),
            'level': goal_level,
            'period': goal.period
        })

    return render_template(
        'timer.html',
        total_study_minutes=total_study_minutes,
        total_target_minutes=total_target_minutes,
        general_level=general_level,
        avg_percent=round(avg_percent, 1),
        goals=goals_data
    )


@app.route('/add_study_goal', methods=['POST'])
@login_required
def add_study_goal():
    title = request.form.get('title')
    daily_target_minutes = int(request.form.get('daily_target_minutes', 60))
    period = request.form.get('period', 'daily')
    goal = StudyGoal(
        user_id=session['user_id'],
        title=title,
        daily_target_minutes=daily_target_minutes,
        period=period
    )
    db.session.add(goal)
    db.session.commit()
    flash('Цель добавлена', 'success')
    return redirect(url_for('timer'))


@app.route('/delete_study_goal/<int:goal_id>')
@login_required
def delete_study_goal(goal_id):
    goal = StudyGoal.query.get_or_404(goal_id)
    if goal.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('timer'))
    db.session.delete(goal)
    db.session.commit()
    flash('Цель удалена', 'success')
    return redirect(url_for('timer'))


@app.route('/edit_study_goal/<int:goal_id>', methods=['POST'])
@login_required
def edit_study_goal(goal_id):
    goal = StudyGoal.query.get_or_404(goal_id)
    if goal.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('timer'))
    goal.title = request.form.get('title')
    goal.daily_target_minutes = int(request.form.get('daily_target_minutes', 60))
    goal.period = request.form.get('period', 'daily')
    db.session.commit()
    flash('Цель обновлена', 'success')
    return redirect(url_for('timer'))


@app.route('/api/start_study/<int:goal_id>', methods=['POST'])
@login_required
def api_start_study(goal_id):
    goal = StudyGoal.query.get_or_404(goal_id)
    if goal.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    session_obj = StudySession(
        user_id=session['user_id'],
        goal_id=goal_id,
        start_time=datetime.utcnow(),
        date=date.today()
    )
    db.session.add(session_obj)
    db.session.commit()
    return jsonify({'session_id': session_obj.id, 'start_time': session_obj.start_time.isoformat()})


@app.route('/api/complete_study/<int:session_id>', methods=['POST'])
@login_required
def api_complete_study(session_id):
    data = request.json
    elapsed_seconds = data.get('elapsed_seconds', 0)
    session_obj = StudySession.query.get_or_404(session_id)
    if session_obj.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    session_obj.end_time = datetime.utcnow()
    session_obj.duration_seconds = elapsed_seconds
    if elapsed_seconds >= 25 * 60:
        session_obj.completed_full = True
        session_obj.was_interrupted = False
    else:
        session_obj.completed_full = False
        session_obj.was_interrupted = True
    db.session.commit()
    return jsonify({'success': True})


# ---------- УВЕДОМЛЕНИЯ ----------
@app.route('/notifications')
@login_required
def notifications():
    user_id = session['user_id']
    items = Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.created_at.desc()).limit(50).all()
    unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return render_template('notifications.html', items=items, unread=unread)


@app.route('/notifications/read/<int:nid>')
@login_required
def mark_notification_read(nid):
    n = Notification.query.get_or_404(nid)
    if n.user_id != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('notifications'))
    n.is_read = True
    db.session.commit()
    return redirect(n.link or url_for('notifications'))


@app.route('/notifications/read_all')
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=session['user_id'], is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    flash('Все уведомления прочитаны', 'success')
    return redirect(url_for('notifications'))


@app.route('/api/notifications/unread_count')
@login_required
def api_unread_count():
    cnt = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
    return jsonify({'count': cnt})


# ---------- НАСТРОЙКИ ПОЧТЫ ----------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', '')

mail = Mail(app)


def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
        print(f"✅ Письмо отправлено на {to}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")


# ---------- ФОНОВЫЕ ЗАДАЧИ ----------
def check_deadlines():
    """За 1 день до дедлайна — уведомление в БД и на email."""
    tomorrow = date.today() + timedelta(days=1)
    tasks = Todo.query.filter(Todo.due_date == tomorrow, Todo.is_done == False).all()

    for task in tasks:
        user = User.query.get(task.user_id)
        if not user:
            continue

        create_notification(
            user_id=user.id,
            ntype='deadline',
            message=f"Задача «{task.title}» — дедлайн завтра ({tomorrow.strftime('%d.%m.%Y')})",
            link=url_for('tasks')
        )

        if user.email:
            subject = f"⏰ Напоминание: задача '{task.title}' завтра!"
            body = f"""Здравствуйте, {user.username}!
У вас запланирована задача "{task.title}" на завтра ({tomorrow.strftime('%d.%m.%Y')}).
Категория: {task.category}
Приоритет: {task.priority}
Не забудьте выполнить!

С уважением, Hido."""
            send_email(user.email, subject, body)


def check_overdue():
    """Ежедневно напоминает о просроченных задачах."""
    today = date.today()
    overdue = Todo.query.filter(
        Todo.due_date < today,
        Todo.is_done == False
    ).all()

    for task in overdue:
        user = User.query.get(task.user_id)
        if not user:
            continue
        create_notification(
            user_id=user.id,
            ntype='deadline',
            message=f"Просрочена задача «{task.title}» (срок был {task.due_date.strftime('%d.%m.%Y')})",
            link=url_for('tasks', filter='overdue')
        )


def check_habits_evening():
    """Вечером напоминает о невыполненных сегодня привычках."""
    today = date.today()
    if datetime.utcnow().hour < 20:
        return

    habits = Habit.query.all()
    for habit in habits:
        done = HabitCompletion.query.filter_by(
            habit_id=habit.id, date=today
        ).first()
        if not done:
            create_notification(
                user_id=habit.user_id,
                ntype='habit_reminder',
                message=f"Не забудь выполнить привычку «{habit.title}» сегодня",
                link=url_for('habits')
            )


# Планировщик — стартуем только в основном процессе
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_deadlines, 'interval', hours=1)
    scheduler.add_job(check_overdue, 'interval', hours=3)
    scheduler.add_job(check_habits_evening, 'interval', hours=1)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)