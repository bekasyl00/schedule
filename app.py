from flask import Flask, render_template, request, redirect, url_for, session
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import telebot
from telebot import types
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Для сессий, замените на свой ключ

# --- Telegram Bot ---
BOT_TOKEN = "8020072349:AAH3xnHE9OtZQJ8HZhVBlTGDsyhWuYj4XBg"
WEBHOOK_URL = "https://schedule-1-oo31.onrender.com/" + BOT_TOKEN 
# Замените на свой токен
bot = telebot.TeleBot(BOT_TOKEN,threaded=False)

# --- Telegram регистрация chat_id и рассылка ---
tg_lessons = []


@app.route("/" + BOT_TOKEN, methods=['POST'])
def receive_update():
    json_str = request.get_data().decode('UTF-8')
    if not json_str:
        return "no data", 400
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

with app.app_context():
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Күнделікті көру'))
    bot.send_message(chat_id, 'Сәлем! Телефоныңызды енгізіңіз (тек цифры):', reply_markup=markup)
    bot.register_next_step_handler(message, save_phone)


# Обработка кнопки "Күнделікті көру"
@bot.message_handler(func=lambda m: m.text == 'Күнделікті көру')
def show_days(message):
    chat_id = message.chat.id
    days = ['Дүйсенбі', 'Сейсенбі', 'Сәрсенбі', 'Бейсенбі', 'Жұма', 'Сенбі', 'Жексенбі']
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for day in days:
        markup.add(types.KeyboardButton(day))
    bot.send_message(chat_id, 'Қай күнді көргіңіз келеді?', reply_markup=markup)

# Обработка выбора дня недели
@bot.message_handler(func=lambda m: m.text in ['Дүйсенбі', 'Сейсенбі', 'Сәрсенбі', 'Бейсенбі', 'Жұма', 'Сенбі', 'Жексенбі'])
def show_schedule_for_day(message):
    chat_id = message.chat.id
    day = message.text
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT user_id FROM telegram_users WHERE chat_id=?', (chat_id,))
        user = cur.fetchone()
        if not user:
            bot.send_message(chat_id, 'Сіз тіркелмегенсіз. Алдымен /start басыңыз.')
            return
        user_id = user[0]
        cur = conn.execute('SELECT time, subject, desc FROM schedules WHERE user_id=? AND day=? ORDER BY time', (user_id, day))
        lessons = cur.fetchall()
        if not lessons:
            bot.send_message(chat_id, f'{day} күні сабақ жоқ.')
        else:
            text = f'{day} күнінің сабақтары:\n'
            for time, subject, desc in lessons:
                text += f'⏰ {time} — {subject}\n{desc}\n\n'
            bot.send_message(chat_id, text)

def save_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id FROM users WHERE phone=?', (phone,))
        user = cur.fetchone()
        if user:
            user_id = user[0]
            conn.execute('CREATE TABLE IF NOT EXISTS telegram_users (user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, UNIQUE(user_id, chat_id), FOREIGN KEY(user_id) REFERENCES users(id))')
            conn.execute('INSERT OR IGNORE INTO telegram_users (user_id, chat_id) VALUES (?, ?)', (user_id, chat_id))
            bot.send_message(chat_id, 'Телефон тіркелді! Енді сізге сабақ туралы ескертулер келеді.')
        else:
            bot.send_message(chat_id, 'Бұл телефон табылмады. Алдымен сайтта тіркеліңіз.')

def send_reminder():
    now = datetime.datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('''SELECT s.subject, s.time, s.day, s.notify_minutes, u.id FROM schedules s JOIN users u ON s.user_id = u.id''')
        lessons = cur.fetchall()
        days_map = {
        'Дүйсенбі': 0, 'Сейсенбі': 1, 'Сәрсенбі': 2, 'Бейсенбі': 3, 
        'Жұма': 4, 'Сенбі': 5, 'Жексенбі': 6
    }
        for subject, time_str, day_str, notify_minutes, user_id in lessons:
            lesson_weekday = days_map.get(day_str)
            if lesson_weekday is None:
                continue
            today_weekday = now.weekday()
            days_ahead = (lesson_weekday - today_weekday) % 7
            lesson_date = now.date() + datetime.timedelta(days=days_ahead)
            try:
                lesson_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            except Exception:
                continue
            lesson_dt = datetime.datetime.combine(lesson_date, lesson_time)
            delta = lesson_dt - now
            total_seconds = delta.total_seconds()
            if 0 <= total_seconds <= notify_minutes * 60:
            # ...оставьте остальной код без изменений...

            # Если осталось меньше notify_hours, отправляем уведомление
            
                days_left = delta.days
                hours_left = delta.seconds // 3600
                minutes_left = (delta.seconds % 3600) // 60
                left_str = []
                if days_left > 0:
                    left_str.append(f"{days_left} күн")
                if hours_left > 0:
                    left_str.append(f"{hours_left} сағат")
                if minutes_left > 0 and days_left == 0:
                    left_str.append(f"{minutes_left} минут")
                left_str = ', '.join(left_str)

                msg = f"⏰ Ескерту! Сабақ: {subject} {lesson_dt.strftime('%A %H:%M')}\nҚалған уақыт: {left_str}"

                cur2 = conn.execute('SELECT chat_id FROM telegram_users WHERE user_id=?', (user_id,))
                for row in cur2.fetchall():
                    chat_id = row[0]
                    try:
                        bot.send_message(chat_id, msg)
                    except Exception as e:
                        print(f"Ошибка отправки Telegram: {e}")

DB_PATH = os.path.join(os.path.dirname(__file__), 'notes.db')
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            role TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    time TEXT NOT NULL,
    subject TEXT NOT NULL,
    desc TEXT NOT NULL,
    notify_minutes INTEGER DEFAULT 60,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')
        conn.execute('''CREATE TABLE IF NOT EXISTS parent_child (
            parent_id INTEGER NOT NULL,
            child_id INTEGER NOT NULL,
            FOREIGN KEY(parent_id) REFERENCES users(id),
            FOREIGN KEY(child_id) REFERENCES users(id)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS telegram_users (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            UNIQUE(user_id, chat_id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
init_db()

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        child_phone = request.form.get('child_phone') if role == 'ата-ана' else None
        if phone and password and first_name and last_name and role:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.execute('INSERT INTO users (phone, password, first_name, last_name, role) VALUES (?, ?, ?, ?, ?)',
                                 (phone, password, first_name, last_name, role))
                    # Получаем id нового пользователя
                    cur = conn.execute('SELECT id FROM users WHERE phone=?', (phone,))
                    parent = cur.fetchone()
                    parent_id = parent[0] if parent else None
                    # Если ата-ана, ищем оқушы и создаём связь
                    if role == 'ата-ана' and child_phone:
                        cur = conn.execute('SELECT id FROM users WHERE phone=? AND role=?', (child_phone, 'оқушы'))
                        child = cur.fetchone()
                        child_id = child[0] if child else None
                        if child_id and parent_id:
                            conn.execute('INSERT INTO parent_child (parent_id, child_id) VALUES (?, ?)', (parent_id, child_id))
                # Автоматически логиним после регистрации
                session['user_phone'] = phone
                session['user_name'] = first_name
                return redirect(url_for('profile'))
            except sqlite3.IntegrityError:
                error = 'Бұл нөмірмен тіркелгенсіз.'
        else:
            error = 'Барлық өрістерді толтырыңыз.'
    return render_template('register.html', error=error)
    # ...existing code...
    # Кнопка 'Шығу' для выхода и повторного вызова /start
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Шығу'))
    # ...existing code...
    if message.text == 'Шығу':
        bot.send_message(message.chat.id, 'Сіз қайтадан /start баса аласыз!')
        return handle_start(message)
    # ...existing code...


# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute('SELECT first_name FROM users WHERE phone=? AND password=?', (phone, password))
            user = cur.fetchone()
        if user:
            session['user_phone'] = phone
            session['user_name'] = user[0]
            return redirect(url_for('profile'))
        else:
            error = 'Телефон немесе құпия сөз қате.'
    return render_template('login.html', error=error)

# Профиль
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    user_name = session.get('user_name')
    user_phone = session.get('user_phone')
    # Получаем роль и id пользователя
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (user_phone,))
        user = cur.fetchone()
        user_id = user[0] if user else None
        role = user[1] if user else None
        children = []
        error = None
        # Если ата-ана, получаем список оқушылар
        if role == 'ата-ана' and user_id:
            # Добавление нового оқушы по номеру
            if request.method == 'POST':
                child_phone = request.form.get('child_phone')
                if child_phone:
                    cur2 = conn.execute('SELECT id FROM users WHERE phone=? AND role=?', (child_phone, 'оқушы'))
                    child = cur2.fetchone()
                    child_id = child[0] if child else None
                    if child_id:
                        # Проверяем, нет ли уже такой связи
                        cur3 = conn.execute('SELECT 1 FROM parent_child WHERE parent_id=? AND child_id=?', (user_id, child_id))
                        if not cur3.fetchone():
                            conn.execute('INSERT INTO parent_child (parent_id, child_id) VALUES (?, ?)', (user_id, child_id))
                    else:
                        error = 'Оқушы табылмады.'
            # Получаем всех оқушылар
            cur = conn.execute('''SELECT u.first_name, u.last_name, u.phone FROM users u
                                   JOIN parent_child pc ON u.id = pc.child_id
                                   WHERE pc.parent_id=?''', (user_id,))
            children = [{'first_name': row[0], 'last_name': row[1], 'phone': row[2]} for row in cur.fetchall()]
        else:
            error = None
    return render_template('profile.html', user_name=user_name, user_phone=user_phone, role=role, children=children, error=error)

# Выход
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/notes', methods=['GET'])
def notes():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    child_phone = request.args.get('child_phone')
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
        user = cur.fetchone()
        user_id = user[0] if user else None
        role = user[1] if user else None
        target_id = user_id
        if role == 'ата-ана' and child_phone:
            cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
            child = cur2.fetchone()
            if child:
                target_id = child[0]
        cur = conn.execute('SELECT id, title, text FROM notes WHERE user_id=? ORDER BY id DESC', (target_id,))
        notes = [{'id': row[0], 'title': row[1], 'text': row[2]} for row in cur.fetchall()]
        # Для ата-ана — список всех его оқушылар
        children = []
        if role == 'ата-ана':
            cur = conn.execute('''SELECT u.first_name, u.last_name, u.phone FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE pc.parent_id=?''', (user_id,))
            children = [{'first_name': row[0], 'last_name': row[1], 'phone': row[2]} for row in cur.fetchall()]
    return render_template('notes.html', notes=notes, children=children, selected_child=child_phone)


@app.route('/notes/add', methods=['POST'])
def add_note():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    title = request.form.get('title')
    text = request.form.get('text')
    if title and text:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute('SELECT id FROM users WHERE phone=?', (session['user_phone'],))
            user = cur.fetchone()
            user_id = user[0] if user else None
            if user_id:
                conn.execute('INSERT INTO notes (user_id, title, text) VALUES (?, ?, ?)', (user_id, title, text))
    return redirect(url_for('notes'))





days_list = ['Дүйсенбі', 'Сейсенбі', 'Сәрсенбі', 'Бейсенбі', 'Жұма', 'Сенбі', 'Жексенбі']

# Главная страница — расписание уроков выбранного дня
@app.route('/', methods=['GET'])
def schedule():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    day = request.args.get('day', 'Дүйсенбі')
    child_phone = request.args.get('child_phone')
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
        user = cur.fetchone()
        user_id = user[0] if user else None
        role = user[1] if user else None
        # Для ата-ана: если выбран child_phone, ищем id оқушы по parent_child
        target_id = user_id
        if role == 'ата-ана' and child_phone:
            cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
            child = cur2.fetchone()
            if child:
                target_id = child[0]
        cur = conn.execute('SELECT id, time, subject, desc FROM schedules WHERE user_id=? AND day=? ORDER BY time', (target_id, day))
        lessons = [{'id': row[0], 'time': row[1], 'subject': row[2], 'desc': row[3]} for row in cur.fetchall()]
        # Для ата-ана — список всех его оқушылар
        children = []
        if role == 'ата-ана':
            cur = conn.execute('''SELECT u.first_name, u.last_name, u.phone FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE pc.parent_id=?''', (user_id,))
            children = [{'first_name': row[0], 'last_name': row[1], 'phone': row[2]} for row in cur.fetchall()]
    return render_template('schedule.html', lessons=lessons, days=days_list, current_day=day, children=children, selected_child=child_phone)

# Добавить урок
@app.route('/add_lesson', methods=['POST'])
def add_lesson():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    day = request.form.get('day')
    time = request.form.get('time')
    subject = request.form.get('subject')
    desc = request.form.get('desc')
    child_phone = request.form.get('child_phone')
    notify_minutes = request.form.get('notify_minutes')

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
        user = cur.fetchone()
        user_id = user[0] if user else None
        role = user[1] if user else None
        target_id = user_id
        if role == 'ата-ана' and child_phone:
            cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
            child = cur2.fetchone()
            if child:
                target_id = child[0]
        try:
            notify_minutes_int = int(notify_minutes) if notify_minutes else 60
        except Exception:
            notify_minutes_int = 60
        if day and time and subject and desc and target_id:
            conn.execute(
                'INSERT INTO schedules (user_id, day, time, subject, desc, notify_minutes) VALUES (?, ?, ?, ?, ?, ?)',
                (target_id, day, time, subject, desc, notify_minutes_int)
            )

    # child_phone нужен для возврата к нужному пользователю
    params = {'day': day}
    if role == 'ата-ана' and child_phone:
        params['child_phone'] = child_phone
    return redirect(url_for('schedule', **params))

# Удалить урок
@app.route('/delete_lesson', methods=['POST'])
def delete_lesson():
    if 'user_phone' not in session:
        return redirect(url_for('login'))
    day = request.form.get('day')
    lesson_id = request.form.get('id')
    child_phone = request.form.get('child_phone')
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
        user = cur.fetchone()
        user_id = user[0] if user else None
        role = user[1] if user else None
        target_id = user_id
        if role == 'ата-ана' and child_phone:
            cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
            child = cur2.fetchone()
            if child:
                target_id = child[0]
        if target_id and lesson_id:
            conn.execute('DELETE FROM schedules WHERE id=? AND user_id=?', (lesson_id, target_id))
    params = {'day': day}
    if role == 'ата-ана' and child_phone:
        params['child_phone'] = child_phone
    return redirect(url_for('schedule', **params))

# Изменить урок
@app.route('/edit_lesson', methods=['POST'])
def edit_lesson():
    lesson_id = request.form['id']
    time = request.form['time']
    subject = request.form['subject']
    desc = request.form['desc']
    notify_minutes = request.form.get('notify_minutes', 60)
    try:
        notify_minutes_int = int(notify_minutes)
    except Exception:
        notify_minutes_int = 60
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
        UPDATE schedules 
        SET time=?, subject=?, desc=?, notify_minutes=? 
        WHERE id=?
    ''', (time, subject, desc, notify_minutes_int, lesson_id))
        conn.commit()
    return redirect(request.referrer or '/')


def run_flask():
    app.run(debug=True, use_reloader=False)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)