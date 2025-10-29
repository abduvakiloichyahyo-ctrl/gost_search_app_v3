from flask import Flask, render_template_string, request, redirect, url_for
import json, os, base64, requests

app = Flask(__name__)

# ---------- Настройки ----------
DATA_FILE = "gost_data.json"
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# ---------- Утилиты ----------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"gosts": {}, "ai_history": []}
    return {"gosts": {}, "ai_history": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN:
        try:
            push_to_github(DATA_FILE)
        except Exception as e:
            print("⚠ Ошибка push в GitHub:", e)

def get_github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def push_to_github(path):
    with open(path, "rb") as f:
        content = f.read()
    encoded = base64.b64encode(content).decode("utf-8")
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = get_github_headers()
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    payload = {"message": "Auto-update gost_data.json", "content": encoded}
    if sha:
        payload["sha"] = sha
    put = requests.put(url, headers=headers, json=payload)
    if put.status_code not in (200, 201):
        raise RuntimeError(f"GitHub API error {put.status_code}: {put.text}")

# ---------- AI (через OpenRouter) ----------
def ask_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        return "⚠ Ошибка: ключ OPENROUTER_API_KEY не найден в переменных окружения."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4-turbo",
        "messages": [
            {"role": "system", "content": "Ты эксперт по сертификации и ГОСТ стандартам."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        return f"⚠ Ошибка OpenRouter API: {response.text}"
    return response.json()["choices"][0]["message"]["content"].strip()

# ---------- HTML шаблоны ----------
TEMPLATE_INDEX = """<!doctype html>
<html><head><meta charset="utf-8"><title>ГОСТ Менеджер</title>
<style>
body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;text-align:center;padding:40px;}
a{display:inline-block;margin:8px;padding:10px 16px;background:#1f6feb;border-radius:8px;color:#fff;text-decoration:none;}
a.secondary{background:#2d2f33}
</style></head>
<body>
  <h1>ГОСТ Менеджер</h1>
  <p>
    <a href="{{ url_for('list_gosts') }}">📋 Список ГОСТов</a>
    <a href="{{ url_for('add_gost') }}" class="secondary">➕ Добавить ГОСТ</a>
    <a href="{{ url_for('ai_search') }}">🤖 AI Поиск ГОСТов</a>
    <a href="{{ url_for('ai_history') }}" class="secondary">🕘 История AI запросов</a>
  </p>
  <p style="opacity:0.8">Хранилище: <b>{{ data_file }}</b></p>
</body></html>
"""

TEMPLATE_LIST = """<!doctype html>
<html><head><meta charset="utf-8"><title>Список ГОСТов</title>
<style>
body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:20px;}
.wrap{max-width:900px;margin:20px auto;background:rgba(255,255,255,0.03);padding:16px;border-radius:10px;}
table{width:100%;border-collapse:collapse;color:#fff;}
th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,0.04);text-align:left;}
a.btn{padding:6px 10px;background:#ff4d4d;color:#fff;border-radius:6px;text-decoration:none;}
.top{margin-bottom:12px;}
</style></head>
<body><div class="wrap">
<div class="top"><a href="{{ url_for('index') }}">⬅ Назад</a> | <a href="{{ url_for('add_gost') }}">➕ Добавить ГОСТ</a></div>
<h2>📋 Список ГОСТов ({{ gosts|length }})</h2>
<table><tr><th>Номер</th><th>Описание</th><th>Действия</th></tr>
{% for num, text in gosts.items() %}
<tr><td><b>{{ num }}</b></td><td style="white-space:pre-wrap;">{{ text }}</td>
<td><a href="{{ url_for('edit_gost', gost=num) }}">✏️</a>
<a href="{{ url_for('delete_gost', gost=num) }}" class="btn" onclick="return confirm('Удалить {{ num }} ?')">🗑</a></td></tr>
{% endfor %}
</table></div></body></html>
"""

TEMPLATE_ADD = """<!doctype html>
<html><head><meta charset="utf-8"><title>Добавить ГОСТ</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}input,textarea{width:100%;padding:8px;margin:6px 0;border-radius:6px;border:1px solid #333}button{padding:10px 14px;border-radius:8px;background:#1f6feb;color:#fff;border:none}</style>
</head><body><h2>➕ Добавить ГОСТ</h2>
<form method="post">
  <input name="gost_number" placeholder="Номер ГОСТ" required>
  <textarea name="gost_text" rows="6" placeholder="Описание" required></textarea>
  <button type="submit">Сохранить</button>
</form>
<p><a href="{{ url_for('list_gosts') }}">⬅ Назад</a></p>
</body></html>
"""

TEMPLATE_EDIT = """<!doctype html>
<html><head><meta charset="utf-8"><title>Редактировать ГОСТ</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}textarea{width:100%;padding:8px;margin:6px 0;border-radius:6px;border:1px solid #333}button{padding:10px 14px;border-radius:8px;background:#1f6feb;color:#fff;border:none}</style>
</head><body><h2>✏️ Редактировать {{ gost }}</h2>
<form method="post">
  <textarea name="gost_text" rows="8" required>{{ text }}</textarea>
  <button type="submit">Сохранить</button>
</form>
<p><a href="{{ url_for('list_gosts') }}">⬅ Назад</a></p>
</body></html>
"""

TEMPLATE_AI_SEARCH = """<!doctype html>
<html><head><meta charset="utf-8"><title>AI Поиск ГОСТов</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}input{width:80%;padding:8px;border-radius:6px;border:1px solid #333}button{padding:8px 12px;border-radius:6px;background:#1f6feb;color:#fff;border:none}.result{background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;margin-top:16px;white-space:pre-wrap}</style>
</head><body>
<h2>🤖 AI Поиск ГОСТов</h2>
<form method="post"><input name="product_name" placeholder="Например: Шланг пневматический" required>
<button type="submit">Искать</button></form>
{% if result %}
<div class="result"><b>Результат:</b><div>{{ result }}</div>
<form method="post" action="{{ url_for('ai_save_to_gosts') }}">
<input type="hidden" name="product_name" value="{{ product_name }}">
<input type="hidden" name="ai_text" value="{{ result|replace('\\n','\\\\n') }}">
<button type="submit" style="margin-top:10px">💾 Сохранить как ГОСТ</button>
</form></div>
{% endif %}
<p><a href="{{ url_for('index') }}">⬅ Назад</a></p>
</body></html>
"""

TEMPLATE_AI_HISTORY = """<!doctype html>
<html><head><meta charset="utf-8"><title>История AI</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}.item{background:rgba(255,255,255,0.03);padding:12px;margin-bottom:10px;border-radius:8px;white-space:pre-wrap}</style>
</head><body><h2>🕘 История AI запросов</h2><a href="{{ url_for('index') }}">⬅ Назад</a>
{% for it in history %}<div class="item"><b>Запрос:</b> {{ it['query'] }}<br><b>Ответ:</b><br>{{ it['answer'] }}</div>{% endfor %}
</body></html>
"""

# ---------- Flask маршруты ----------
@app.route("/")
def index():
    return render_template_string(TEMPLATE_INDEX, data_file=DATA_FILE)

@app.route("/list")
def list_gosts():
    return render_template_string(TEMPLATE_LIST, gosts=load_data().get("gosts", {}))

@app.route("/add", methods=["GET", "POST"])
def add_gost():
    if request.method == "POST":
        data = load_data()
        data["gosts"][request.form["gost_number"].strip()] = request.form["gost_text"].strip()
        save_data(data)
        return redirect(url_for("list_gosts"))
    return render_template_string(TEMPLATE_ADD)

@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    data = load_data()
    if request.method == "POST":
        data["gosts"][gost] = request.form["gost_text"].strip()
        save_data(data)
        return redirect(url_for("list_gosts"))
    return render_template_string(TEMPLATE_EDIT, gost=gost, text=data["gosts"].get(gost, ""))

@app.route("/delete/<gost>")
def delete_gost(gost):
    data = load_data()
    if gost in data["gosts"]:
        del data["gosts"][gost]
        save_data(data)
    return redirect(url_for("list_gosts"))

@app.route("/ai_search", methods=["GET", "POST"])
def ai_search():
    result, product_name = None, ""
    if request.method == "POST":
        product_name = request.form["product_name"].strip()
        prompt = f"""Ты — эксперт по сертификации и ГОСТ.
Для продукта "{product_name}" подбери 3–6 ГОСТов и кратко объясни их смысл."""
        answer = ask_openrouter(prompt)
        data = load_data()
        data.setdefault("ai_history", []).insert(0, {"query": product_name, "answer": answer})
        data["ai_history"] = data["ai_history"][:100]
        save_data(data)
        result = answer
    return render_template_string(TEMPLATE_AI_SEARCH, result=result, product_name=product_name)

@app.route("/ai_save_to_gosts", methods=["POST"])
def ai_save_to_gosts():
    data = load_data()
    name = f"AI: {request.form['product_name']}"
    text = request.form["ai_text"]
    i, key = 1, name
    while key in data["gosts"]:
        i += 1
        key = f"{name} ({i})"
    data["gosts"][key] = text
    save_data(data)
    return redirect(url_for("list_gosts"))

@app.route("/ai_history")
def ai_history():
    return render_template_string(TEMPLATE_AI_HISTORY, history=load_data().get("ai_history", []))

# ---------- Запуск ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
