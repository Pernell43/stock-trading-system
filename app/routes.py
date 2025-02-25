from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User  # Import models example
from app import db, bcrypt

routes = Blueprint("routes", __name__)

@routes.route("/")
def home():
    return render_template("index.html")

@routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", category="success")
            return redirect(url_for("routes.home"))
        else:
            flash("Invalid email or password. Please try again.", category="error")

    return render_template("login.html")

@routes.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", category="info")
    return redirect(url_for("routes.login"))

@routes.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        age = request.form.get("age")
        country = request.form.get("country")
        ssn = request.form.get("ssn") if country == "US" else None  # Only for US users
        currency = request.form.get("currency")

        # Input validation
        if len(email) < 4:
            flash('Email must be greater than 3 characters', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character', category='error')
        elif password != confirm_password:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters', category='error')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists.', category='error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists.', category='error')
        else:
            # Create a new user instance
            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                age=int(age),
                country=country,
                ssn=ssn,
                currency=currency,
                isAdministrator=False  # Default to regular user
            )
            
            # Hash and store password securely
            new_user.set_password(password)

            # Add to database and commit
            db.session.add(new_user)
            db.session.commit()

            flash("Account has been created!", category='success')
            return redirect(url_for("routes.home"))  # Redirect to home page after registration

    return render_template("register.html")

@routes.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")

@routes.route("/market")
def market():
    return render_template("market.html")

@routes.route("/settings")
def settings():
    return render_template("settings.html")
