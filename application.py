import os, hashlib, requests, json

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
    if session != []:
        return render_template("home.html", data=session)
    else:
        return render_template("index.html", title="Welcome")

@app.route("/home", methods=["POST"])
def index_form():
    # Checks which form was submitted
    if "register" in request.form:
        return register()
    elif "login" in request.form:
        return login()
    else:
        return "Error"

def login():
    email = request.form.get("email")
    password = request.form.get("password")

    # Check if user exists, error if not
    users = db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).fetchall()


    for user in users:

        # Check password
        if hashlib.md5(password.encode()).hexdigest() != user.password_hash:
            print(f"Passwords do not match")
            return render_template("index.html", modal_title="Error", modal_body="Incorrect password.")

        else:
            print(f"Passwords match")

            # Log user in
            login_user(user.id, user.email, user.first_name, user.last_name)

        return render_template("home.html", data=session)

    # If no user found, throw an error
    return render_template("index.html", modal_title="Error", modal_body="A user with this email address could not be found. Please register.")

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
    last_insert = db.execute("INSERT INTO users (first_name, last_name, email, password_hash) VALUES (:first_name, :last_name, :email, :password_hash) RETURNING id",
              {"first_name": first_name, "last_name": last_name, "email": email, "password_hash": password_hash})

    db.commit()

    userid = last_insert.fetchone()
    userid = userid[0]

    print (userid)

    # Log user in
    login_user(userid, email, first_name, last_name)

    return render_template("home.html", modal_title="Welcome, " + session['first_name'], modal_body="Sign up complete", data=session)

def login_user(userid, email, first_name, last_name):
    session['userid'] = userid
    session['email'] = email
    session['first_name'] = first_name
    session['last_name'] = last_name

@app.route("/signedout")
def signOut():
    session = []
    return render_template("index.html", modal_title="Signed out", modal_body="You have been signed out")

@app.route("/books", methods=["GET"])
def book_search():
    search = request.args.get("search")

    results = db.execute("SELECT * FROM books WHERE LOWER(isbn) LIKE LOWER(:search) OR LOWER(title) LIKE LOWER(:search) OR LOWER(author) LIKE LOWER(:search)", {"search": "%"+search+"%"}).fetchall()


    return render_template("search_results.html", results=results, search=search)

@app.route("/books/<string:isbn>")
def book(isbn):
    books, reviews, goodreads = get_book_info(isbn)

    user_has_reviewed = 0
    for review in reviews:
        if review.userid == session['userid']:
            user_has_reviewed = 1

    for book in books:
        return render_template("book.html", book=book, user_has_reviewed=user_has_reviewed, reviews = reviews, goodreads = goodreads)

    return "Error"

@app.route("/books/<string:isbn>/review_submitted", methods=["POST"])
def submit_review(isbn):
    score = request.form.get("rating")
    review = request.form.get("review")

    db.execute("INSERT INTO reviews (userid, bookid, score, review, timestamp)\
                SELECT :userid, (SELECT id FROM books WHERE isbn = :isbn), :score, :review, NOW()",
              {"userid": session['userid'], "isbn": isbn, "score": score, "review": review})
    db.commit()

    books, reviews, goodreads = get_book_info(isbn)

    for book in books:
        return render_template("book.html", book=book, user_has_reviewed=1, reviews = reviews, goodreads = goodreads)

    return "Error"

def get_book_info(isbn):
    # Get Goodreads info
    goodreads = goodreads_api(isbn)

    # Get book info
    books = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()

    # Get reviews of this book by this user
    reviews = db.execute("SELECT * FROM reviews WHERE bookid IN (SELECT id FROM books WHERE isbn = :isbn)", {"isbn": isbn}).fetchall()

    return books, reviews, goodreads

def goodreads_api(isbn):
    results = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "eP7x0SkdEcWBAmOzZ9GYQ", "isbns": isbn})
    results = results.json()
    results = results['books']

    for result in results:
        response = {"average_rating": result['average_rating'], "reviews_count": result['reviews_count']}

    return response

@app.route("/api/<string:isbn>")
def api(isbn):
    # Get book info
    books = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    for book in books:
        title = book.title
        author = book.author
        year = book.year



        reviews = db.execute("SELECT COUNT(*), AVG(score) FROM reviews WHERE bookid IN (SELECT id FROM books WHERE isbn = :isbn)", {"isbn": isbn}).fetchall()
        for review in reviews:
            review_count = review[0]
            average_score = float(review[1])

        response = {"title": title, "author": author, "year": year, "isbn": isbn, "review_count": review_count, "average_score": average_score}

        json_response = json.dumps(response)

        return json_response

    return render_template("404.html")
