# AI Website Generator Backend - NovaForge (ENFORCED FULL-STACK + Dynamic Features)
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os
import pathlib
import requests
import sqlite3
import shutil

# ----------------- Load Environment -----------------
load_dotenv()

app = Flask(__name__)
CORS(app)

NETLIFY_BUILD_HOOK = os.getenv('NETLIFY_BUILD_HOOK')  # Netlify build hook URL
NETLIFY_SITE_URL = os.getenv('NETLIFY_SITE_URL')      # Your public site URL, e.g. https://my-app.netlify.app
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_DIR = pathlib.Path(__file__).resolve().parent
GENERATED_ROOT = BASE_DIR / "generated_projects"
GENERATED_ROOT.mkdir(exist_ok=True)
DEPLOY_TARGET = BASE_DIR / "deploy_target"
DEPLOY_TARGET.mkdir(exist_ok=True)

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# ----------------- HELPERS -----------------
def extract_between_tags(text, start, end):
    try:
        s = text.find(start)
        e = text.find(end)
        if s != -1 and e != -1:
            return text[s + len(start):e].strip()
    except:
        pass
    return None

def enforced_app_js():
    """Fallback JS if Gemini fails"""
    return """\
const API_URL = "http://localhost:5000/api/data";

document.addEventListener("DOMContentLoaded", () => {
    loadData();
    const form = document.getElementById("data-form");
    if (form) form.addEventListener("submit", submitData);
});

async function loadData() {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error();
        const data = await res.json();
        render(data);
    } catch {
        showError("Backend server is not running");
    }
}

async function submitData(e) {
    e.preventDefault();
    const input = document.getElementById("content");
    if (!input.value) return;
    try {
        await fetch(API_URL, {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({content: input.value})
        });
        input.value = "";
        loadData();
    } catch {
        showError("Cannot save. Backend down.");
    }
}

function render(data) {
    const list = document.getElementById("data-list");
    list.innerHTML = "";
    data.forEach(r => {
        const li = document.createElement("li");
        li.textContent = r[1];
        list.appendChild(li);
    });
}

function showError(msg) {
    document.getElementById("data-list").innerHTML =
        `<li style="color:red">${msg}</li>`;
}
"""

def generate_backend_code(project_name):
    db = f"{project_name.lower().replace(' ','_')}.db"
    return f"""\
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)
DB = '{db}'

def init():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS data (id INTEGER PRIMARY KEY, content TEXT)")
    c.commit()
    c.close()

init()

@app.route('/api/data', methods=['GET'])
def get_data():
    c = sqlite3.connect(DB)
    rows = c.execute("SELECT * FROM data").fetchall()
    c.close()
    return jsonify(rows)

@app.route('/api/data', methods=['POST'])
def add_data():
    content = request.json.get("content")
    c = sqlite3.connect(DB)
    c.execute("INSERT INTO data (content) VALUES (?)", (content,))
    c.commit()
    c.close()
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(debug=True)
"""

# ----------------- GENERATE PROJECT -----------------
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json
    name = data.get("projectName", "Website")
    desc = data.get("description", "")
    ptype = data.get("projectType", "custom")

    prompt = f"""
Generate ONLY valid HTML.

STRICT RULES:
- NO static/sample data
- HTML must have empty containers
- JS must fetch data from /api/data
- DO NOT use localStorage
- Use <style> and <script>

Project: {name}
Description: {desc}
"""

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        res = model.generate_content(prompt)
        html = res.text.replace("```html","").replace("```","").strip()
    except:
        html = "<html><body><ul id='data-list'></ul></body></html>"

    css = extract_between_tags(html, "<style>", "</style>") or ""
    js = extract_between_tags(html, "<script>", "</script>")

    if not js or len(js.strip()) < 10:
        js = enforced_app_js()

    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    pdir = GENERATED_ROOT / safe
    pdir.mkdir(exist_ok=True)

    backend_code = generate_backend_code(name)

    (pdir / "index.html").write_text(html, encoding="utf-8")
    (pdir / "style.css").write_text(css, encoding="utf-8")
    (pdir / "app.js").write_text(js, encoding="utf-8")
    (pdir / "backend.py").write_text(backend_code, encoding="utf-8")

    return jsonify(
        success=True,
        code={"html": html, "css": css, "js": js, "backend": backend_code}
    )

# ----------------- ADD FEATURE DYNAMICALLY -----------------
@app.route("/api/add-feature", methods=["POST"])
def add_feature():
    data = request.json
    project_name = data.get("projectName")
    feature_desc = data.get("featureDescription")

    safe = "".join(c for c in project_name if c.isalnum() or c in "-_")
    pdir = GENERATED_ROOT / safe

    if not pdir.exists():
        return jsonify(success=False, error="Project not found"), 404

    html = (pdir / "index.html").read_text(encoding="utf-8")
    css = (pdir / "style.css").read_text(encoding="utf-8")
    js = (pdir / "app.js").read_text(encoding="utf-8")
    backend = (pdir / "backend.py").read_text(encoding="utf-8")

    prompt = f"""
You are modifying an EXISTING project.

RULES:
- DO NOT remove any existing functionality
- ONLY ADD the requested feature
- Keep structure intact
- Return updated HTML, CSS, JS, Backend separately

FEATURE TO ADD:
{feature_desc}

CURRENT HTML:
{html}

CURRENT CSS:
{css}

CURRENT JS:
{js}

CURRENT BACKEND:
{backend}
"""

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        res = model.generate_content(prompt)
        text = res.text
    except:
        text = ""

    new_html = extract_between_tags(text, "HTML_START", "HTML_END") or html
    new_css = extract_between_tags(text, "CSS_START", "CSS_END") or css
    new_js = extract_between_tags(text, "JS_START", "JS_END") or js
    new_backend = extract_between_tags(text, "BACKEND_START", "BACKEND_END") or backend

    (pdir / "index.html").write_text(new_html, encoding="utf-8")
    (pdir / "style.css").write_text(new_css, encoding="utf-8")
    (pdir / "app.js").write_text(new_js, encoding="utf-8")
    (pdir / "backend.py").write_text(new_backend, encoding="utf-8")

    return jsonify(success=True, code={"html": new_html, "css": new_css, "js": new_js, "backend": new_backend})

# ----------------- STATIC SERVING -----------------
@app.route("/<project>/")
def serve(project):
    return send_from_directory(GENERATED_ROOT / project, "index.html")

@app.route("/<project>/<path:p>")
def assets(project, p):
    return send_from_directory(GENERATED_ROOT / project, p)

@app.route("/api/health")
def health():
    return jsonify(status="ok", engine="NovaForge")

#-----------------DEPLOYMENT-----------------

@app.route('/api/deploy', methods=['POST'])
def deploy_project():
    """Copy selected project into deploy_target/ (no Netlify)."""
    try:
        data = request.json or {}
        project_name = data.get("projectName") or "website"
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "-"
            for c in project_name.strip()
        )
        project_dir = GENERATED_ROOT / safe_name

        if not project_dir.exists():
            return jsonify({
                "success": False,
                "error": f"Project folder not found for '{safe_name}'. Generate code first."
            }), 400

        # 1) Clear old deploy_target files
        for item in DEPLOY_TARGET.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # 2) Copy this project into deploy_target/
        for item in project_dir.iterdir():
            dest = DEPLOY_TARGET / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        print(f"📦 Copied project '{safe_name}' to deploy_target/")

        return jsonify({
            "success": True,
            "message": f"Project '{safe_name}' copied to deploy_target."
        })
    except Exception as e:
        print("Deploy error:", e)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
@app.route("/api/projects", methods=["GET"])
def list_projects():
    """List all saved generated projects."""
    projects = []
    for entry in GENERATED_ROOT.iterdir():
        if entry.is_dir():
            projects.append(entry.name)
    return jsonify(success=True, projects=projects)
@app.route("/api/projects/<project_name>", methods=["GET"])
def get_project(project_name):
    safe_name = "".join(c for c in project_name if c.isalnum() or c in "-_")
    pdir = GENERATED_ROOT / safe_name
    if not pdir.exists():
        return jsonify(success=False, error="Project not found"), 404

    html = (pdir / "index.html").read_text(encoding="utf-8")
    css = (pdir / "style.css").read_text(encoding="utf-8")
    js = (pdir / "app.js").read_text(encoding="utf-8")
    backend = (pdir / "backend.py").read_text(encoding="utf-8")

    return jsonify(
        success=True,
        code={"html": html, "css": css, "js": js, "backend": backend},
        projectName=safe_name,
    )


# ----------------- RUN -----------------
if __name__ == "__main__":
    print("🚀 NovaForge running on http://localhost:5000")
    app.run(debug=True, port=5000)

















