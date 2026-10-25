# TMT_Hido — Time Management Tool

Flask + SQLite веб-приложение для планирования и отслеживания ежедневных учебных задач.

## Стек
- Python 3.13, Flask
- SQLite (SQLAlchemy ORM)
- Bootstrap 5, Chart.js, FullCalendar
- Flask-Mail (email), APScheduler (background jobs)

## Возможности
- Регистрация и вход пользователей
- CRUD задач (создание, редактирование, удаление, отметка выполнения)
- Фильтры и сортировка задач
- Календарь задач (FullCalendar)
- Трекер привычек
- Учебный таймер (метод Помодоро)
- Статистика продуктивности
- Внутренние и email-уведомления

## Как запустить

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ao16-glitch/TMT_Hido.git
cd TMT_Hido
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Создать `.env`

Скопируйте `.env.example` в `.env` и заполните:

```
SECRET_KEY=your-secret-key-here
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

> Email-уведомления необязательны — можно оставить поля пустыми.

### 5. Запустить

```bash
python app.py
```

Откройте http://127.0.0.1:5000

**Тестовый пользователь:** `admin` / `admin123`

## База данных

SQLite (`hido.db`, создаётся автоматически при первом запуске).

Таблицы:
- `users` — пользователи
- `todos` — задачи (основная таблица)
- `habits` — привычки
- `habit_completions` — отметки о выполнении привычек
- `study_goals` — учебные цели
- `study_sessions` — сессии таймера
- `notifications` — уведомления

## Структура проекта

```
├── app.py              # Flask-приложение
├── models.py           # SQLAlchemy-модели
├── database.py         # Инициализация БД
├── seed_data.py        # Генератор тестовых данных
├── requirements.txt
├── static/
└── templates/
```

## Скриншоты

(добавьте позже — папку `screenshots/` с изображениями)
