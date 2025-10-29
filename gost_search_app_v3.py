from flask import Flask, render_template_string, request, redirect, url_for
import json, os, requests, openai

app = Flask(__name__)

# --- Настройки файлов ---
DATA_FILE = "gost_data.json"

# --- Настройка GitHub ---
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# --- Настройка OpenAI API ---
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- Проверяем, есть ли база ГОСТов ---
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

# -------------------------------
# 🔹 Главная страница
# -------------------------------
TEMPLATE_INDEX = """<html>
<head>
<meta charset='utf-8'>
<title>ГОСТ Менеджер</title>
<style>
body {
  font-family: "Segoe UI", sans-serif;
  color: #fff;
  text-align: center;
  background: #000;
  overflow: hidden;
}
video#bgVideo {
  position: fixed;
  top: 0; left: 0;
  min-width: 100%; min-height: 100%;
  object-fit: cover;
  z-index: -1;
  filter: brightness(0.4);
}
h1 { margin-top: 15%; font-size: 36px; }
a {
  display: inline-block;
  margin: 10px;
  padding: 12px 20px;
  background: rgba(255,255,255,0.1);
  color: #fff;
  text-decoration: none;
  border-radius: 8px;
  transition: 0.3s;
}
a:hover { background: rgba(255,255,255,0.25); }
</style>
</head>
<body>
<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>

<h1>ГОСТ Менеджер ⚙️</h1>
<a href="{{ url_for('list_gosts') }}">📋 Список ГОСТов</a>
<a href="{{ url_for('add_gost') }}">➕ Добавить ГОСТ</a>
<a href="{{ url_for('ai_search') }}">🤖 AI Поиск ГОСТов</a>
</body>
</html>
"""

# -------------------------------
# 🔹 Список ГОСТов
# -------------------------------
TEMPLATE_LIST = """<html>
<head>
<meta charset='utf-8'>
<title>Список ГОСТов</title>
<style>
body {
  font-family: "Segoe UI", sans-serif;
  color: #fff;
  margin: 0;
  background: #000;
  overflow-y: auto;
}
video#bgVideo {
  position: fixed;
  top: 0; left: 0;
  min-width: 100%; min-height: 100%;
  object-fit: cover;
  z-index: -1;
  filter: brightness(0.4);
}
.container {
  width: 800px;
  margin: 40px auto;
  background: rgba(0,0,0,0.6);
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(0,0,0,0.4);
  margin-bottom: 80px;
}
table {
  width: 100%;
  border-collapse: collapse;
}
td, th {
  padding: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.2);
}
a { color: #fff; text-decoration: none; }
a:hover { text-decoration: underline; }
button {
  padding: 5px 10px;
  border: none;
  border-radius: 5px;
  background: #ff4d4d;
  color: white;
  cursor: pointer;
}
button:hover { background: #d93636; }
</style>
</head>
<body>
<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>

<div class="container">
<h1>📋 Список ГОСТов</h1>
<table>
<tr><th>Номер</th><th>Название</th><th>Действие</th></tr>
{% for g in data %}
<tr>
  <td>{{ g["number"] }}</td>
  <td>{{ g["name"] }}</td>
  <td><a href="{{ url_for('delete_gost', number=g['number']) }}"><button>🗑 Удалить</button></a></td>
</tr>
{% endfor %}
</table>

<p><a href='{{ url_for("index") }}'>⬅ Назад</a></p>
</div>
</body>
</html>"""

# -------------------------------
# 🔹 Добавление ГОСТа
# -------------------------------
TEMPLATE_ADD = """<html>
<head>
<meta charset='utf-8'>
<title>Добавить ГОСТ</title>
<style>
body {
  font-family: "Segoe UI", sans-serif;
  color: #fff;
  background: #000;
  text-align: center;
}
input[type=text] {
  padding: 10px;
  width: 300px;
  border: none;
  border-radius: 5px;
  margin: 5px;
}
button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  background: #007bff;
  color: white;
  cursor: pointer;
}
button:hover { background: #0056b3; }
a { color: #fff; text-decoration: none; }
</style>
</head>
<body>
<h1>➕ Добавить ГОСТ</h1>
<form method="post">
  <input type="text" name="number" placeholder="Номер ГОСТа" required><br>
  <input type="text" name="name" placeholder="Название ГОСТа" required><br>
  <button type="submit">Добавить</button>
</form>
<p><a href='{{ url_for("index") }}'>⬅ Назад</a></p>
</body>
</html>"""

# -------------------------------
# 🔹 AI поиск ГОСТов
# -------------------------------
TEMPLATE_AI_SEARCH = """<html>
<head>
<meta charset='utf-8'>
<title>AI Поиск ГОСТов</title>
<style>
body {
  font-family: "Segoe UI", sans-serif;
  color: #fff;
  background: #000;
  overflow-y: auto;
}
video#bgVideo {
  position: fixed;
  top: 0; left: 0;
  min-width: 100%; min-height: 100%;
  object-fit: cover;
  z-index: -1;
  filter: brightness(0.4);
}
.container {
  width: 600px;
  margin: 100px auto;
  background: rgba(255,255,255,0.08);
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 0 20px rgba(0,0,0,0.4);
  text-align: center;
  backdrop-filter: blur(8px);
}
input[type=text] {
  width: 80%;
  padding: 10px;
  border: none;
  border-radius: 4px;
  font-size: 16px;
}
button {
  padding: 10px 18px;
  border: none;
  border-radius: 4px;
  background: #007bff;
  color: white;
  cursor: pointer;
}
button:hover { background: #0056b3; }
.result {
  background: rgba(255,255,255,0.1);
  margin-top: 20px;
  padding: 15px;
  border-radius: 8px;
  text-align: left;
  white-space: pre-wrap;
}
a { color: #fff; text-decoration: none; }
</style>
</head>
<body>
<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>

<div class="container">
<h1>🤖 AI Поиск ГОСТов</h1>
<form method="post">
  <input type="text" name="product_name" placeholder="Например: Шланг пневматический" required>
  <button type="submit">Искать</button>
</form>

{% if result %}
<div class="result">
  <b>Рекомендованные ГОСТы:</b><br>
  {{ result }}
</div>
{% endif %}

<p><a href='{{ url_for("index") }}'>⬅ Назад</a></p>
</div>
</body>
</html>"""

# -------------------------------
# 🔹 Маршруты Flask
# -------------------------------
@app.route("/")
def index():
    return render_template_string(TEMPLATE_INDEX)

@app.route("/list")
def list_gosts():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return render_template_string(TEMPLATE_LIST, data=data)

@app.route("/add", methods=["GET", "POST"])
def add_gost():
    if request.method == "POST":
        number = request.form["number"]
        name = request.form["name"]
        with open(DATA_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data.append({"number": number, "name": name})
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
        return redirect(url_for("list_gosts"))
    return render_template_string(TEMPLATE_ADD)

@app.route("/delete/<number>")
def delete_gost(number):
    with open(DATA_FILE, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data = [d for d in data if d["number"] != number]
        f.seek(0)
        f.truncate()
        json.dump(data, f, ensure_ascii=False, indent=2)
    return redirect(url_for("list_gosts"))

@app.route("/ai_search", methods=["GET", "POST"])
def ai_search():
    result = ""
    if request.method == "POST":
        product_name = request.form["product_name"].strip()
        prompt = f"""
        Ты эксперт по сертификации продукции. 
        По названию изделия: "{product_name}" предложи 3–5 возможных ГОСТов, 
        по которым может проходить испытание или сертификация.
        Формат ответа:
        ГОСТ НОМЕР — краткое описание.
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            result = response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            result = f"⚠ Ошибка при запросе к OpenAI API: {e}"
    return render_template_string(TEMPLATE_AI_SEARCH, result=result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
