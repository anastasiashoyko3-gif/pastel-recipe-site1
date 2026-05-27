from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from werkzeug.utils import secure_filename
from supabase import create_client
import os
import random

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
INVITE_CODE = os.getenv("INVITE_CODE", "secretcake2026")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_access(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("access_granted"):
            return redirect(url_for("invite", code=""))
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
@require_access
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    calories = request.args.get("calories", "").strip()

    response = supabase.table("recipes").select("*").order("id", desc=True).execute()

    recipes = response.data

    if q:
        recipes = [
            r for r in recipes
            if q.lower() in r["title"].lower()
            or q.lower() in r["ingredients"].lower()
        ]

    if category:
        recipes = [r for r in recipes if r["category"] == category]

    if calories:
        recipes = [r for r in recipes if r["calories"] == calories]

    return render_template(
        "index.html",
        recipes=recipes,
        q=q,
        category=category,
        calories=calories
    )


@app.route("/invite/<code>")
def invite(code):
    if code == INVITE_CODE:
        session["access_granted"] = True
        flash("Доступ відкрито ✨")
        return redirect(url_for("index"))

    return render_template(
        "locked.html",
        invite_code=INVITE_CODE,
        error="Невірне посилання 😭"
    )


@app.route("/recipe/<int:recipe_id>")
@require_access
def recipe(recipe_id):
    response = supabase.table("recipes").select("*").eq("id", recipe_id).execute()

    recipe = response.data[0] if response.data else None

    if not recipe:
        return redirect(url_for("index"))

    return render_template("recipe.html", recipe=recipe)


@app.route("/random")
@require_access
def random_recipe():
    response = supabase.table("recipes").select("id").execute()

    items = response.data

    if not items:
        flash("Рецептів ще немає 😭")
        return redirect(url_for("index"))

    item = random.choice(items)

    return redirect(url_for("recipe", recipe_id=item["id"]))


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin"] = True
            session["access_granted"] = True
            return redirect(url_for("admin_panel"))

        flash("Невірний пароль 😭")

    return render_template("admin_login.html")


@app.route("/admin/panel")
@require_admin
def admin_panel():
    response = supabase.table("recipes").select("*").order("id", desc=True).execute()

    recipes = response.data

    return render_template("admin_panel.html", recipes=recipes)


@app.route("/admin/add", methods=["GET", "POST"])
@require_admin
def admin_add():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        calories = request.form.get("calories", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        steps = request.form.get("steps", "").strip()

        image_name = None

        image = request.files.get("image")

        if image and image.filename and allowed_file(image.filename):
            image_name = secure_filename(image.filename)

            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_name))

        supabase.table("recipes").insert({
            "title": title,
            "category": category,
            "calories": calories,
            "ingredients": ingredients,
            "steps": steps,
            "image": image_name
        }).execute()

        flash("Рецепт додано ✅")

        return redirect(url_for("admin_panel"))

    return render_template("admin_form.html", recipe=None)


@app.route("/admin/edit/<int:recipe_id>", methods=["GET", "POST"])
@require_admin
def admin_edit(recipe_id):
    response = supabase.table("recipes").select("*").eq("id", recipe_id).execute()

    recipe = response.data[0] if response.data else None

    if not recipe:
        return redirect(url_for("admin_panel"))

    if request.method == "POST":
        image_name = recipe["image"]

        image = request.files.get("image")

        if image and image.filename and allowed_file(image.filename):
            image_name = secure_filename(image.filename)

            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_name))

        supabase.table("recipes").update({
            "title": request.form.get("title", "").strip(),
            "category": request.form.get("category", "").strip(),
            "calories": request.form.get("calories", "").strip(),
            "ingredients": request.form.get("ingredients", "").strip(),
            "steps": request.form.get("steps", "").strip(),
            "image": image_name
        }).eq("id", recipe_id).execute()

        flash("Рецепт оновлено ✅")

        return redirect(url_for("admin_panel"))

    return render_template("admin_form.html", recipe=recipe)


@app.route("/admin/delete/<int:recipe_id>", methods=["POST"])
@require_admin
def admin_delete(recipe_id):
    supabase.table("recipes").delete().eq("id", recipe_id).execute()

    flash("Рецепт видалено ❌")

    return redirect(url_for("admin_panel"))


@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
