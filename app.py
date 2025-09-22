# # app.py
# import os
# import sqlite3
# import datetime
# from flask import Flask, request, render_template, redirect, url_for, session, jsonify
# import telebot
# from telebot import types
# from apscheduler.schedulers.background import BackgroundScheduler

# # ---------------- Configuration ----------------

# BOT_TOKEN = "8020072349:AAH3xnHE9OtZQJ8HZhVBlTGDsyhWuYj4XBg"
# WEBHOOK_URL = "https://schedule-1-oo31.onrender.com/" + BOT_TOKEN  # твой render-домен + токен
# # Опция: если хочешь защитить /set_webhook, установи тут секрет, иначе оставь пустым:
# WEBHOOK_SECRET = ""  # если не нужен — оставить ""

# # Flask app
# app = Flask(__name__)
# app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey")

# # Telebot
# bot = telebot.TeleBot(BOT_TOKEN)

# # ---------------- Database ----------------
# DB_PATH = os.path.join(os.path.dirname(__file__), "notes.db")

# def init_db():
#     with sqlite3.connect(DB_PATH) as conn:
#         conn.execute('''CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             phone TEXT NOT NULL UNIQUE,
#             password TEXT NOT NULL,
#             first_name TEXT NOT NULL,
#             last_name TEXT NOT NULL,
#             role TEXT NOT NULL
#         )''')
#         conn.execute('''CREATE TABLE IF NOT EXISTS notes (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER NOT NULL,
#             title TEXT NOT NULL,
#             text TEXT NOT NULL,
#             FOREIGN KEY(user_id) REFERENCES users(id)
#         )''')
#         conn.execute('''CREATE TABLE IF NOT EXISTS schedules (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER NOT NULL,
#             day TEXT NOT NULL,
#             time TEXT NOT NULL,
#             subject TEXT NOT NULL,
#             desc TEXT NOT NULL,
#             FOREIGN KEY(user_id) REFERENCES users(id)
#         )''')
#         conn.execute('''CREATE TABLE IF NOT EXISTS parent_child (
#             parent_id INTEGER NOT NULL,
#             child_id INTEGER NOT NULL,
#             FOREIGN KEY(parent_id) REFERENCES users(id),
#             FOREIGN KEY(child_id) REFERENCES users(id)
#         )''')
#         conn.execute('''CREATE TABLE IF NOT EXISTS telegram_users (
#             user_id INTEGER NOT NULL,
#             chat_id INTEGER NOT NULL,
#             UNIQUE(user_id, chat_id),
#             FOREIGN KEY(user_id) REFERENCES users(id)
#         )''')

# init_db()

# # ---------------- Telegram handlers ----------------
# days_list = ['Дүйсенбі','Сейсенбі','Сәрсенбі','Бейсенбі','Жұма','Сенбі','Жексенбі']

# @bot.message_handler(commands=['start'])
# def handle_start(message):
#     chat_id = message.chat.id
#     markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
#     markup.add(types.KeyboardButton('Күнделікті көру'))
#     bot.send_message(chat_id, 'Сәлем! Телефоныңызды енгізіңіз (тек цифры):', reply_markup=markup)
#     bot.register_next_step_handler(message, save_phone)

# def save_phone(message):
#     chat_id = message.chat.id
#     phone = message.text.strip()
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id FROM users WHERE phone=?', (phone,))
#         user = cur.fetchone()
#         if user:
#             user_id = user[0]
#             conn.execute('INSERT OR IGNORE INTO telegram_users (user_id, chat_id) VALUES (?, ?)', (user_id, chat_id))
#             bot.send_message(chat_id, 'Телефон тіркелді! Енді сізге сабақ туралы ескертулер келеді.')
#         else:
#             bot.send_message(chat_id, 'Бұл телефон табылмады. Алдымен сайтта тіркеліңіз.')

# @bot.message_handler(func=lambda m: m.text == 'Күнделікті көру')
# def show_days(message):
#     chat_id = message.chat.id
#     markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
#     for day in days_list:
#         markup.add(types.KeyboardButton(day))
#     bot.send_message(chat_id, 'Қай күнді көргіңіз келеді?', reply_markup=markup)

# @bot.message_handler(func=lambda m: m.text in days_list)
# def show_schedule_for_day(message):
#     chat_id = message.chat.id
#     day = message.text
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT user_id FROM telegram_users WHERE chat_id=?', (chat_id,))
#         user = cur.fetchone()
#         if not user:
#             bot.send_message(chat_id, 'Сіз тіркелмегенсіз. Алдымен /start басыңыз.')
#             return
#         user_id = user[0]
#         cur = conn.execute('SELECT time, subject, desc FROM schedules WHERE user_id=? AND day=? ORDER BY time', (user_id, day))
#         lessons = cur.fetchall()
#         if not lessons:
#             bot.send_message(chat_id, f'{day} күні сабақ жоқ.')
#         else:
#             text = f'{day} күнінің сабақтары:\n'
#             for time, subject, desc in lessons:
#                 text += f'⏰ {time} — {subject}\n{desc}\n\n'
#             bot.send_message(chat_id, text)

# # ---------------- Webhook endpoint ----------------
# @app.route("/" + BOT_TOKEN, methods=["POST"])
# def receive_update():
#     # Telegram будет POST-ить JSON сюда
#     try:
#         json_str = request.get_data().decode("utf-8")
#         update = telebot.types.Update.de_json(json_str)
#         bot.process_new_updates([update])
#     except Exception as e:
#         print("Error processing update:", e)
#         return "error", 500
#     return "ok", 200

# # ---------------- Optional: set/remove webhook endpoint ----------------
# @app.route("/set_webhook", methods=["GET", "POST"])
# def set_webhook_route():
#     # Для безопасности: если WEBHOOK_SECRET задан — требуем ?secret=...
#     secret = request.args.get("secret", "")
#     if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
#         return jsonify({"ok": False, "error": "bad secret"}), 403

#     try:
#         bot.remove_webhook()
#         ok = bot.set_webhook(url=WEBHOOK_URL)
#         return jsonify({"ok": True, "set_webhook": ok}), 200
#     except Exception as e:
#         print("set_webhook error:", e)
#         return jsonify({"ok": False, "error": str(e)}), 500

# # ---------------- Scheduler reminders ----------------
# def send_reminder():
#     now = datetime.datetime.now()
#     days_map = {'Дүйсенбі':0,'Сейсенбі':1,'Сәрсенбі':2,'Бейсенбі':3,'Жұма':4,'Сенбі':5,'Жексенбі':6}
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT s.subject, s.time, s.day, u.id FROM schedules s JOIN users u ON s.user_id = u.id')
#         for subject, time_str, day_str, user_id in cur.fetchall():
#             lesson_weekday = days_map.get(day_str)
#             if lesson_weekday is None:
#                 continue
#             today_weekday = now.weekday()
#             days_ahead = (lesson_weekday - today_weekday) % 7
#             lesson_date = now.date() + datetime.timedelta(days=days_ahead)
#             try:
#                 lesson_time = datetime.datetime.strptime(time_str, "%H:%M").time()
#             except Exception:
#                 continue
#             lesson_dt = datetime.datetime.combine(lesson_date, lesson_time)
#             delta_seconds = (lesson_dt - now).total_seconds()
#             # напоминание за ~24ч или ~1ч (нестрого)
#             if 82800 <= delta_seconds <= 87600 or 3540 <= delta_seconds <= 4260:
#                 msg = f"⏰ Ескерту! Сабақ: {subject} {lesson_dt.strftime('%A %H:%M')}"
#                 cur2 = conn.execute('SELECT chat_id FROM telegram_users WHERE user_id=?', (user_id,))
#                 for row in cur2.fetchall():
#                     try:
#                         bot.send_message(row[0], msg)
#                     except Exception as e:
#                         print("Ошибка отправки:", e)

# scheduler = BackgroundScheduler()
# scheduler.add_job(send_reminder, "interval", minutes=1)
# scheduler.start()

# # ---------------- Your Flask routes (register/login/profile/schedule/notes) ----------------
# # Я добавляю те же маршруты, которые были у тебя ранее (чисто и без дублирования).
# # Если у тебя есть шаблоны .html в папке templates — они будут использоваться.

# @app.route("/")
# def index():
#     return "Flask + Telegram бот работает! Отправь /start в Telegram боту."

# # Регистрация (пример, использует templates/register.html)
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     error = None
#     if request.method == 'POST':
#         phone = request.form.get('phone')
#         password = request.form.get('password')
#         first_name = request.form.get('first_name')
#         last_name = request.form.get('last_name')
#         role = request.form.get('role')
#         child_phone = request.form.get('child_phone') if role == 'ата-ана' else None
#         if phone and password and first_name and last_name and role:
#             try:
#                 with sqlite3.connect(DB_PATH) as conn:
#                     conn.execute('INSERT INTO users (phone, password, first_name, last_name, role) VALUES (?, ?, ?, ?, ?)',
#                                  (phone, password, first_name, last_name, role))
#                     # если parent-child связь — вставляем
#                     cur = conn.execute('SELECT id FROM users WHERE phone=?', (phone,))
#                     parent = cur.fetchone()
#                     parent_id = parent[0] if parent else None
#                     if role == 'ата-ана' and child_phone and parent_id:
#                         cur = conn.execute('SELECT id FROM users WHERE phone=? AND role=?', (child_phone, 'оқушы'))
#                         child = cur.fetchone()
#                         if child:
#                             child_id = child[0]
#                             conn.execute('INSERT OR IGNORE INTO parent_child (parent_id, child_id) VALUES (?, ?)', (parent_id, child_id))
#                 session['user_phone'] = phone
#                 session['user_name'] = first_name
#                 return redirect(url_for('profile'))
#             except sqlite3.IntegrityError:
#                 error = 'Бұл нөмірмен тіркелгенсіз.'
#         else:
#             error = 'Барлық өрістерді толтырыңыз.'
#     return render_template('register.html', error=error)

# # Login
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     error = None
#     if request.method == 'POST':
#         phone = request.form.get('phone')
#         password = request.form.get('password')
#         with sqlite3.connect(DB_PATH) as conn:
#             cur = conn.execute('SELECT first_name FROM users WHERE phone=? AND password=?', (phone, password))
#             user = cur.fetchone()
#         if user:
#             session['user_phone'] = phone
#             session['user_name'] = user[0]
#             return redirect(url_for('profile'))
#         else:
#             error = 'Телефон немесе құпия сөз қате.'
#     return render_template('login.html', error=error)

# # Profile
# @app.route('/profile', methods=['GET', 'POST'])
# def profile():
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     user_name = session.get('user_name')
#     user_phone = session.get('user_phone')
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (user_phone,))
#         user = cur.fetchone()
#         user_id = user[0] if user else None
#         role = user[1] if user else None
#         children = []
#         error = None
#         if role == 'ата-ана' and user_id:
#             if request.method == 'POST':
#                 child_phone = request.form.get('child_phone')
#                 if child_phone:
#                     cur2 = conn.execute('SELECT id FROM users WHERE phone=? AND role=?', (child_phone, 'оқушы'))
#                     child = cur2.fetchone()
#                     if child:
#                         child_id = child[0]
#                         cur3 = conn.execute('SELECT 1 FROM parent_child WHERE parent_id=? AND child_id=?', (user_id, child_id))
#                         if not cur3.fetchone():
#                             conn.execute('INSERT INTO parent_child (parent_id, child_id) VALUES (?, ?)', (user_id, child_id))
#                     else:
#                         error = 'Оқушы табылмады.'
#             cur = conn.execute('''SELECT u.first_name, u.last_name, u.phone FROM users u
#                                    JOIN parent_child pc ON u.id = pc.child_id
#                                    WHERE pc.parent_id=?''', (user_id,))
#             children = [{'first_name': r[0], 'last_name': r[1], 'phone': r[2]} for r in cur.fetchall()]
#     return render_template('profile.html', user_name=user_name, user_phone=user_phone, role=role, children=children, error=error)

# # Notes view/add
# @app.route('/notes', methods=['GET'])
# def notes():
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     child_phone = request.args.get('child_phone')
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
#         user = cur.fetchone()
#         user_id = user[0] if user else None
#         role = user[1] if user else None
#         target_id = user_id
#         if role == 'ата-ана' and child_phone:
#             cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
#             child = cur2.fetchone()
#             if child:
#                 target_id = child[0]
#         cur = conn.execute('SELECT id, title, text FROM notes WHERE user_id=? ORDER BY id DESC', (target_id,))
#         notes = [{'id': row[0], 'title': row[1], 'text': row[2]} for row in cur.fetchall()]
#         children = []
#         if role == 'ата-ана':
#             cur = conn.execute('''SELECT u.first_name, u.last_name, u.phone FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE pc.parent_id=?''', (user_id,))
#             children = [{'first_name': r[0], 'last_name': r[1], 'phone': r[2]} for r in cur.fetchall()]
#     return render_template('notes.html', notes=notes, children=children, selected_child=child_phone)

# @app.route('/notes/add', methods=['POST'])
# def add_note():
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     title = request.form.get('title')
#     text = request.form.get('text')
#     if title and text:
#         with sqlite3.connect(DB_PATH) as conn:
#             cur = conn.execute('SELECT id FROM users WHERE phone=?', (session['user_phone'],))
#             user = cur.fetchone()
#             user_id = user[0] if user else None
#             if user_id:
#                 conn.execute('INSERT INTO notes (user_id, title, text) VALUES (?, ?, ?)', (user_id, title, text))
#     return redirect(url_for('notes'))

# # Schedule routes (list/add/edit/delete) — примеры, используй свои шаблоны
# @app.route('/add_lesson', methods=['POST'])
# def add_lesson():
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     day = request.form.get('day')
#     time = request.form.get('time')
#     subject = request.form.get('subject')
#     desc = request.form.get('desc')
#     child_phone = request.form.get('child_phone')
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
#         user = cur.fetchone()
#         user_id = user[0] if user else None
#         role = user[1] if user else None
#         target_id = user_id
#         if role == 'ата-ана' and child_phone:
#             cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
#             child = cur2.fetchone()
#             if child:
#                 target_id = child[0]
#         if day and time and subject and desc is not None and target_id:
#             conn.execute('INSERT INTO schedules (user_id, day, time, subject, desc) VALUES (?, ?, ?, ?, ?)',
#                          (target_id, day, time, subject, desc))
#     params = {'day': day}
#     if role == 'ата-ана' and child_phone:
#         params['child_phone'] = child_phone
#     return redirect(url_for('schedule', **params))

# @app.route('/delete_lesson', methods=['POST'])
# def delete_lesson():
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     day = request.form.get('day')
#     lesson_id = request.form.get('id')
#     child_phone = request.form.get('child_phone')
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
#         user = cur.fetchone()
#         user_id = user[0] if user else None
#         role = user[1] if user else None
#         target_id = user_id
#         if role == 'ата-ана' and child_phone:
#             cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
#             child = cur2.fetchone()
#             if child:
#                 target_id = child[0]
#         if target_id and lesson_id:
#             conn.execute('DELETE FROM schedules WHERE id=? AND user_id=?', (lesson_id, target_id))
#     params = {'day': day}
#     if role == 'ата-ана' and child_phone:
#         params['child_phone'] = child_phone
#     return redirect(url_for('schedule', **params))

# @app.route('/edit_lesson', methods=['POST'])
# def edit_lesson():
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     day = request.form.get('day')
#     lesson_id = request.form.get('id')
#     time = request.form.get('time')
#     subject = request.form.get('subject')
#     desc = request.form.get('desc')
#     child_phone = request.form.get('child_phone')
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
#         user = cur.fetchone()
#         user_id = user[0] if user else None
#         role = user[1] if user else None
#         target_id = user_id
#         if role == 'ата-ана' and child_phone:
#             cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
#             child = cur2.fetchone()
#             if child:
#                 target_id = child[0]
#         if target_id and lesson_id:
#             conn.execute('UPDATE schedules SET time=?, subject=?, desc=? WHERE id=? AND user_id=?',
#                          (time, subject, desc, lesson_id, target_id))
#     params = {'day': day}
#     if role == 'ата-ана' and child_phone:
#         params['child_phone'] = child_phone
#     return redirect(url_for('schedule', **params))

# @app.route('/', methods=['GET'])
# def schedule():
#     # основной рендер расписания
#     if 'user_phone' not in session:
#         return redirect(url_for('login'))
#     day = request.args.get('day', 'Дүйсенбі')
#     child_phone = request.args.get('child_phone')
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.execute('SELECT id, role FROM users WHERE phone=?', (session['user_phone'],))
#         user = cur.fetchone()
#         user_id = user[0] if user else None
#         role = user[1] if user else None
#         target_id = user_id
#         if role == 'ата-ана' and child_phone:
#             cur2 = conn.execute('''SELECT u.id FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE u.phone=? AND pc.parent_id=?''', (child_phone, user_id))
#             child = cur2.fetchone()
#             if child:
#                 target_id = child[0]
#         cur = conn.execute('SELECT id, time, subject, desc FROM schedules WHERE user_id=? AND day=? ORDER BY time', (target_id, day))
#         lessons = [{'id': r[0], 'time': r[1], 'subject': r[2], 'desc': r[3]} for r in cur.fetchall()]
#         children = []
#         if role == 'ата-ана':
#             cur = conn.execute('''SELECT u.first_name, u.last_name, u.phone FROM users u JOIN parent_child pc ON u.id = pc.child_id WHERE pc.parent_id=?''', (user_id,))
#             children = [{'first_name': r[0], 'last_name': r[1], 'phone': r[2]} for r in cur.fetchall()]
#     return render_template('schedule.html', lessons=lessons, days=days_list, current_day=day, children=children, selected_child=child_phone)

# # ---------------- Auto set webhook on startup ----------------
# # Попробуем установить вебхук при старте (Render должен разрешать исходящие запросы)
# try:
#     bot.remove_webhook()
#     set_ok = bot.set_webhook(url=WEBHOOK_URL)
#     print("Auto set_webhook result:", set_ok, "WEBHOOK_URL:", WEBHOOK_URL)
# except Exception as e:
#     print("Auto set_webhook failed:", e)

# # ---------------- Run (для локального запуска; на Render запускает gunicorn) ----------------
# if __name__ == "__main__":
#     # локально: не забудь, что webhook не будет работать если сервер не доступен извне
#     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
from flask import Flask, request
import telebot

TOKEN = "8020072349:AAH3xnHE9OtZQJ8HZhVBlTGDsyhWuYj4XBg"
bot = telebot.TeleBot(TOKEN, threaded=False)  # threaded=False важно для вебхука

app = Flask(__name__)

@app.route('/' + TOKEN, methods=['POST'])
def receive_update():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/", methods=['GET'])
def index():
    return "Бот работает!", 200

# обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Привет! Я бот расписания.")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
