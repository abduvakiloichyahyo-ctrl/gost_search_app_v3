from flask import Flask, render_template_string, request, redirect, url_for
import json, os, base64, requests

# ✅ Функция для обращения к OpenRouter AI
def ask_openrouter(query):
    """
    Отправляет запрос к OpenRouter AI и возвращает ответ в виде текста.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")  # ключ из Render
        if not api_key:
            return "⚠️ Ошибка: отсутствует OPENROUTER_API_KEY"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "gpt-4o-mini",  # быстрая и недорогая AI-модель
            "messages": [
                {
                    "role": "system",
                    "content": "Ты эксперт по ГОСТам и техническим стандартам. Отвечай кратко и по делу.",
                },
                {"role": "user", "content": query},
            ],
        }

        response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                 headers=headers, json=data)
        if response.status_code != 200:
            return f"Ошибка API OpenRouter: {response.text}"

        ai_text = response.json()["choices"][0]["message"]["content"]
        return ai_text.strip()

    except Exception as e:
        return f"⚠️ Ошибка запроса к OpenRouter: {e}"


app = Flask(__name__)

DATA_FILE = "gost_data.json"

# --- Настройки GitHub ---
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_FILE_PATH = "gost_data.json"

# --- OpenRouter (бесплатный AI) ключ из окружения ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# модель можно поменять на ту, которая доступна в твоём OpenRouter аккаунте
AI_MODEL = "gpt-4-turbo"

def github_api_request(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/{endpoint}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.request(method, url, headers=headers, json=data)
    if response.status_code >= 400:
        print("GitHub API error:", response.text)
    # попытка вернуть json или пустой объект при ошибке парсинга
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
body {
  font-family: "Segoe UI", sans-serif;
  margin: 0;
  height: 100vh;
  overflow: hidden;
  color: #fff;
}
video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
.overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
.container {
  position: relative; z-index: 2; width: 600px; margin: auto; text-align: center; top: 50%; transform: translateY(-50%);
  background: rgba(255,255,255,0.08); padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.4);
  backdrop-filter: blur(8px);
}
h1 { font-weight: 300; margin-bottom: 20px; }
input[type=text] { padding: 10px; width: 65%; border: none; border-radius: 4px; outline: none; font-size: 16px; }
button {
  padding: 10px 18px; border: none; background: #007bff; color: #fff; border-radius: 4px; cursor: pointer; font-size: 16px;
}
button:hover { background: #0056b3; }
a { text-decoration: none; color: #fff; margin: 0 10px; }
a:hover { text-decoration: underline; }
div.result { background: rgba(255,255,255,0.1); padding: 10px; margin-top: 10px; border-radius: 6px; }
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
    <!-- Кнопка AI: отправляет запрос на /ai_search методом POST -->
    <button formaction="{{ url_for('ai_search') }}" formmethod="post">AI поиск 🤖</button>
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
  {% elif ai_result %}
  <h2>Результат AI:</h2>
  <div class="result">{{ ai_result }}</div>
  {% elif query %}
  <p>Ничего не найдено.</p>
  {% endif %}
</div>

</body>
</html>"""

TEMPLATE_ADD = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Добавить ГОСТ</title>
    <style>
        body { background: #1e1e2f; color: white; font-family: sans-serif; text-align: center; padding: 40px; }
        input, textarea { width: 60%; padding: 10px; border-radius: 10px; border: none; margin-bottom: 15px; }
        button { padding: 10px 20px; background: #4caf50; border: none; border-radius: 10px; color: white; cursor: pointer; }
        button:hover { background: #388e3c; }
    </style>
</head>
<body>
    <h1>➕ Добавить новый ГОСТ</h1>
    <form method="POST">
        <input name="gost_number" placeholder="Номер ГОСТ" required><br>
        <textarea name="gost_text" placeholder="Описание или содержание" rows="5" required></textarea><br>
        <button type="submit">Сохранить</button>
    </form>
    <a href="/">🏠 Назад</a>
</body>
</html>
"""

TEMPLATE_LIST = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Список ГОСТов</title>
    <style>
        body { background: #101820; color: white; font-family: sans-serif; text-align: center; padding: 30px; }
        table { margin: 0 auto; border-collapse: collapse; width: 80%; }
        td, th { border: 1px solid #555; padding: 10px; }
        a { color: #00bcd4; text-decoration: none; }
    </style>
</head>
<body>
    <h1>📜 Все ГОСТы</h1>
    <table>
        <tr><th>Номер</th><th>Описание</th><th>Действия</th></tr>
        {% for gost, text in gost_data.items() %}
        <tr>
            <td>{{ gost }}</td>
            <td>{{ text }}</td>
            <td>
                <a href="{{ url_for('edit_gost', gost=gost) }}">✏️</a> |
                <a href="{{ url_for('delete_gost', gost=gost) }}">🗑</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    <br>
    <a href="/">🏠 На главную</a>
</body>
</html>
"""

TEMPLATE_EDIT = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Редактировать ГОСТ</title>
    <style>
        body { background: #1b1b2f; color: white; font-family: sans-serif; text-align: center; padding: 40px; }
        textarea { width: 70%; height: 200px; padding: 10px; border-radius: 10px; border: none; }
        button { padding: 10px 20px; background: #2196f3; border: none; border-radius: 10px; color: white; cursor: pointer; }
        button:hover { background: #1976d2; }
    </style>
</head>
<body>
    <h1>✏️ Редактировать {{ gost }}</h1>
    <form method="POST">
        <textarea name="gost_text">{{ text }}</textarea><br>
        <button type="submit">💾 Сохранить</button>
    </form>
    <a href="/list">📜 К списку</a>
</body>
</html>
"""


# ---------- Flask маршруты ----------
@app.route("/", methods=["GET"])
def index():
    data = load_data()
    search_query = request.args.get("q", "").lower().strip()
    results = {}
    ai_result = None

    if search_query:
        for gost, text in data.items():
            text_combined = " ".join(text) if isinstance(text, list) else str(text)
            if search_query in gost.lower() or search_query in text_combined.lower():
                results[gost] = text_combined

        # Если обычный поиск ничего не дал — попытаемся использовать AI
        if not results:
           ai_result = ask_openrouter(search_query)

    return render_template_string(TEMPLATE_INDEX, results=results, query=search_query, ai_result=ai_result)


@app.route("/ai_search", methods=["POST"])
def ai_search():
    query = request.form.get("q", "").strip()
    if not query:
        return redirect(url_for("index"))

    ai_text = ask_openrouter(query)
    return render_template_string(TEMPLATE_INDEX, results=None, ai_result=ai_text, query=query)


@app.route("/add", methods=["GET", "POST"])
def add_gost():
    if request.method == "POST":
        data = load_data()
        gost_number = request.form["gost_number"].strip()
        gost_text = request.form["gost_text"].strip()
        data[gost_number] = gost_text
        save_data(data)
        return redirect(url_for("add_gost"))
    return render_template_string(TEMPLATE_ADD)


@app.route("/list", methods=["GET"])
def list_gosts():
    data = load_data()
    return render_template_string(TEMPLATE_LIST, gost_data=data)


@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    data = load_data()
    if request.method == "POST":
        data[gost] = request.form["gost_text"].strip()
        save_data(data)
        return redirect(url_for("edit_gost", gost=gost))
    text = data.get(gost, "")
    return render_template_string(TEMPLATE_EDIT, gost=gost, text=text)


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

