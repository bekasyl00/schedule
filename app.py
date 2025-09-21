
from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)

# Временное хранилище расписания уроков (по дням недели)
lessons_schedule = {
    'Дүйсенбі': [
        {'time': '08:00', 'subject': 'Математика', 'desc': 'Тригонометрия'},
        {'time': '09:00', 'subject': 'Қазақ тілі', 'desc': 'Жаттығу жұмысы'},
    ],
    'Сейсенбі': [
        {'time': '08:00', 'subject': 'Физика', 'desc': 'Механика'},
        {'time': '09:00', 'subject': 'Тарих', 'desc': 'Қазақстан тарихы'},
    ],
    'Сәрсенбі': [],
    'Бейсенбі': [],
    'Жұма': [],
    'Сенбі': [],
    'Жексенбі': [],
}


# Главная страница — расписание уроков выбранного дня
@app.route('/', methods=['GET'])
def schedule():
    day = request.args.get('day', 'Дүйсенбі')
    lessons = lessons_schedule.get(day, [])
    days = list(lessons_schedule.keys())
    return render_template('schedule.html', lessons=lessons, days=days, current_day=day)

# Добавить урок
@app.route('/add_lesson', methods=['POST'])
def add_lesson():
    day = request.form.get('day')
    time = request.form.get('time')
    subject = request.form.get('subject')
    desc = request.form.get('desc')
    if day and time and subject and desc is not None:
        lessons_schedule[day].append({'time': time, 'subject': subject, 'desc': desc})
    return redirect(url_for('schedule', day=day))

# Удалить урок
@app.route('/delete_lesson', methods=['POST'])
def delete_lesson():
    day = request.form.get('day')
    idx = int(request.form.get('idx'))
    if day in lessons_schedule and 0 <= idx < len(lessons_schedule[day]):
        lessons_schedule[day].pop(idx)
    return redirect(url_for('schedule', day=day))

# Изменить урок
@app.route('/edit_lesson', methods=['POST'])
def edit_lesson():
    day = request.form.get('day')
    idx = int(request.form.get('idx'))
    time = request.form.get('time')
    subject = request.form.get('subject')
    desc = request.form.get('desc')
    if day in lessons_schedule and 0 <= idx < len(lessons_schedule[day]):
        lessons_schedule[day][idx] = {'time': time, 'subject': subject, 'desc': desc}
    return redirect(url_for('schedule', day=day))

if __name__ == '__main__':
    app.run(debug=True)
