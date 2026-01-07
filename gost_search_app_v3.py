from flask import Flask, render_template_string, request, jsonify
import json, os

app = Flask(__name__)

DATA_FILE = "gost_data.json"
TNVED_FILE = "tnved_data.json"
REGULATION_FILE = "regulation.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_tnved():
    if os.path.exists(TNVED_FILE):
        with open(TNVED_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def load_regulation():
    if os.path.exists(REGULATION_FILE):
        with open(REGULATION_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

TEMPLATE_INDEX = """<html>
<head>
<meta charset='utf-8'>
<title>ГОСТ База</title>
<link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">
<style>
body { font-family: "Segoe UI", sans-serif; margin: 0; color: #fff; background: #000; overflow-y: auto; }
video#bgVideo { position: fixed; top: 0; left: 0; min-width: 100%; min-height: 100%; object-fit: cover; z-index: -2; }
.overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); z-index: -1; }
h1, h2 { font-weight: 300; }
h1 { margin-top: 0; }
input[type=text], input[type=number] { padding: 10px; width: 70%; border: none; border-radius: 4px; outline: none; font-size: 16px; }
button { padding: 10px 18px; border: none; background: #007bff; color: #fff; border-radius: 4px; cursor: pointer; font-size: 16px; }
button:hover { background: #0056b3; }
a { text-decoration: none; color: #fff; margin: 0 10px; }
a:hover { text-decoration: underline; }
div.result { background: rgba(255,255,255,0.1); padding: 10px; margin-top: 10px; border-radius: 6px; text-align: left; }
.mark { color: #00ffcc; font-size: 14px; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { padding: 8px; border-bottom: 1px solid #555; text-align: left; }

.highlight {
  background: rgba(255, 255, 0, 0.35);
  color: #fff;
  padding: 0 3px;
  border-radius: 3px;
}

#lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.85);
  display: none;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  cursor: zoom-out;
}

#lightbox img {
  max-width: 90%;
  max-height: 90%;
  object-fit: contain;
  border-radius: 12px;
}

#content-column {
  min-width: 0;          /* 🔥 КРИТИЧЕСКИ ВАЖНО */
  overflow-wrap: break-word;
}
#image-panel {
  width: 420px;
  flex-shrink: 0;
}

/* основной layout */
.container {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 60px auto;
  padding: 30px;

  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 20px;

  border-radius: 12px;
  box-shadow: 0 0 20px rgba(0,0,0,0.4);
  backdrop-filter: blur(8px);
}

/* правая панель */
#image-panel {
  position: sticky;
  top: 20px;
  height: fit-content;
  background: rgba(0,0,0,0.35);
  border-radius: 16px;
  padding: 15px;
}

#image-panel img {
  width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 12px;
  background: #111;
}

/* ---------- SPA АНИМАЦИИ ---------- */
#app {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

#app.fade-out {
  opacity: 0;
  transform: translateY(10px);
}

#app.fade-in {
  opacity: 1;
  transform: translateY(0);
}
#app {
  position: relative;
  transition: opacity 0.25s ease;
}

#app.glitch {
  animation: glitchFade 0.35s linear;
}

@keyframes glitchFade {
  0% {
    opacity: 1;
    filter: none;
    transform: translate(0);
  }
  20% {
    opacity: 0.6;
    filter: hue-rotate(20deg) contrast(1.4);
    transform: translate(-2px, 2px);
  }
  40% {
    opacity: 0.4;
    filter: hue-rotate(-20deg) contrast(1.6);
    transform: translate(2px, -2px);
  }
  60% {
    opacity: 0.6;
    filter: hue-rotate(10deg) contrast(1.3);
    transform: translate(-1px, 1px);
  }
  100% {
    opacity: 1;
    filter: none;
    transform: translate(0);
  }
}   /* 👈 ВОТ ЭТОЙ СКОБКИ НЕ ХВАТАЛО */

.gost-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}
/* ---------- СКРЫТИЕ ПРАВОЙ ПАНЕЛИ ---------- */
.hide-image #image-panel {
  display: none;
}

.hide-image.container {
  grid-template-columns: 1fr;
}
</style>
</head>
<body>

<video autoplay muted loop id="bgVideo">
  <source id="bgSource" src="/static/background.mp4" type="video/mp4">
</video>
<div class="overlay"></div>
<div class="container">

  <!-- 🔹 ЛЕВАЯ КОЛОНКА -->
  <div id="content-column">

    <div style="margin-bottom:20px;">
      <!-- 🔹 SPA навигация -->
      <a href="/" data-link style="font-size:18px;">🔍 Поиск ГОСТ</a>
      <a href="/list" data-link style="font-size:18px;">📋 Список ГОСТов</a>
      <a href="/add" data-link style="font-size:18px;">➕ Добавить ГОСТ</a>

      <br><br>

      <!-- 🎨 Управление фоном -->
      <button onclick="setBackground('video1')">🎥 Фон 1</button>
      <button onclick="setBackground('video2')">🎥 Фон 2</button>
      <button onclick="setBackground('image')">🖼 Картинка</button>
      <button onclick="setBackground('gradient')">🎨 Градиент</button>
    </div>
    <button id="toggle-image-btn"
        onclick="toggleImagePanel()"
        style="margin-bottom:15px;">
  👁 Скрыть изображение
</button>

    <!-- 👇 SPA-контент -->
    <div id="app"></div>

  </div>

  <!-- 🔹 ПРАВАЯ КОЛОНКА -->
  <div id="image-panel">
    <img id="preview-image" src="/static/images/no-image.png">
  </div>

</div>

<script>
const spaCache = {};

document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeLightbox();
});
function highlightText(text, query) {
    if (typeof text !== "string" || !query) return text || "";

    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${escaped})`, "gi");

    return text.replace(regex, '<span class="highlight">$1</span>');
}

function showImage(src) {
    const img = document.getElementById("preview-image");

    if (!src) {
        img.src = "/static/images/no-image.png";
        return;
    }

    img.src = src;
img.onclick = () => openLightbox(src);
}

function uploadImage(gost) {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";

    input.onchange = () => {
        const file = input.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("gost", gost);
        formData.append("image", file);

        fetch("/api/upload-gost-image", {
            method: "POST",
            body: formData
        })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
            showImage(res.image);
                delete spaCache["list"];   // ♻️ обновить список
                loadList();
            } else {
                alert(res.error || "Ошибка загрузки");
            }
        });
    };

    input.click();
}

   
/* ---------- GLITCH CONTENT ---------- */
function setAppContent(html) {
  const app = document.getElementById("app");

  app.classList.remove("glitch");
  void app.offsetWidth;   // принудительный reflow
  app.classList.add("glitch");

  setTimeout(() => {
    app.innerHTML = html;   // ✅ правильно
  }, 150);
}

function toggleImagePanel() {
    const container = document.querySelector(".container");
    const btn = document.getElementById("toggle-image-btn");

    container.classList.toggle("hide-image");

    const hidden = container.classList.contains("hide-image");
    btn.innerText = hidden
        ? "👁 Показать изображение"
        : "👁 Скрыть изображение";

    // 💾 сохраняем состояние
    localStorage.setItem(
        "hide-image-panel",
        hidden ? "1" : "0"
    );
}

/* ---------- BACKGROUND SWITCH ---------- */
function setBackground(type) {
  const video = document.getElementById("bgVideo");
  const source = document.getElementById("bgSource");

  // сбрасываем всё
  video.style.display = "none";
  document.body.style.background = "#000";

  if (type === "video1") {
    video.style.display = "block";
    source.src = "/static/background.mp4";
    video.load();
    video.play();
  }

  if (type === "video2") {
    video.style.display = "block";
    source.src = "/static/background2.mp4";
    video.load();
    video.play();
  }

  if (type === "image") {
    document.body.style.background =
      "url('/static/bg.jpg') center / cover no-repeat fixed";
  }

  if (type === "gradient") {
    document.body.style.background =
      "linear-gradient(135deg, #1f0036, #3b0a45, #000)";
  }

  // 💾 сохраняем выбор
  localStorage.setItem("site-bg", type);
}

/* ---------- SPA: КЕШ СТРАНИЦ ---------- */
function loadPageCached(url, cacheKey) {
    const app = document.getElementById("app");

    if (spaCache[cacheKey]) {
        setAppContent(spaCache[cacheKey]);
        return;
    }

    fetch(url)
      .then(r => r.text())
      .then(html => {
          spaCache[cacheKey] = html;
          setAppContent(html);
      })
      .catch(() => {
          setAppContent("<p>⚠ Ошибка загрузки</p>");
      });
}

/* ---------- SPA: РЕДАКТИРОВАНИЕ ---------- */
function editGost(gost) {
    fetch("/api/get-gost/" + encodeURIComponent(gost))
      .then(r => r.json())
      .then(data => {
        setAppContent(`
          <h2>✏️ Редактировать ${gost}</h2>
          <input id="edit-mark" value="${data.mark || ""}" placeholder="Маркировка"><br><br>
          <textarea id="edit-text" rows="5" style="width:100%;">${data.text || ""}</textarea><br><br>
          <button onclick="saveGostEdit('${gost}')">💾 Сохранить</button>
          <button onclick="loadList()">⬅ Назад</button>
        `);
      });
}

function openLightbox(src) {
    if (!src) return;

    const lb = document.getElementById("lightbox");
    const img = document.getElementById("lightbox-img");

    img.src = src;
    lb.style.display = "flex";
}

function closeLightbox() {
    document.getElementById("lightbox").style.display = "none";
}

/* ---------- SPA: УДАЛЕНИЕ ---------- */
function deleteGost(gost) {
  if (!confirm("Удалить ГОСТ " + gost + "?")) return;

  fetch("/api/delete-gost/" + encodeURIComponent(gost))
    .then(() => {
    delete spaCache["list"]; // 🔥 сброс кеша
    loadList();
});
}

// Функция загрузки главной страницы (Поиск ГОСТ)
function loadAdd() {
    setAppContent(`
      <h1>➕ Добавить ГОСТ</h1>
      <form id="add-gost-form">
        <input type="text" name="gost_number" placeholder="Номер ГОСТа" required style="width: 65%;"><br><br>
        <input type="text" name="gost_mark" placeholder="Маркировка ГОСТа"><br><br>
        <input type="text" name="gost_text" placeholder="Описание/текст ГОСТа" required><br><br>
        <button type="submit">Добавить</button>
      </form>
      <div id="add-result" style="margin-top:15px;"></div>
    `);

    setTimeout(() => {
        document.getElementById("add-gost-form")
          ?.addEventListener("submit", function(e){
              e.preventDefault();

              const form = e.target;
              const number = form.gost_number.value.trim();
              const mark = form.gost_mark.value.trim();
              const text = form.gost_text.value.trim();

              fetch("/api/add-gost", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                      gost_number: number,
                      gost_mark: mark,
                      gost_text: text
                  })
              })
              .then(r => r.json())
              .then(res => {
                  if (res.success) {
                      delete spaCache["list"];
                      window.history.pushState(null, "", "/list");
                      loadRoute();
                  } else {
                      document.getElementById("add-result").innerHTML =
                        "<p>❌ " + (res.error || "Ошибка") + "</p>";
                  }
              })
              .catch(() => {
                  document.getElementById("add-result").innerHTML =
                    "<p>⚠ Ошибка запроса</p>";
              });
          });
    }, 170);
}
// Функция загрузки списка ГОСТов
function loadHome() {
    setAppContent(`
      <h1>🔍 Поиск ГОСТ</h1>

      <input type="text" id="gost-input"
  placeholder="Введите номер или маркировку ГОСТа..."
  style="width:70%;">

<button onclick="searchGost()">Искать</button>
      <div id="gost-search-results"></div>

      <hr style="margin:25px 0;opacity:0.3;">

      <h2>🔎 Поиск КОД ТН ВЭД</h2>
      <input type="text" id="tnved-input" placeholder="Код или наименование" style="width:70%;">
      <button id="tnved-search-btn" style="background:#17a2b8;">ТН ВЭД</button>
      <div id="tnved-results"></div>

      <hr style="margin:25px 0;opacity:0.3;">

      <h2>⚖ Проверка по техрегламенту</h2>
      <input type="text" id="reg-product" placeholder="Код ТН ВЭД" style="width:70%;"><br><br>
      <input type="number" id="reg-voltage" placeholder="Напряжение (В)">
      <button id="reg-search-btn" style="background:#6f42c1;">Проверить</button>
      <div id="reg-result" style="margin-top:15px;"></div>
    `);


        document.getElementById("tnved-search-btn")
          ?.addEventListener("click", searchTNVED);

        document.getElementById("reg-search-btn")
          ?.addEventListener("click", checkRegulation);
    }, 170);
}
function loadList() {
    loadPageCached("/api/list-gosts", "list");
}

// Функция поиска ГОСТ
function searchGost() {
    const q = document.getElementById("gost-input").value.trim();
    const box = document.getElementById("gost-search-results");
    box.innerHTML = "";
    if (!q) return;
    fetch("/api/search?q=" + encodeURIComponent(q))
      .then(r => r.json())
      .then(data => {
          if (!data || Object.keys(data).length === 0) {
              box.innerHTML = "<p>❌ Ничего не найдено</p>";
              return;
          }
          let html = "<h2>Результаты:</h2>";
          for (const gost in data) {
              const info = data[gost];
              const text = info.text || "";
              const mark = info.mark || "";
              html += `<div class="result">
  <b>${highlightText(gost, q)}</b>
  <span class="mark">(${highlightText(mark, q)})</span><br>
  ${highlightText(text, q)}
</div>`;
          }
          box.innerHTML = html;
      })
      .catch(() => {
          box.innerHTML = "<p>⚠ Ошибка запроса</p>";
      });
}

// Функция поиска по ТН ВЭД
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
            let html = "";
            for (const code in data) {
                const item = data[code];
                html += `<div class="result"><b>КОД ТН ВЭД:</b> ${code}<br><b>Наименование:</b> ${item.name || ""}`;
                if (item.standards && item.standards.length) {
                    html += "<br><b>Стандарты:</b><ul>";
                    item.standards.forEach(s => html += `<li>${s}</li>`);
                    html += "</ul>";
                }
                html += "</div>";
            }
            box.innerHTML = html;
        })
        .catch(() => {
            box.innerHTML = "<p>⚠ Ошибка запроса</p>";
        });
}

// Функция проверки по техрегламенту
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
                <b style="color:#90ee90;">✅ Подпадает под техрегламент</b><br>
                Регламент: ${data.regulation || ""}<br>
                Формы: ${data.forms || ""}
              </div>
            `;
        })
        .catch(() => {
            box.innerHTML = "<p>⚠ Ошибка проверки</p>";
        });
}

// Функция маршрутизации SPA
function loadRoute() {
    const path = window.location.pathname;
    if (path === "/" || path === "") {
        loadHome();
    } else if (path === "/list") {
        loadList();
    } else if (path === "/add") {
        loadAdd();
    } else {
        loadHome();
    }
}

document.addEventListener('DOMContentLoaded', function() {

    // 🔁 восстановление скрытой панели
    const hidden = localStorage.getItem("hide-image-panel") === "1";
    const container = document.querySelector(".container");
    const btn = document.getElementById("toggle-image-btn");

    if (hidden && container && btn) {
        container.classList.add("hide-image");
        btn.innerText = "👁 Показать изображение";
    }

    document.querySelectorAll('a[data-link]').forEach(a => {
        a.addEventListener('click', function(e) {
            e.preventDefault();
            window.history.pushState(null, "", this.getAttribute('href'));
            loadRoute();
        });
    });

    loadRoute();
});

</script>
<div id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img">
</div>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(TEMPLATE_INDEX)

from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/upload-gost-image", methods=["POST"])
def upload_gost_image():
    gost = request.form.get("gost")
    file = request.files.get("image")

    if not gost or not file:
        return {"success": False, "error": "Нет данных"}

    if not allowed_file(file.filename):
        return {"success": False, "error": "Недопустимый формат"}

    filename = secure_filename(f"{gost}.jpg")
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    data = load_data()
    if gost not in data:
        return {"success": False, "error": "ГОСТ не найден"}

    data[gost]["image"] = "/" + path.replace("\\", "/")
    save_data(data)

    return {"success": True, "image": data[gost]["image"]}

@app.route("/api/list-gosts")
def api_list_gosts():
    data = load_data()
    html = "<h2>📋 Список ГОСТов</h2>"

    for gost, info in data.items():
        text = info.get("text", "")
        mark = info.get("mark", "")
        image = info.get("image", "/static/images/no-image.png")

        html += f"""
<div class="result">
  <b>{gost}</b> <span class="mark">({mark})</span><br>
  {text}<br><br>

  <button onclick="showImage('{image}')">👁 Показать</button>
  <button onclick="uploadImage('{gost}')">🖼 Изображение</button>
  <button onclick="editGost('{gost}')">✏️ Редактировать</button>
  <button onclick="deleteGost('{gost}')" style="background:#dc3545;">
    🗑 Удалить
  </button>
</div>
        """

    return html

@app.route("/api/get-gost/<gost>")
def api_get_gost(gost):
    data = load_data()
    return data.get(gost, {})

@app.route("/api/update-gost", methods=["POST"])
def api_update_gost():
    data = load_data()
    j = request.json
    gost = j.get("number")

    if gost not in data:
        return {"ok": False}

    data[gost] = {
        "mark": j.get("mark", ""),
        "text": j.get("text", "")
    }

    save_data(data)
    return {"ok": True}

@app.route("/api/delete-gost/<gost>")
def api_delete_gost(gost):
    data = load_data()
    if gost in data:
        del data[gost]
        save_data(data)
    return {"ok": True}

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip().lower()
    data = load_data()
    results = {}
    if q:
        for gost, info in data.items():
            if isinstance(info, dict):
                text = info.get("text", "")
                mark = info.get("mark", "")
            else:
                text = str(info)
                mark = ""
            combined = f"{gost} {mark} {text}".lower()
            if q in combined:
                results[gost] = {"text": text, "mark": mark}
    return jsonify(results)

@app.route("/api/add-gost", methods=["POST"])
def api_add_gost():
    data_json = request.get_json()
    if not data_json:
        return jsonify({"success": False, "error": "Нет данных"}), 400
    gost_number = data_json.get("gost_number", "").strip()
    gost_mark = data_json.get("gost_mark", "").strip()
    gost_text = data_json.get("gost_text", "").strip()
    if gost_number:
        data = load_data()
        data[gost_number] = {"text": gost_text, "mark": gost_mark}
        save_data(data)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Неверный номер ГОСТ"}), 400

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
    return jsonify(results)

@app.route("/api/regulation-check")
def api_regulation_check():
    query = request.args.get("q", "").strip()
    voltage = request.args.get("v", "").strip()
    reg = load_regulation()

    result = {"applies": False, "reason": ""}

    if not query.isdigit() or len(query) < 6:
        result["reason"] = "Введите корректный код ТН ВЭД"
        return jsonify(result)

    if query not in reg.get("tnved_codes", []):
        result["reason"] = "Код ТН ВЭД не входит в область действия регламента"
        return jsonify(result)

    if voltage.isdigit():
        v = int(voltage)
        ac_min = reg["voltage_limits"]["ac_min_v"]
        ac_max = reg["voltage_limits"]["ac_max_v"]
        if v < ac_min or v > ac_max:
            result["reason"] = "Напряжение вне диапазона регламента"
            return jsonify(result)

    result["applies"] = True
    result["reason"] = "Подпадает под технический регламент"
    result["regulation"] = reg.get("name", "")
    result["forms"] = reg.get("conformity_forms", "")
    return jsonify(result)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)































