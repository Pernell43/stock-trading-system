from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Stock, StockPrice  # Import models example
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

# Log out route, may need to adjust this better
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

# Portfolio Blank Route
@routes.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")

# Market Blank Route
@routes.route("/market")
@login_required
def market():
    """Fetch stock data and send it to the frontend."""
    stocks = Stock.query.all()
    stock_data = [
        {
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "volume": stock.volume,
            "current_price": stock.current_price,
            "market_cap": stock.market_cap,
        }
        for stock in stocks
    ]
    return render_template("market.html", stocks=stock_data)

# Settings Blank Route
@routes.route("/settings")
def settings():
    return render_template("settings.html", user=current_user)

# When the user needs to be referenced
@routes.route("/api/user", methods=["GET"])
@login_required
def get_user_data():
    """Returns the current logged-in user details as JSON."""
    user_data = {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "username": current_user.username,
        "age": current_user.age,
        "country": current_user.country,
        "currency": current_user.currency,
        "isAdministrator": current_user.isAdministrator
    }
    return jsonify(user_data), 200

# For updating the user
@routes.route("/api/user/update", methods=["PUT"])
@login_required
def update_user():
    """Allows a user to update their profile details."""
    data = request.json  # Get data from JSON request
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    # Update only provided fields
    if "first_name" in data:
        current_user.first_name = data["first_name"]
    if "last_name" in data:
        current_user.last_name = data["last_name"]
    if "email" in data:
        current_user.email = data["email"]
    if "username" in data:
        current_user.username = data["username"]
    if "age" in data:
        current_user.age = data["age"]
    if "country" in data:
        current_user.country = data["country"]
    if "currency" in data:
        current_user.currency = data["currency"]

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200

# Delete User Account
@routes.route("/api/user/delete", methods=["DELETE"])
@login_required
def delete_account():
    """Deletes the logged-in user account."""
    db.session.delete(current_user)
    db.session.commit()
    return jsonify({"message": "Account deleted successfully"}), 200

@routes.route("/admin", methods=["GET", "POST"])
@login_required  # Ensures only logged-in users can access
def admin():
    if not current_user.isAdministrator:
        flash("Access denied: You are not an administrator!", "error")
        return redirect(url_for("routes.home"))

    if request.method == "POST":
        ticker = request.form.get("ticker").upper()
        company_name = request.form.get("company_name")
        volume = request.form.get("volume")
        initial_price = request.form.get("initial_price")

        # Ensure all fields are filled
        if not ticker or not company_name or not volume or not initial_price:
            flash("All fields are required!", "error")
        else:
            try:
                volume = int(volume)
                initial_price = float(initial_price)

                # Check if the stock already exists
                existing_stock = Stock.query.filter_by(ticker=ticker).first()
                if existing_stock:
                    flash(f"Stock {ticker} already exists!", "error")
                else:
                    new_stock = Stock(
                        ticker=ticker,
                        company_name=company_name,
                        volume=volume,
                        initial_price=initial_price,
                        current_price=initial_price,
                        market_cap=volume * initial_price
                    )
                    db.session.add(new_stock)
                    db.session.commit()
                    flash(f"Stock {ticker} added successfully!", "success")
            except ValueError:
                flash("Invalid volume or price format!", "error")

    return render_template("adminAddTicker.html")

@routes.route("/market/<string:stock_ticker>")
def stock(stock_ticker):
    from app.models import Stock, StockPrice
    stock = Stock.query.filter_by(ticker=stock_ticker).first_or_404()
    stock_prices = StockPrice.query.filter_by(stock_id=stock.id).order_by(StockPrice.timestamp.asc()).all()
    
    return render_template("stock.html", stock=stock, prices=stock_prices)

@routes.route("/stock/<string:ticker>")
def stock_details(ticker):
    from app.models import Stock, StockPrice
    stock = Stock.query.filter_by(ticker=ticker.upper()).first()
    if not stock:
        return "Stock not found", 404
    
    # Get historical price data
    stock_prices = StockPrice.query.filter_by(stock_id=stock.id).order_by(StockPrice.timestamp).all()
    price_data = [{"time": price.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "price": price.price} for price in stock_prices]

    return jsonify({
        "ticker": stock.ticker,
        "company_name": stock.company_name,
        "current_price": stock.current_price,
        "market_cap": stock.market_cap,
        "history": price_data
    })