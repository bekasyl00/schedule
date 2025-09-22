import os
import sqlite3
import datetime
import logging
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

# ---------------- Configuration ----------------
BOT_TOKEN = "8020072349:AAH3xnHE9OtZQJ8HZhVBlTGDsyhWuYj4XBg"
WEBHOOK_URL = "https://schedule-1-oo31.onrender.com/" + BOT_TOKEN  # твой render-домен + токен
WEBHOOK_SECRET = ""  # если хочешь защиту: поставь строку и вызывать /set_webhook?secret=xxx

# Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telebot
bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- Database ----------------
DB_PATH = os.path.join(os.path.dirname(__file__), "notes.db")

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
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
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

# ---------------- Telegram handlers ----------------
days_list = ['Дүйсенбі','Сейсенбі','Сәрсенбі','Бейсенбі','Жұма','Сенбі','Жексенбі']

@bot.message_handler(commands=['start'])
def handle_start(message):
    logger.info("Handler /start called: chat_id=%s", message.chat.id)
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Күнделікті көру'))
    bot.send_message(chat_id, 'Сәлем! Телефоныңызды енгізіңіз (тек цифры):', reply_markup=markup)
    bot.register_next_step_handler(message, save_phone)

def save_phone(message):
    logger.info("save_phone called for chat_id=%s text=%s", message.chat.id, message.text)
    chat_id = message.chat.id
    phone = message.text.strip()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id FROM users WHERE phone=?', (phone,))
        user = cur.fetchone()
        if user:
            user_id = user[0]
            conn.execute('INSERT OR IGNORE INTO telegram_users (user_id, chat_id) VALUES (?, ?)', (user_id, chat_id))
            bot.send_message(chat_id, 'Телефон тіркелді! Енді сізге сабақ туралы ескертулер келеді.')
        else:
            bot.send_message(chat_id, 'Бұл телефон табылмады. Алдымен сайтта тіркеліңіз.')

@bot.message_handler(func=lambda m: m.text == 'Күнделікті көру')
def show_days(message):
    logger.info("show_days for chat_id=%s", message.chat.id)
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for day in days_list:
        markup.add(types.KeyboardButton(day))
    bot.send_message(chat_id, 'Қай күнді көргіңіз келеді?', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in days_list)
def show_schedule_for_day(message):
    logger.info("show_schedule_for_day chat=%s day=%s", message.chat.id, message.text)
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

# ---------------- Webhook endpoint ----------------
@app.route("/" + BOT_TOKEN, methods=["POST"])
def receive_update():
    # Telegram будет POST-ить JSON сюда
    try:
        json_str = request.get_data().decode("utf-8")
        logger.info("Incoming update: %s", json_str)
        # For debug: print to stdout too (Render logs)
        print("UPDATE:", json_str)
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        logger.exception("Error processing update")
        return "error", 500
    return "ok", 200

# ---------------- Optional: set/remove webhook endpoint ----------------
@app.route("/set_webhook", methods=["GET", "POST"])
def set_webhook_route():
    secret = request.args.get("secret", "")
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        return jsonify({"ok": False, "error": "bad secret"}), 403

    try:
        bot.remove_webhook()
        ok = bot.set_webhook(url=WEBHOOK_URL)
        logger.info("Manual set_webhook result: %s", ok)
        return jsonify({"ok": True, "set_webhook": ok, "webhook_url": WEBHOOK_URL}), 200
    except Exception as e:
        logger.exception("set_webhook error")
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------------- Scheduler reminders ----------------
def send_reminder():
    now = datetime.datetime.datetime.now() if hasattr(datetime, 'datetime') else datetime.datetime.now()
    # compat: sometimes datetime imported as module only
    if isinstance(now, datetime.datetime) is False:
        now = datetime.datetime.now()
    days_map = {'Дүйсенбі':0,'Сейсенбі':1,'Сәрсенбі':2,'Бейсенбі':3,'Жұма':4,'Сенбі':5,'Жексенбі':6}
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT s.subject, s.time, s.day, u.id FROM schedules s JOIN users u ON s.user_id = u.id')
        for subject, time_str, day_str, user_id in cur.fetchall():
            lesson_weekday = days_map.get(day_str)
            if lesson_weekday is None:
                continue
            today_weekday = now.weekday()
            days_ahead = (lesson_weekday - today_weekday) % 7
            lesson_date = now.date() + datetime.timedelta(days=days_ahead)
            try:
                lesson_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            except Exception:
                continue
            lesson_dt = datetime.datetime.combine(lesson_date, lesson_time)
            delta_seconds = (lesson_dt - now).total_seconds()
            if 82800 <= delta_seconds <= 87600 or 3540 <= delta_seconds <= 4260:
                msg = f"⏰ Ескерту! Сабақ: {subject} {lesson_dt.strftime('%A %H:%M')}"
                cur2 = conn.execute('SELECT chat_id FROM telegram_users WHERE user_id=?', (user_id,))
                for row in cur2.fetchall():
                    try:
                        bot.send_message(row[0], msg)
                    except Exception as e:
                        logger.exception("Ошибка отправки reminder")

scheduler = BackgroundScheduler()
scheduler.add_job(send_reminder, "interval", minutes=1)
scheduler.start()

# ---------------- Your Flask routes (register/login/profile/schedule/notes) ----------------
@app.route("/")
def index():
    return "Flask + Telegram бот работает! Отправь /start в Telegram боту."

# (Остальные маршруты: register/login/profile/notes/add_lesson и т.д.)
# Для краткости: вставь сюда свои маршруты, как у тебя в основном коде.
# Пример: route /schedule -> render_template('schedule.html', ...)

# ---------------- Auto set webhook on startup ----------------
try:
    bot.remove_webhook()
    set_ok = bot.set_webhook(url=WEBHOOK_URL)
    logger.info("Auto set_webhook result: %s WEBHOOK_URL: %s", set_ok, WEBHOOK_URL)
    print("Auto set_webhook result:", set_ok, "WEBHOOK_URL:", WEBHOOK_URL)
except Exception as e:
    logger.exception("Auto set_webhook failed")

# ---------------- Run (локально) ----------------
if __name__ == "__main__":
    # локально: webhook не будет работать без публичного URL — используй ngrok или деплой
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
