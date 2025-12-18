from flask import Flask, render_template_string, request, redirect, url_for
import json, os, base64, requests

app = Flask(__name__)

DATA_FILE = "gost_data.json"

# --- Настройки GitHub ---
GITHUB_USER = os.environ.get("GITHUB_USER")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_FILE_PATH = "gost_data.json"
# ---------- ТН ВЭД ----------
TNVED_FILE = "tnved_data.json"

REGULATION_FILE = "regulation.json"

def load_regulation():
    if os.path.exists(REGULATION_FILE):
        with open(REGULATION_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}
    
def load_tnved():
    if os.path.exists(TNVED_FILE):
        with open(TNVED_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

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
.mark { color: #00ffcc; font-size: 14px; }
</style>
</head>
<body>

<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>
<div class="overlay"></div>

<div class="container">
  <h1>🔍 Поиск ГОСТов</h1>
  <div style="margin-bottom:15px;">
  <input type="text" id="tnved-input" placeholder="Поиск КОД ТН ВЭД или продукции...">
  <button type="button" onclick="searchTNVED()" style="background:#17a2b8;">
    ТН ВЭД
  </button>
</div>

<div id="tnved-results"></div>

<hr style="margin:25px 0;opacity:0.3;">

<h2>⚖ Проверка по техрегламенту</h2>

<input type="text" id="reg-product" placeholder="Наименование товара">
<br><br>
<input type="number" id="reg-voltage" placeholder="Напряжение (В)">
<br><br>
<button onclick="checkRegulation()" style="background:#6f42c1;">
  Проверить
</button>

<div id="reg-result" style="margin-top:15px;"></div>
  

<!-- 🔍 Поиск ГОСТ -->
<form method="get">
  <input type='text' name='q' value='{{ query }}' placeholder='Введите номер или маркировку ГОСТа...'>
  <button type='submit'>Искать</button>
</form>
  <p>
    <a href='{{ url_for("add_gost") }}'>➕ Добавить ГОСТ</a> |
    <a href='{{ url_for("list_gosts") }}'>📋 Список ГОСТов</a>
  </p>
  {% if results %}
  <h2>Результаты:</h2>
  {% for gost, info in results.items() %}
    <div class="result">
      <b>{{ gost }}</b> <span class="mark">({{ info.mark }})</span><br>{{ info.text }}
    </div>
  {% endfor %}
  {% elif query %}
  <p>Ничего не найдено.</p>
  {% endif %}
</div>
<script>
/* ---------- ТН ВЭД ---------- */
function searchTNVED() {
    const input = document.getElementById("tnved-input");
    const box = document.getElementById("tnved-results");
    const q = input.value.trim();

    box.innerHTML = "";
    if (!q) return;

    fetch("/api/tnved?q=" + encodeURIComponent(q))
        .then(r => r.json())
        .then(data => {
            if (!data || Object.keys(data).length === 0) {
                box.innerHTML = "<p>❌ Ничего не найдено</p>";
                return;
            }

            for (const code in data) {
                const item = data[code];
                let html = `
                  <div class="result">
                    <b>КОД ТН ВЭД:</b> ${code}<br>
                    <b>Наименование:</b> ${item.name || ""}
                `;

                if (item.standards && item.standards.length) {
                    html += "<br><b>Стандарты:</b><ul>";
                    item.standards.forEach(s => html += `<li>${s}</li>`);
                    html += "</ul>";
                }

                html += "</div>";
                box.innerHTML += html;
            }
        })
        .catch(() => {
            box.innerHTML = "<p>⚠ Ошибка запроса</p>";
        });
}

/* ---------- ТЕХРЕГЛАМЕНТ ---------- */
function checkRegulation() {
    const product = document.getElementById("reg-product").value.trim();
    const voltage = document.getElementById("reg-voltage").value.trim();
    const box = document.getElementById("reg-result");

    box.innerHTML = "";
    if (!product) {
        box.innerHTML = "<p>❌ Введите наименование товара</p>";
        return;
    }

    fetch(`/api/regulation-check?q=${encodeURIComponent(product)}&v=${encodeURIComponent(voltage)}`)
        .then(r => r.json())
        .then(data => {
            if (!data.applies) {
                box.innerHTML = `<p style="color:#ff6b6b;">❌ ${data.reason}</p>`;
                return;
            }

            box.innerHTML = `
              <div class="result">
                <b style="color:#90ee90;">✅ Подпадает под техрегламент</b>
              </div>
            `;
        })
        .catch(() => {
            box.innerHTML = "<p>⚠ Ошибка проверки</p>";
        });
}
</script>
</body>
</html>"""

TEMPLATE_ADD = """<html>
<head>
<meta charset='utf-8'>
<title>Добавить ГОСТ</title>
<link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
<style>
body { font-family: "Segoe UI", sans-serif; margin: 0; color: #fff; overflow-y: auto; background: #000; }
video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
.overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
.container { position: relative; z-index: 2; width: 500px; margin: 50px auto; background: rgba(255,255,255,0.08); padding: 30px; border-radius: 12px; box-shadow: 0 0 20px rgba(0,0,0,0.4); backdrop-filter: blur(8px); text-align: center; }
input, textarea { width: 100%; padding: 10px; border: none; border-radius: 4px; margin-bottom: 12px; font-size: 15px; }
button { padding: 10px 18px; border: none; background: #28a745; color: #fff; border-radius: 4px; cursor: pointer; font-size: 16px; }
button:hover { background: #218838; }
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
.mark { color: #00ffcc; }
div.result { background: rgba(255,255,255,0.1); padding: 10px; margin-top: 10px; border-radius: 6px; }
.btn-delete { background: #dc3545; color: #fff; padding: 6px 10px; border-radius: 4px; text-decoration: none; }
.btn-edit { background: #ffc107; color: #000; padding: 6px 10px; border-radius: 4px; text-decoration: none; }
.btn-delete:hover { background: #c82333; }
.btn-edit:hover { background: #e0a800; }
</style>
</head>
<body>
<video autoplay muted loop id="bgVideo">
  <source src="{{ url_for('static', filename='background.mp4') }}" type="video/mp4">
</video>
<div class="overlay"></div>
<div class="container">
  <h1>📋 Все ГОСТы</h1>
  {% for gost, info in data.items() %}
    <div class="result">
      <b>{{ gost }}</b> <span class="mark">({{ info.mark }})</span><br>{{ info.text }}<br>
      <a class="btn-edit" href="{{ url_for('edit_gost', gost=gost) }}">✏ Редактировать</a>
      <a class="btn-delete" href="{{ url_for('delete_gost', gost=gost) }}" onclick="return confirm('Удалить {{ gost }}?');">🗑 Удалить</a>
    </div>
  {% endfor %}
  <a class="btn-edit" href="{{ url_for('index') }}">⬅ Назад</a>
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
        for gost, info in data.items():
            # Поддержка старого и нового формата
            if isinstance(info, str):
                text = info
                mark = ""
            else:
                text = info.get("text", "")
                mark = info.get("mark", "")

            # Объединяем поля для поиска
            combined = f"{gost} {mark} {text}".lower()
            if search_query in combined:
                results[gost] = {"mark": mark, "text": text}

    # --- Генерация HTML для результатов ---
    html_results = ""
    for gost, info in results.items():
        html_results += f"""
        <div class='result'>
            <div style="font-size:18px; font-weight:600; color:#00bfff;">ГОСТ: {gost}</div>
            <div style="margin-top:6px;">
                <span style="color:#ffcc00; font-weight:500;">Маркировка:</span> {info.get('mark', '')}
            </div>
            <div style="margin-top:8px; background:rgba(255,255,255,0.08); padding:10px; border-radius:6px;">
                <span style="color:#90ee90; font-weight:500;">Пункты:</span><br>
                <div style="margin-top:5px; color:#e0e0e0; line-height:1.5;">
                    {info.get('text', '').replace('\n', '<br>')}
                </div>
            </div>
        </div>
        """

    return render_template_string(
        TEMPLATE_INDEX.replace(
            "{% for gost, text in results.items() %}",
            "{{ html_results|safe }}"
        ),
        results=results,
        html_results=html_results,
        query=search_query
    )

@app.route("/list")
def list_gosts():
    data = load_data()
    return render_template_string(TEMPLATE_LIST, data=data)


@app.route("/add", methods=["GET", "POST"])
def add_gost():
    if request.method == "POST":
        data = load_data()
        gost_number = request.form["gost_number"].strip()
        gost_mark = request.form["gost_mark"].strip()
        gost_text = request.form["gost_text"].strip()

        data[gost_number] = {"text": gost_text, "mark": gost_mark}
        save_data(data)
        return redirect(url_for("list_gosts"))
    return render_template_string(TEMPLATE_ADD)


@app.route("/edit/<gost>", methods=["GET", "POST"])
def edit_gost(gost):
    data = load_data()
    raw = data.get(gost, "")

    # Приводим старые записи (строки) к новому виду
    if isinstance(raw, str):
        info = {"text": raw, "mark": ""}
    else:
        info = {"text": raw.get("text", ""), "mark": raw.get("mark", "")}

    if request.method == "POST":
        # Собираем обновленные данные
        new_text = request.form.get("gost_text", "").strip()
        new_mark = request.form.get("gost_mark", "").strip()

        # Сохраняем в едином формате
        data[gost] = {"text": new_text, "mark": new_mark}
        save_data(data)

        return redirect(url_for("list_gosts"))

    # Форма редактирования
    return render_template_string("""
    <html>
    <head><meta charset='utf-8'><title>Редактировать {{ gost }}</title></head>
    <body style="background:#000;color:#fff;font-family:Segoe UI,sans-serif;padding:20px;">
      <h1>Редактировать {{ gost }}</h1>
      <form method="post">
          <label>Маркировка:</label><br>
          <input type="text" name="gost_mark" value="{{ info.mark }}" style="width:500px;padding:8px;"><br><br>
          <label>Пункты ГОСТа:</label><br>
          <textarea name="gost_text" rows="10" cols="70" style="padding:8px">{{ info.text }}</textarea><br><br>
          <button type="submit">💾 Сохранить</button>
      </form>
      <p><a href="{{ url_for('list_gosts') }}" style="color:#fff">⬅ Назад</a></p>
    </body>
    </html>
    """, gost=gost, info=info)


@app.route("/delete/<gost>")
def delete_gost(gost):
    data = load_data()
    if gost in data:
        del data[gost]
        save_data(data)
    return redirect(url_for("list_gosts"))

    if query:
        for code, info in data.items():
            name = info.get("name", "")
            combined = f"{code} {name}".lower()
            if query in combined:
                results[code] = info

    return results
    query = request.args.get("q", "").strip().lower()
    data = load_tnved()
    results = {}

    if query:
        for code, info in data.items():
            name = info.get("name", "")
            combined = f"{code} {name}".lower()
            if query in combined:
                results[code] = info

    return render_template_string("""
    <html>
    <head>
        <meta charset="utf-8">
        <title>🔎 Поиск ТН ВЭД</title>
    </head>
    <body style="background:#000;color:#fff;font-family:Segoe UI,sans-serif;padding:20px;">
        <h1>🔎 Результаты поиска ТН ВЭД</h1>

        {% if results %}
            {% for code, info in results.items() %}
                <div style="margin-bottom:15px;padding:12px;background:rgba(255,255,255,0.08);border-radius:8px;">
                    <div style="font-size:18px;color:#00bfff;"><b>КОД ТН ВЭД:</b> {{ code }}</div>
                    <div style="margin-top:6px;"><b>Наименование:</b> {{ info.name }}</div>

                    {% if info.gost %}
                        <div style="margin-top:6px;">
                            <b>ГОСТ:</b>
                            <ul>
                                {% for g in info.gost %}
                                    <li>{{ g }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    {% endif %}
                </div>
            {% endfor %}
        {% else %}
            <p>❌ Ничего не найдено</p>
        {% endif %}

        <a href="/" style="color:#fff">⬅ Назад</a>
    </body>
    </html>
    """, results=results)

# ---------- Запуск ----------
@app.route("/api/tnved")
def api_tnved():
    query = request.args.get("q", "").strip().lower()
    data = load_tnved()
    results = {}

    if query:
        for code, info in data.items():
            name = info.get("name", "")
            combined = f"{code} {name}".lower()
            if query in combined:
                results[code] = info

    return results
REGULATION_FILE = "regulation.json"

def load_regulation():
    if os.path.exists(REGULATION_FILE):
        with open(REGULATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.route("/api/regulation-check")
def regulation_check():
    query = request.args.get("q", "").strip()
    voltage = request.args.get("v", "").strip()

    reg = load_regulation()

    result = {
        "applies": False,
        "reason": ""
    }

    # 1. Проверка: введён ли код
    if not query.isdigit() or len(query) < 6:
        result["reason"] = "Введите корректный код ТН ВЭД"
        return result

    # 2. Проверка: есть ли код в регламенте
    if query not in reg.get("tnved_codes", []):
        result["reason"] = "Код ТН ВЭД не входит в область действия регламента"
        return result

    # 3. Проверка по напряжению (если ввели)
    if voltage.isdigit():
        v = int(voltage)
        ac_min = reg["voltage_limits"]["ac_min_v"]
        ac_max = reg["voltage_limits"]["ac_max_v"]

        if v < ac_min or v > ac_max:
            result["reason"] = "Напряжение вне диапазона регламента"
            return result

    # ✅ Если ВСЕ проверки прошли
    result["applies"] = True
    result["reason"] = "Подпадает под технический регламент"
    result["regulation"] = reg["name"]
    result["forms"] = reg["conformity_forms"]

    return result

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)











