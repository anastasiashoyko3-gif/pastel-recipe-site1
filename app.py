
import os
from supabase import create_client
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
INVITE_CODE = os.getenv("INVITE_CODE", "secretcake2026")

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER




def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_access(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("access_granted") or session.get("admin"):
            return func(*args, **kwargs)
        return render_template("locked.html", invite_code=INVITE_CODE)
    return wrapper


def require_admin(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("admin"):
            return func(*args, **kwargs)
        return redirect(url_for("admin_login"))
    return wrapper


@app.route("/")
@require_access
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    calories = request.args.get("calories", "").strip()

    sql = "SELECT * FROM recipes WHERE 1=1"
    params = []

    if q:
        sql += " AND (LOWER(title) LIKE LOWER(?) OR LOWER(ingredients) LIKE LOWER(?) OR LOWER(steps) LIKE LOWER(?))"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if category:
        sql += " AND category=?"
        params.append(category)

    if calories:
    sql += " AND calories=?"
    params.append(calories)

response = supabase.table("recipes").select("*").execute()
recipes = response.data

return render_template("index.html", recipes=recipes, q=q, category=category, calories=calories)
@app.route("/invite/<code>")
def invite(code):
    if code == INVITE_CODE:
        session["access_granted"] = True
        flash("Доступ відкрито ✨")
        return redirect(url_for("index"))
    return render_template("locked.html", invite_code=INVITE_CODE, error="Невірне посилання 😭")


@app.route("/recipe/<int:recipe_id>")
@require_access
def recipe(recipe_id):
  response = supabase.table("recipes").select("*").eq("id", recipe_id).execute()

item = response.data[0] if response.data else None
    if not item:
        return redirect(url_for("index"))
    return render_template("recipe.html", recipe=item)


@app.route("/random")
@require_access
def random_recipe():
   response = supabase.table("recipes").select("id").execute()

items = response.data

if items:
    import random
    item = random.choice(items)
else:
    item = None
    if not item:
        flash("Рецептів ще немає 😭")
        return redirect(url_for("index"))
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
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_name))

        db.execute("""
            UPDATE recipes
            SET title=?, category=?, calories=?, ingredients=?, steps=?, image=?
            WHERE id=?
        """, (
            request.form.get("title", "").strip(),
            request.form.get("category", "").strip(),
            request.form.get("calories", "").strip(),
            request.form.get("ingredients", "").strip(),
            request.form.get("steps", "").strip(),
            image_name,
            recipe_id
        ))
        db.commit()
        db.close()

        flash("Рецепт оновлено ✅")
        return redirect(url_for("admin_panel"))

    db.close()
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
