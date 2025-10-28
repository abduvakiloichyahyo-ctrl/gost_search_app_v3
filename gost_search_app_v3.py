from flask import Flask, render_template_string, request, redirect, url_for
import json, os, base64, requests

app = Flask(__name__)

DATA_FILE = "gost_data.json"

# --- Настройки GitHub ---
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_FILE_PATH = "gost_data.json"

def github_api_request(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/{endpoint}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.request(method, url, headers=headers, json=data)
    if response.status_code >= 400:
        print("GitHub API error:", response.text)
    return response.json()

# --- Работа с локальными данными ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    push_to_github()

# --- Отправляем файл в GitHub ---
def push_to_github():
    try:
        # 1. Считываем локальный файл
        with open(DATA_FILE, "rb") as f:
            content = f.read()
        encoded = base64.b64encode(content).decode()

        # 2. Получаем SHA текущей версии файла
        file_info = github_api_request("GET", f"contents/{GITHUB_FILE_PATH}")
        sha = file_info.get("sha")

        # 3. Отправляем обновлённый файл
        github_api_request("PUT", f"contents/{GITHUB_FILE_PATH}", {
            "message": "Автообновление gost_data.json через сайт",
            "content": encoded,
            "sha": sha
        })
        print("✅ Файл gost_data.json отправлен в GitHub")
    except Exception as e:
        print("⚠ Ошибка при отправке в GitHub:", e)

# --- Flask маршруты ---
@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()
    search_query = request.args.get("q", "").lower().strip()
    results = {}

    if search_query:
        for gost, text in data.items():
            text_combined = " ".join(text) if isinstance(text, list) else str(text)
            if search_query in gost.lower() or search_query in text_combined.lower():
                results[gost] = text_combined

    return render_template_string(TEMPLATE_INDEX, results=results, query=search_query)

@app.route("/add", methods=["GET", "POST"])
def add_gost():
    data = load_data()
    if request.method == "POST":
        gost_number = request.form["gost_number"].strip()
        gost_text = request.form["gost_text"].strip()
        if gost_number and gost_text:
            data[gost_number] = gost_text
            save_data(data)
            return redirect(url_for("index"))
    return render_template_string(TEMPLATE_ADD)

@app.route("/list")
def list_gosts():
    data = load_data()
    return render_template_string(TEMPLATE_LIST, gost_data=data)

@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    data = load_data()
    if gost not in data:
        return "ГОСТ не найден", 404

    if request.method == "POST":
        new_text = request.form["gost_text"].strip()
        data[gost] = new_text
        save_data(data)
        return redirect(url_for("list_gosts"))

    return render_template_string(TEMPLATE_EDIT, gost=gost, text=data[gost])

@app.route("/delete/<gost>")
def delete_gost(gost):
    data = load_data()
    if gost in data:
        del data[gost]
        save_data(data)
    return redirect(url_for("list_gosts"))

# ---------- HTML шаблоны (без изменений) ----------
TEMPLATE_INDEX = """<html><head><meta charset='utf-8'><title>Поиск ГОСТов</title></head>
<body><h1>🔍 Поиск ГОСТов</h1>
<form method='get'><input type='text' name='q' value='{{ query }}' placeholder='Введите номер ГОСТа...'>
<button type='submit'>Искать</button></form>
<p><a href='{{ url_for("add_gost") }}'>➕ Добавить ГОСТ</a> | <a href='{{ url_for("list_gosts") }}'>📋 Список ГОСТов</a></p>
{% if results %}<h2>Результаты:</h2>{% for gost, text in results.items() %}
<div><b>{{ gost }}</b><br>{{ text }}</div>{% endfor %}{% elif query %}<p>Ничего не найдено.</p>{% endif %}</body></html>"""

TEMPLATE_ADD = """<html><head><meta charset='utf-8'><title>Добавить ГОСТ</title></head>
<body><h1>Добавить новый ГОСТ</h1><form method='post'>
<p>Номер ГОСТа:<br><input type='text' name='gost_number'></p>
<p>Пункты:<br><textarea name='gost_text'></textarea></p>
<button type='submit'>Сохранить</button></form>
<p><a href='{{ url_for("index") }}'>⬅ Назад</a></p></body></html>"""

TEMPLATE_LIST = """<html><head><meta charset='utf-8'><title>Список ГОСТов</title></head>
<body><h1>📋 Список ГОСТов</h1><table border=1>
<tr><th>Номер</th><th>Текст</th><th>Действия</th></tr>
{% for gost, text in gost_data.items() %}
<tr><td>{{ gost }}</td><td>{{ text }}</td>
<td><a href='{{ url_for("edit_gost", gost=gost) }}'>✏️</a> | 
<a href='{{ url_for("delete_gost", gost=gost) }}'>🗑</a></td></tr>{% endfor %}
</table><p><a href='{{ url_for("index") }}'>⬅ Назад</a></p></body></html>"""

TEMPLATE_EDIT = """<html><head><meta charset='utf-8'><title>Редактировать ГОСТ</title></head>
<body><h1>Редактировать {{ gost }}</h1>
<form method='post'><textarea name='gost_text'>{{ text }}</textarea><br>
<button type='submit'>💾 Сохранить</button></form>
<p><a href='{{ url_for("list_gosts") }}'>⬅ Назад</a></p></body></html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask запущен на 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
