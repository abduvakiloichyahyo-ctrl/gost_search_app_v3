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
    try:
        return response.json()
    except Exception:
        return {}


# --- Работа с локальными данными ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    push_to_github()


# --- Отправляем файл в GitHub ---
def push_to_github():
    try:
        with open(DATA_FILE, "rb") as f:
            content = f.read()
        encoded = base64.b64encode(content).decode()
        file_info = github_api_request("GET", f"contents/{GITHUB_FILE_PATH}")
        sha = file_info.get("sha")
        github_api_request("PUT", f"contents/{GITHUB_FILE_PATH}", {
            "message": "Автообновление gost_data.json через сайт",
            "content": encoded,
            "sha": sha
        })
        print("✅ Файл gost_data.json отправлен в GitHub")
    except Exception as e:
        print("⚠ Ошибка при отправке в GitHub:", e)


# ---------- HTML шаблоны ----------
TEMPLATE_INDEX = """<html>
<head>
<meta charset='utf-8'>
<title>ГОСТ База — Поиск ГОСТов</title>
<link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
<style>
body { font-family: "Segoe UI", sans-serif; margin: 0; color: #fff; overflow-y: auto; background: #000; }
video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
.overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
.container { position: relative; z-index: 2; width: 600px; margin: 50px auto; text-align: center; background: rgba(255,255,255,0.08); padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.4); backdrop-filter: blur(8px); }
h1 { font-weight: 300; margin-bottom: 20px; }
input[type=text] { padding: 10px; width: 65%; border: none; border-radius: 4px; outline: none; font-size: 16px; }
button { padding: 10px 18px; border: none; background: #007bff; color: #fff; border-radius: 4px; cursor: pointer; font-size: 16px; }
button:hover { background: #0056b3; }
a { text-decoration: none; color: #fff; margin: 0 10px; }
a:hover { text-decoration: underline; }
div.result { background: rgba(255,255,255,0.1); padding: 10px; margin-top: 10px; border-radius: 6px; text-align: left; }
</style>
</head>
<body>

<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>
<div class="overlay"></div>

<div class="container">
  <h1>🔍 Поиск ГОСТов</h1>
  <form method='get'>
    <input type='text' name='q' value='{{ query }}' placeholder='Введите номер ГОСТа...'>
    <button type='submit'>Искать</button>
  </form>
  <p>
    <a href='{{ url_for("add_gost") }}'>➕ Добавить ГОСТ</a> |
    <a href='{{ url_for("list_gosts") }}'>📋 Список ГОСТов</a>
  </p>
  {% if results %}
  <h2>Результаты:</h2>
  {% for gost, text in results.items() %}
    <div class="result"><b>{{ gost }}</b><br>{{ text }}</div>
  {% endfor %}
  {% elif query %}
  <p>Ничего не найдено.</p>
  {% endif %}
</div>

</body>
</html>"""

TEMPLATE_ADD = """<html>
<head>
<meta charset='utf-8'>
<title>Добавить ГОСТ</title>
<link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
<style>
body { 
  font-family: "Segoe UI", sans-serif; 
  margin: 0; color: #fff; overflow-y: auto; background: #000; 
}
video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
.overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
.container { position: relative; z-index: 2; width: 500px; margin: 50px auto; background: rgba(255,255,255,0.08); padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.4); backdrop-filter: blur(8px); text-align: center; }
h1 { font-weight: 300; margin-bottom: 20px; }
input, textarea { width: 100%; padding: 10px; border: none; border-radius: 4px; margin-bottom: 12px; font-size: 15px; }
button { padding: 10px 18px; border: none; background: #28a745; color: #fff; border-radius: 4px; cursor: pointer; font-size: 16px; }
button:hover { background: #218838; }
a { color: #fff; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>
<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>
<div class="overlay"></div>

<div class="container">
<h1>➕ Добавить ГОСТ</h1>
<form method='post'>
<input type='text' name='gost_number' placeholder='Номер ГОСТа' required><br>
<input type='text' name='gost_mark' placeholder='Маркировка ГОСТа' required><br>
<textarea name='gost_text' placeholder='Пункты ГОСТа' rows="6" required></textarea><br>
<button type='submit'>💾 Сохранить</button>
</form>
<p><a href='{{ url_for("index") }}'>⬅ Назад</a></p>
</div>
</body>
</html>"""

TEMPLATE_LIST = """<html>
<head>
<meta charset='utf-8'>
<title>📋 Список ГОСТов</title>
<link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
<style>
body { font-family: "Segoe UI", sans-serif; margin: 0; color: #fff; overflow-y: auto; background: #000; }
video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
.overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
.container { position: relative; z-index: 2; width: 700px; margin: 50px auto; background: rgba(255,255,255,0.08); padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.4); backdrop-filter: blur(8px); }
h1 { text-align: center; font-weight: 300; }
a { color: #fff; text-decoration: none; }
a:hover { text-decoration: underline; }
div.result { background: rgba(255,255,255,0.1); padding: 10px; margin-top: 10px; border-radius: 6px; }
button { padding: 6px 10px; border: none; border-radius: 4px; cursor: pointer; }
.btn-delete { background: #dc3545; color: #fff; }
.btn-edit { background: #ffc107; color: #000; }
.btn-delete:hover { background: #c82333; }
.btn-edit:hover { background: #e0a800; }
.back { display: inline-block; margin-top: 20px; background: #007bff; color: #fff; padding: 10px 15px; border-radius: 6px; text-decoration: none; }
.back:hover { background: #0056b3; }
</style>
</head>
<body>

<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>
<div class="overlay"></div>

<div class="container">
  <h1>📋 Все ГОСТы</h1>
  {% for gost, text in data.items() %}
    <div class="result">
  <b>{{ gost }}</b><br>{{ text }}<br>
  <a class="btn-edit" href="{{ url_for('edit_gost', gost=gost) }}">✏ Редактировать</a>
  <a class="btn-delete" href="{{ url_for('delete_gost', gost=gost) }}"
     onclick="return confirm('Вы точно хотите удалить {{ gost }}?');">
     🗑 Удалить
  </a>
</div>
  {% endfor %}
  <a class="back" href="{{ url_for('index') }}">⬅ Назад</a>
</div>

</body>
</html>"""

# ---------- Flask маршруты ----------
@app.route("/", methods=["GET"])
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
if request.method == "POST":
    data = load_data()
    gost_number = request.form["gost_number"].strip()
    gost_mark = request.form["gost_mark"].strip()
    gost_text = request.form["gost_text"].strip()
    data[gost_number] = {
        "text": gost_text,
        "mark": gost_mark
    }
    save_data(data)
    return redirect(url_for("list_gosts"))


@app.route("/list", methods=["GET"])
def list_gosts():
    data = load_data()
    return render_template_string(TEMPLATE_LIST, data=data)


@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    data = load_data()
    if request.method == "POST":
        data[gost] = request.form["gost_text"].strip()
        save_data(data)
        return redirect(url_for("list_gosts"))
    text = data.get(gost, "")
    return render_template_string("""
    <html><body>
    <h1>Редактировать {{ gost }}</h1>
    <form method="post">
        <textarea name="gost_text" rows="10" cols="50">{{ text }}</textarea><br>
        <button type="submit">💾 Сохранить</button>
    </form>
    <a href="{{ url_for('list_gosts') }}">⬅ Назад</a>
    </body></html>
    """, gost=gost, text=text)


@app.route("/delete/<gost>")
def delete_gost(gost):
    data = load_data()
    if gost in data:
        del data[gost]
        save_data(data)
    return redirect(url_for("list_gosts"))


# ---------- Запуск ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




