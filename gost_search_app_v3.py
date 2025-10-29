from flask import Flask, render_template_string, request, redirect, url_for
import json, os, base64, requests

app = Flask(__name__)

DATA_FILE = "gost_data.json"

# --- Настройки GitHub ---
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_FILE_PATH = "gost_data.json"

# --- Настройки OpenRouter (AI) ---
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")  # ⚠️ Установи в Render переменную окружения OPENROUTER_KEY
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Работа с GitHub ---
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

# ---------- HTML шаблон главной страницы ----------
TEMPLATE_INDEX = """
<html>
<head>
    <meta charset='utf-8'>
    <title>ГОСТ База — Поиск ГОСТов</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
    <style>
        body { font-family: "Segoe UI", sans-serif; margin: 0; height: 100vh; overflow: hidden; color: #fff; }
        video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
        .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
        .container { position: relative; z-index: 2; width: 600px; margin: auto; text-align: center; top: 50%; transform: translateY(-50%); background: rgba(255,255,255,0.08); padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.4); backdrop-filter: blur(8px); }
        h1 { font-weight: 300; margin-bottom: 20px; }
        input[type=text] { padding: 10px; width: 60%; border: none; border-radius: 4px; outline: none; font-size: 16px; }
        button { padding: 10px 18px; border: none; background: #007bff; color: #fff; border-radius: 4px; cursor: pointer; font-size: 16px; margin: 3px; }
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
        <button formaction="/ai_search" formmethod="post">AI поиск 🤖</button>
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
</html>
"""

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

@app.route("/ai_search", methods=["POST"])
def ai_search():
    query = request.form.get("q", "").strip()
    if not query:
        return redirect(url_for("index"))

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Ты эксперт по сертификации и ГОСТам. Отвечай кратко и по делу."},
            {"role": "user", "content": f"Найди или объясни ГОСТ для: {query}"}
        ]
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        ai_text = data.get("choices", [{}])[0].get("message", {}).get("content", "Ошибка при обработке AI-ответа.")
    except Exception as e:
        ai_text = f"⚠ Ошибка при запросе к AI: {e}"

    return render_template_string(TEMPLATE_INDEX, results=None, ai_result=ai_text, query=query)

# --- Остальные маршруты (add/list/edit/delete) ---
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
