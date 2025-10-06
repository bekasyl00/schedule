import os
import sys
import sqlite3
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# Импортируем функцию send_reminder из твоего main.py
sys.path.append(os.path.dirname(__file__))
from app import send_reminder

scheduler = BlockingScheduler()

# Запуск напоминаний каждую минуту
scheduler.add_job(send_reminder, 'interval', minutes=1)

print("Scheduler started...")
scheduler.start()
