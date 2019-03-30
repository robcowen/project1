import os, hashlib

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html", title="Welcome")

@app.route("/register", methods=["POST"])
def register():
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")
    password1 = request.form.get("password1")
    password2 = request.form.get("password2")

    # Check if user exists, error if not
    user_exists = db.execute("SELECT COUNT(*) FROM users WHERE email = :email", {"email": email}).fetchone()
    for user_exist in user_exists:
        if user_exist > 0:
            # User already exists
            return render_template("index.html", modal_title="Error", modal_body="A user with this email already exists. Please sign in.")

    # Check passwords
    if (password1 != password2):
        return render_template("index.html", modal_title="Error", modal_body="The entered passwords do not match. Please check and try again.")

    # Hash password
    h = hashlib.md5(password1.encode())
    password_hash = h.hexdigest()

    # Save to database
    db.execute("INSERT INTO users (first_name, last_name, email, password_hash) VALUES (:first_name, :last_name, :email, :password_hash)",
              {"first_name": first_name, "last_name": last_name, "email": email, "password_hash": password_hash})
    db.commit()

    return render_template("register_success.html", title="Success", data=email)
