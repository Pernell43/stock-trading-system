from flask import Blueprint, abort, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Stock, StockPrice, Transaction, Portfolio, MarketConfig, PendingOrder  # Import models example
from app import db, bcrypt
from datetime import datetime


def is_market_open():
    now = datetime.now()
    today = now.weekday()  # 0 = Monday, 6 = Sunday
    current_time = now.time()

    config = MarketConfig.query.first()
    if not config:
        return True  # Allow trading if no config yet (fail-safe for dev)

    # If weekend and market is restricted to weekdays only
    if config.weekdays_only and today >= 5:
        return False

    return config.open_time <= current_time <= config.close_time

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


@routes.route("/dashboard")
@login_required
def dashboard():
    user = current_user
    portfolio = Portfolio.query.filter_by(user_id=user.id).all()
    transactions = Transaction.query.filter(
        (Transaction.buyer_id == user.id) | (Transaction.seller_id == user.id)
    ).order_by(Transaction.timestamp.desc()).all()
    return render_template("dashboard.html", user=user, portfolio=portfolio, transactions=transactions)

@routes.route("/trade/buy/<string:ticker>", methods=["GET", "POST"])
@login_required
def trade_buy(ticker):
    stock = Stock.query.filter_by(ticker=ticker).first_or_404()

    if request.method == "POST":
        volume = int(request.form.get("volume"))
        limit_price_raw = request.form.get("limit_price")
        limit_price = float(limit_price_raw) if limit_price_raw else None

        if limit_price:  # 🧠 It's a LIMIT ORDER
            order = PendingOrder(
                user_id=current_user.id,
                stock_id=stock.id,
                order_type="buy",
                volume=volume,
                target_price=limit_price
            )
            db.session.add(order)
            db.session.commit()
            flash(f"Limit buy order placed for {volume} shares of {ticker} at ${limit_price:.2f}", "success")
            return redirect(url_for("routes.dashboard"))
        else:  # 💥 It's a MARKET ORDER
            total_price = stock.current_price * volume

            if current_user.cash_balance < total_price:
                flash("Insufficient funds for this purchase.", "error")
                return redirect(request.url)

            current_user.cash_balance -= total_price

            portfolio_item = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
            if portfolio_item:
                portfolio_item.shares += volume
            else:
                db.session.add(Portfolio(user_id=current_user.id, stock_id=stock.id, shares=volume))

            db.session.add(Transaction(
                buyer_id=current_user.id,
                seller_id=None,
                stock_id=stock.id,
                price=stock.current_price,
                volume=volume,
                status="Success"
            ))
            db.session.commit()

            flash(f"Market purchase of {volume} shares of {ticker} complete!", "success")
            return redirect(url_for("routes.dashboard"))

    return render_template("trade.html", stock=stock)

@routes.route("/trade/confirm/<string:ticker>/<int:volume>")
@login_required
def trade_confirm(ticker, volume):
    stock = Stock.query.filter_by(ticker=ticker).first_or_404()
    return render_template("trade_confirm.html", stock=stock, volume=volume)

@routes.route("/trade/sell/<string:ticker>", methods=["GET", "POST"])
@login_required
def trade_sell(ticker):
    stock = Stock.query.filter_by(ticker=ticker).first_or_404()
    portfolio_item = Portfolio.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()

    if not portfolio_item or portfolio_item.shares == 0:
        flash("You don't own any shares of this stock.", "error")
        return redirect(url_for("routes.market"))

    if request.method == "POST":
        volume = int(request.form.get("volume"))
        limit_price_raw = request.form.get("limit_price")
        limit_price = float(limit_price_raw) if limit_price_raw else None

        if volume > portfolio_item.shares:
            flash("Not enough shares to sell.", "error")
            return redirect(request.url)

        if limit_price:  # 🧠 LIMIT SELL ORDER
            order = PendingOrder(
                user_id=current_user.id,
                stock_id=stock.id,
                order_type="sell",
                volume=volume,
                target_price=limit_price
            )
            db.session.add(order)
            db.session.commit()
            flash(f"Limit sell order placed for {volume} shares of {ticker} at ${limit_price:.2f}", "success")
            return redirect(url_for("routes.dashboard"))

        else:  # 💥 MARKET SELL ORDER
            sale_total = stock.current_price * volume
            portfolio_item.shares -= volume
            current_user.cash_balance += sale_total

            db.session.add(Transaction(
                buyer_id=None,
                seller_id=current_user.id,
                stock_id=stock.id,
                price=stock.current_price,
                volume=volume,
                status="Success"
            ))

            db.session.commit()
            flash(f"Market sale of {volume} shares of {ticker} complete!", "success")
            return redirect(url_for("routes.dashboard"))

    return render_template("trade.html", stock=stock)

@routes.route("/wallet", methods=["GET", "POST"])
@login_required
def wallet():

    user = current_user
    if request.method == "POST":
        action = request.form.get("action")
        amount = float(request.form.get("amount", 0))

        if amount <= 0:
            flash("Amount must be greater than 0", "error")
            return redirect(url_for("routes.wallet"))

        if action == "deposit":
            current_user.cash_balance += amount
            flash(f"Deposited ${amount:.2f}", "success")

        elif action == "withdraw":
            if current_user.cash_balance >= amount:
                current_user.cash_balance -= amount
                flash(f"Withdrew ${amount:.2f}", "success")
            else:
                flash("Insufficient funds for withdrawal", "error")

        db.session.commit()
        return redirect(url_for("routes.wallet"))

    return render_template("wallet.html", user=current_user)

@routes.route("/order/pending/<string:ticker>", methods=["GET", "POST"])
@login_required
def place_pending_order(ticker):
    user = current_user
    stock = Stock.query.filter_by(ticker=ticker).first_or_404()

    if request.method == "POST":
        order_type = request.form.get("order_type")
        volume = int(request.form.get("volume"))
        target_price = float(request.form.get("target_price"))

        order = PendingOrder(
            user_id=current_user.id,
            stock_id=stock.id,
            order_type=order_type,
            volume=volume,
            target_price=target_price
        )
        db.session.add(order)
        db.session.commit()

        flash(f"{order_type.title()} order placed for {stock.ticker} at ${target_price}", "success")
        return redirect(url_for("routes.dashboard"))

    return render_template("place_order.html", stock=stock)

@routes.route("/order/cancel/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(order_id):
    user = current_user
    order = PendingOrder.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)

    order.is_active = False
    db.session.commit()
    flash("Order canceled successfully.", "info")
    return redirect(url_for("routes.dashboard"))