from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

# Наши "экспонаты" - просто список словарей
exhibits = [
    {"id": 1, "name": "Картина 'Звездная ночь'", "room": "Зал 1"},
    {"id": 2, "name": "Статуя 'Давид'", "room": "Зал 2"}
]

# Главная страница
@app.route('/')
def home():
    return render_template('museum.html', exhibits=exhibits)

# API: Показать все экспонаты (JSON)
@app.route('/api/exhibits')
def api_exhibits():
    return jsonify(exhibits)

# API: Добавить новый экспонат (JSON)
@app.route('/api/add', methods=['POST'])
def api_add_exhibit():
    data = request.json
    if 'name' in data and 'room' in data:
        new_id = max(ex['id'] for ex in exhibits) + 1 if exhibits else 1
        new_exhibit = {
            "id": new_id,
            "name": data['name'],
            "room": data['room']
        }
        exhibits.append(new_exhibit)
        return jsonify({"status": "success", "exhibit": new_exhibit}), 201
    return jsonify({"status": "error", "message": "Не указано название или зал"}), 400

# Веб-интерфейс: Добавить экспонат (форма)
@app.route('/add', methods=['GET', 'POST'])
def add_exhibit():
    if request.method == 'POST':
        name = request.form.get('name')
        room = request.form.get('room')
        if name and room:
            new_id = max(ex['id'] for ex in exhibits) + 1 if exhibits else 1
            exhibits.append({"id": new_id, "name": name, "room": room})
            return render_template('museum.html', exhibits=exhibits, message=f"Добавлен новый экспонат: {name} в {room}")
        return render_template('museum.html', exhibits=exhibits, error="Ошибка: не указано название или зал")
    return render_template('museum.html', exhibits=exhibits)

if __name__ == '__main__':
    app.run(debug=True)



