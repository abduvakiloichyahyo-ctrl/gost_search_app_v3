from flask import Flask, render_template_string, request, redirect, url_for
import json
import os

app = Flask(__name__)

DATA_FILE = "gost_data.json"

# Загружаем базу ГОСТов
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Сохраняем базу ГОСТов
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route("/", methods=["GET", "POST"])
def index():
    gost_data = load_data()
    search_query = request.args.get("q", "").lower().strip()
    results = {}

    if search_query:
       for gost, text in data.items():
    # Преобразуем пункты в одну строку (если это список)
    text_combined = " ".join(text) if isinstance(text, list) else str(text)

    if search_query in gost.lower() or search_query in text_combined.lower():
        results[gost] = text

    return render_template_string(TEMPLATE_INDEX, results=results, query=search_query)

@app.route("/add", methods=["GET", "POST"])
def add_gost():
    gost_data = load_data()
    if request.method == "POST":
        gost_number = request.form["gost_number"].strip()
        gost_text = request.form["gost_text"].strip()
        if gost_number and gost_text:
            gost_data[gost_number] = gost_text
            save_data(gost_data)
            return redirect(url_for("index"))
    return render_template_string(TEMPLATE_ADD)

@app.route("/list")
def list_gosts():
    gost_data = load_data()
    return render_template_string(TEMPLATE_LIST, gost_data=gost_data)

@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    gost_data = load_data()
    if gost not in gost_data:
        return "ГОСТ не найден", 404

    if request.method == "POST":
        new_text = request.form["gost_text"].strip()
        gost_data[gost] = new_text
        save_data(gost_data)
        return redirect(url_for("list_gosts"))

    return render_template_string(TEMPLATE_EDIT, gost=gost, text=gost_data[gost])

@app.route("/delete/<gost>")
def delete_gost(gost):
    gost_data = load_data()
    if gost in gost_data:
        del gost_data[gost]
        save_data(gost_data)
    return redirect(url_for("list_gosts"))

# ---------- HTML шаблоны ----------

TEMPLATE_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Поиск ГОСТов</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f8f9fa; }
        h1 { color: #333; }
        input[type=text] { width: 300px; padding: 5px; }
        button { padding: 5px 10px; cursor: pointer; }
        .result { background: white; padding: 10px; margin-top: 10px; border-radius: 5px; }
        a { text-decoration: none; color: #007bff; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>🔍 Поиск по ГОСТам</h1>
    <form method="get">
        <input type="text" name="q" value="{{ query }}" placeholder="Введите номер ГОСТа...">
        <button type="submit">Искать</button>
    </form>
    <p><a href="{{ url_for('add_gost') }}">➕ Добавить ГОСТ</a> | 
       <a href="{{ url_for('list_gosts') }}">📋 Список ГОСТов</a></p>

    {% if results %}
        <h2>Результаты:</h2>
        {% for gost, text in results.items() %}
            <div class="result">
                <b>{{ gost }}</b><br>{{ text }}
            </div>
        {% endfor %}
    {% elif query %}
        <p>Ничего не найдено.</p>
    {% endif %}
</body>
</html>
"""

TEMPLATE_ADD = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Добавить ГОСТ</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f8f9fa; }
        textarea { width: 400px; height: 150px; }
    </style>
</head>
<body>
    <h1>➕ Добавить новый ГОСТ</h1>
    <form method="post">
        <p>Номер ГОСТа:<br><input type="text" name="gost_number" required></p>
        <p>Пункты внешнего осмотра:<br><textarea name="gost_text" required></textarea></p>
        <button type="submit">Сохранить</button>
    </form>
    <p><a href="{{ url_for('index') }}">⬅ Вернуться</a></p>
</body>
</html>
"""

TEMPLATE_LIST = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Список ГОСТов</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f8f9fa; }
        table { border-collapse: collapse; width: 100%; background: white; }
        td, th { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background: #eee; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .actions { white-space: nowrap; }
    </style>
</head>
<body>
    <h1>📋 Все ГОСТы</h1>
    <table>
        <tr><th>Номер ГОСТа</th><th>Пункты</th><th>Действия</th></tr>
        {% for gost, text in gost_data.items() %}
        <tr>
            <td><b>{{ gost }}</b></td>
            <td>{{ text[:100] }}{% if text|length > 100 %}...{% endif %}</td>
            <td class="actions">
                <a href="{{ url_for('edit_gost', gost=gost) }}">✏️ Редактировать</a> |
                <a href="{{ url_for('delete_gost', gost=gost) }}" onclick="return confirm('Удалить ГОСТ {{ gost }}?')">🗑 Удалить</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    <p><a href="{{ url_for('index') }}">⬅ Вернуться</a></p>
</body>
</html>
"""

TEMPLATE_EDIT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Редактировать ГОСТ</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f8f9fa; }
        textarea { width: 400px; height: 150px; }
    </style>
</head>
<body>
    <h1>✏️ Редактирование {{ gost }}</h1>
    <form method="post">
        <p>Пункты внешнего осмотра:<br><textarea name="gost_text" required>{{ text }}</textarea></p>
        <button type="submit">💾 Сохранить изменения</button>
    </form>
    <p><a href="{{ url_for('list_gosts') }}">⬅ Назад</a></p>
</body>
</html>
"""

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask запущен на 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)


