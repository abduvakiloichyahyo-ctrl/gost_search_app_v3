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

# ---------- Минималистичные HTML шаблоны ----------
TEMPLATE_INDEX = """<html>...</html>"""  # Используй тот же шаблон, что был до этого
TEMPLATE_ADD = """<html>...</html>"""
TEMPLATE_LIST = """<html>...</html>"""
TEMPLATE_EDIT = """<html>...</html>"""

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
