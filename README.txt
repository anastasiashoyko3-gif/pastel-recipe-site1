
PASTEL RECIPE SITE

Локально:
pip install -r requirements.txt
python app.py

Відкрити:
http://127.0.0.1:5000

Адмінка:
http://127.0.0.1:5000/admin
Пароль стандартний:
admin123

Invite:
http://127.0.0.1:5000/invite/secretcake2026

Render:
Build command:
pip install -r requirements.txt

Start command:
gunicorn app:app

Environment variables:
SECRET_KEY = будь-який довгий текст
ADMIN_PASSWORD = твій пароль
INVITE_CODE = твій секретний код
