from flask import Flask, render_template_string, request, redirect, url_for
import json
import os
import base64
import requests
from openai import OpenAI

app = Flask(__name__)

# ---------- Настройки ----------
DATA_FILE = "gost_data.json"
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Инициализация OpenAI client (современный SDK)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------- Утилиты для работы с локальными данными ----------
def load_data():
    """Загружает JSON, если нет — возвращает структуру с полями gosts и ai_history."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {"gosts": {}, "ai_history": []}
    else:
        return {"gosts": {}, "ai_history": []}

def save_data(data):
    """Сохраняет локально и пытается запушить в GitHub (если настроен)."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Попытка отправить на GitHub (если переменные окружения заданы)
    if GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN:
        try:
            push_to_github(DATA_FILE)
        except Exception as e:
            print("⚠ Ошибка при push на GitHub:", e)

# ---------- GitHub sync ----------
def get_github_api_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def push_to_github(path_on_disk):
    """
    Загружает содержимое файла и создает/обновляет файл в репозитории:
    repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DATA_FILE}
    """
    if not (GITHUB_USER and GITHUB_REPO and GITHUB_TOKEN):
        raise RuntimeError("GitHub credentials not set")

    with open(path_on_disk, "rb") as f:
        content = f.read()
    encoded = base64.b64encode(content).decode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = get_github_api_headers()

    # Узнаем, есть ли файл — чтобы получить sha
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")
    else:
        sha = None

    payload = {
        "message": "Автообновление gost_data.json через сайт",
        "content": encoded
    }
    if sha:
        payload["sha"] = sha

    put = requests.put(url, headers=headers, json=payload)
    if put.status_code not in (200, 201):
        # Выкидываем ошибку, чтобы её можно было логировать
        raise RuntimeError(f"GitHub API error {put.status_code}: {put.text}")

# ---------- HTML шаблоны (минимальные и аккуратные) ----------
TEMPLATE_INDEX = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>ГОСТ Менеджер</title>
  <style>
    body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;text-align:center;padding:40px;}
    a{display:inline-block;margin:8px;padding:10px 16px;background:#1f6feb;border-radius:8px;color:#fff;text-decoration:none;}
    a.secondary{background:#2d2f33}
  </style>
</head>
<body>
  <h1>ГОСТ Менеджер</h1>
  <p>
    <a href="{{ url_for('list_gosts') }}">📋 Список ГОСТов</a>
    <a href="{{ url_for('add_gost') }}" class="secondary">➕ Добавить ГОСТ</a>
    <a href="{{ url_for('ai_search') }}">🤖 AI Поиск ГОСТов</a>
    <a href="{{ url_for('ai_history') }}" class="secondary">🕘 История AI запросов</a>
  </p>
  <p style="opacity:0.8">Хранилище: <b>{{ data_file }}</b></p>
</body>
</html>
"""

TEMPLATE_LIST = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Список ГОСТов</title>
  <style>
    body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:20px;}
    .wrap{max-width:900px;margin:20px auto;background:rgba(255,255,255,0.03);padding:16px;border-radius:10px;}
    table{width:100%;border-collapse:collapse;color:#fff;}
    th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,0.04);text-align:left;vertical-align:top;}
    a.btn{padding:6px 10px;background:#ff4d4d;color:#fff;border-radius:6px;text-decoration:none;}
    .top{margin-bottom:12px;}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <a href="{{ url_for('index') }}">⬅ Назад</a> | <a href="{{ url_for('add_gost') }}">➕ Добавить ГОСТ</a>
    </div>
    <h2>📋 Список ГОСТов ({{ gosts|length }})</h2>
    <table>
      <tr><th>Номер</th><th>Текст / Описание</th><th>Действия</th></tr>
      {% for num, text in gosts.items() %}
      <tr>
        <td><b>{{ num }}</b></td>
        <td style="white-space:pre-wrap;">{{ text }}</td>
        <td>
          <a href="{{ url_for('edit_gost', gost=num) }}">✏️</a>
          <a href="{{ url_for('delete_gost', gost=num) }}" class="btn" onclick="return confirm('Удалить {{ num }} ?')">🗑 Удалить</a>
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
</body>
</html>
"""

TEMPLATE_ADD = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Добавить ГОСТ</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}input,textarea{width:100%;padding:8px;margin:6px 0;border-radius:6px;border:1px solid #333}button{padding:10px 14px;border-radius:8px;background:#1f6feb;color:#fff;border:none}</style>
</head>
<body>
  <h2>➕ Добавить ГОСТ</h2>
  <form method="post">
    <input name="gost_number" placeholder="Номер ГОСТ (например: ГОСТ 12345-67)" required>
    <textarea name="gost_text" rows="6" placeholder="Текст / описание / пункты ГОСТа" required></textarea>
    <button type="submit">Сохранить</button>
  </form>
  <p><a href="{{ url_for('list_gosts') }}">⬅ Назад</a></p>
</body>
</html>
"""

TEMPLATE_EDIT = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Редактировать ГОСТ</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}textarea{width:100%;padding:8px;margin:6px 0;border-radius:6px;border:1px solid #333}button{padding:10px 14px;border-radius:8px;background:#1f6feb;color:#fff;border:none}</style>
</head>
<body>
  <h2>✏️ Редактировать {{ gost }}</h2>
  <form method="post">
    <textarea name="gost_text" rows="8" required>{{ text }}</textarea>
    <button type="submit">Сохранить</button>
  </form>
  <p><a href="{{ url_for('list_gosts') }}">⬅ Назад</a></p>
</body>
</html>
"""

TEMPLATE_AI_SEARCH = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>AI Поиск ГОСТов</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}input{width:80%;padding:8px;border-radius:6px;border:1px solid #333}button{padding:8px 12px;border-radius:6px;background:#1f6feb;color:#fff;border:none}.result{background:rgba(255,255,255,0.03);padding:12px;border-radius:8px;margin-top:16px;white-space:pre-wrap}</style>
</head>
<body>
  <h2>🤖 AI Поиск ГОСТов по названию продукции</h2>
  <form method="post">
    <input name="product_name" placeholder="Например: Шланг пневматический для компрессора" required>
    <button type="submit">Искать</button>
  </form>

  {% if result %}
    <div class="result">
      <b>Результат:</b>
      <div>{{ result }}</div>
      <form method="post" action="{{ url_for('ai_save_to_gosts') }}">
        <input type="hidden" name="product_name" value="{{ product_name }}">
        <input type="hidden" name="ai_text" value="{{ result|replace('\n','\\n') }}">
        <button type="submit" style="margin-top:10px">💾 Добавить найденные как отдельную запись ГОСТ (черновик)</button>
      </form>
    </div>
  {% endif %}

  <p><a href="{{ url_for('index') }}">⬅ Назад</a></p>
</body>
</html>
"""

TEMPLATE_AI_HISTORY = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>История AI запросов</title>
<style>body{font-family:Segoe UI,Arial;background:#0b0f14;color:#fff;padding:30px}.item{background:rgba(255,255,255,0.03);padding:12px;margin-bottom:10px;border-radius:8px;white-space:pre-wrap}</style>
</head>
<body>
  <h2>🕘 История AI запросов</h2>
  <p><a href="{{ url_for('index') }}">⬅ Назад</a></p>
  {% for it in history %}
    <div class="item"><b>Запрос:</b> {{ it['query'] }}<br><b>Ответ:</b><br>{{ it['answer'] }}</div>
  {% endfor %}
</body>
</html>
"""

# ---------- Flask маршруты ----------
@app.route("/")
def index():
    return render_template_string(TEMPLATE_INDEX, data_file=DATA_FILE)

@app.route("/list")
def list_gosts():
    data = load_data()
    gosts = data.get("gosts", {})
    return render_template_string(TEMPLATE_LIST, gosts=gosts)

@app.route("/add", methods=["GET", "POST"])
def add_gost():
    if request.method == "POST":
        gost_number = request.form["gost_number"].strip()
        gost_text = request.form["gost_text"].strip()
        data = load_data()
        gosts = data.setdefault("gosts", {})
        gosts[gost_number] = gost_text
        save_data(data)
        return redirect(url_for("list_gosts"))
    return render_template_string(TEMPLATE_ADD)

@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    data = load_data()
    gosts = data.setdefault("gosts", {})
    if request.method == "POST":
        gosts[gost] = request.form["gost_text"].strip()
        save_data(data)
        return redirect(url_for("list_gosts"))
    text = gosts.get(gost, "")
    return render_template_string(TEMPLATE_EDIT, gost=gost, text=text)

@app.route("/delete/<gost>")
def delete_gost(gost):
    data = load_data()
    gosts = data.setdefault("gosts", {})
    if gost in gosts:
        del gosts[gost]
        save_data(data)
    return redirect(url_for("list_gosts"))

# ---------- AI поиск ----------
@app.route("/ai_search", methods=["GET", "POST"])
def ai_search():
    result = None
    product_name = ""
    if request.method == "POST":
        product_name = request.form["product_name"].strip()
        # Подготовим промпт
        prompt = f"""Ты — эксперт по сертификации и ГОСТ стандартам.
По названию изделия: "{product_name}" предложи 3-6 наиболее вероятных ГОСТов (по номеру и краткому описанию), по которым может проходить оценка соответствия или испытания.
Формат:
ГОСТ XXXX — краткое описание.
Если точных ГОСТов нет, дай рекомендации какие разделы/испытания следует учитывать."""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Ты эксперт по сертификации и ГОСТ стандартам."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.25,
                max_tokens=500
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            answer = f"⚠ Ошибка при запросе к OpenAI API: {e}"

        # Сохраняем историю AI
        data = load_data()
        history = data.setdefault("ai_history", [])
        history.insert(0, {"query": product_name, "answer": answer})
        # Ограничим историю, например, 100 записей
        data["ai_history"] = history[:100]
        save_data(data)

        result = answer

    return render_template_string(TEMPLATE_AI_SEARCH, result=result, product_name=product_name)

# Маршрут для сохранения AI-ответа как черновика ГОСТа
@app.route("/ai_save_to_gosts", methods=["POST"])
def ai_save_to_gosts():
    product_name = request.form.get("product_name", "AI-результат").strip()
    ai_text = request.form.get("ai_text", "").strip()
    data = load_data()
    gosts = data.setdefault("gosts", {})
    # формируем ключ, уникальный: AI: название + индекс если нужно
    base_key = f"AI: {product_name}"
    key = base_key
    i = 1
    while key in gosts:
        i += 1
        key = f"{base_key} ({i})"
    gosts[key] = ai_text
    save_data(data)
    return redirect(url_for("list_gosts"))

@app.route("/ai_history")
def ai_history():
    data = load_data()
    history = data.get("ai_history", [])
    return render_template_string(TEMPLATE_AI_HISTORY, history=history)

# ---------- Запуск ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
