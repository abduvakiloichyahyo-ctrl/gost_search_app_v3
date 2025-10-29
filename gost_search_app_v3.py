from flask import Flask, render_template_string, request, redirect, url_for
import json, os, base64, requests

app = Flask(__name__)

DATA_FILE = "gost_data.json"

# --- Настройки GitHub ---
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_FILE_PATH = "gost_data.json"

# --- OpenRouter (бесплатный AI) ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ---------- AI функция ----------
def ask_openrouter(query):
    """Запрос к OpenRouter AI"""
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "⚠️ Ошибка: не найден OPENROUTER_API_KEY"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Ты эксперт по ГОСТам. Отвечай кратко и по существу."},
                {"role": "user", "content": query},
            ],
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        if response.status_code != 200:
            return f"Ошибка API OpenRouter: {response.text}"

        ai_text = response.json()["choices"][0]["message"]["content"]
        return ai_text.strip()

    except Exception as e:
        return f"⚠️ Ошибка запроса к OpenRouter: {e}"


# ---------- GitHub ----------
def github_api_request(method, endpoint, data=None):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/{endpoint}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    response = requests.request(method, url, headers=headers, json=data)
    if response.status_code >= 400:
        print("GitHub API error:", response.text)
    try:
        return response.json()
    except Exception:
        return {}

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
        print("✅ Файл gost_data.json успешно загружен на GitHub")
    except Exception as e:
        print("⚠ Ошибка при отправке в GitHub:", e)


# ---------- HTML шаблоны ----------
TEMPLATE_INDEX = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Поиск ГОСТ</title>
    <style>
        body {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: white;
            font-family: 'Segoe UI', sans-serif;
            text-align: center;
            margin: 0;
            padding: 40px;
        }
        input {
            padding: 10px;
            width: 300px;
            border: none;
            border-radius: 10px;
        }
        button {
            padding: 10px 20px;
            border: none;
            background: #00bcd4;
            color: white;
            border-radius: 10px;
            cursor: pointer;
        }
        button:hover { background: #0097a7; }
        .result {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            margin-top: 20px;
            border-radius: 10px;
            text-align: left;
            width: 60%;
            margin-left: auto;
            margin-right: auto;
        }
        a { color: #80deea; text-decoration: none; }
    </style>
</head>
<body>
    <h1>🔍 Поиск по ГОСТам</h1>
    <form method="GET">
        <input type="text" name="q" placeholder="Введите номер или описание ГОСТ" value="{{ query or '' }}">
        <button type="submit">Искать</button>
    </form>
    <br>
    {% if results %}
        <h3>Результаты поиска:</h3>
        {% for gost, text in results.items() %}
            <div class="result">
                <b>{{ gost }}</b><br>{{ text }}
            </div>
        {% endfor %}
    {% elif ai_result %}
        <div class="result">
            <b>🤖 Ответ AI:</b><br>{{ ai_result }}
        </div>
    {% elif query %}
        <p>Ничего не найдено...</p>
    {% endif %}
    <br>
    <a href="{{ url_for('add_gost') }}">➕ Добавить ГОСТ</a> |
    <a href="{{ url_for('list_gosts') }}">📜 Список ГОСТов</a>
</body>
</html>
"""

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
    results, ai_result = {}, None

    if search_query:
        for gost, text in data.items():
            text_combined = " ".join(text) if isinstance(text, list) else str(text)
            if search_query in gost.lower() or search_query in text_combined.lower():
                results[gost] = text_combined

        if not results:
            ai_result = ask_openrouter(search_query)

    return render_template_string(TEMPLATE_INDEX, results=results, query=search_query, ai_result=ai_result)


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


@app.route("/list")
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
