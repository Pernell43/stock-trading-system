from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_apscheduler import APScheduler
import random
import os
from datetime import datetime

_last_update_day = None

def is_new_day():
    global _last_update_day
    today = datetime.now().date()
    if _last_update_day != today:
        _last_update_day = today
        return True
    return False
    

# Initialize extensions (db, migrate, bcrypt, login_manager, scheduler)
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
scheduler = APScheduler() # Initialize the scheduler

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # This routes correctly

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = "the secret key for app"  # Change this in production
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'stocktradingapp.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    scheduler.init_app(app)  # Attach scheduler to app
    scheduler.start()  # Start the scheduler

    # Flask-Login Configuration
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"

    from app.models import User, Stock, StockPrice  # Import models

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))  # Loads user by ID

    # Import and register blueprints (if using modular routes)
    from app.routes import routes
    app.register_blueprint(routes, url_prefix="/")

    reset_database(app)

    return app

def create_database(app):
    """Creates the database if it does not exist."""
    db_path = os.path.join(BASE_DIR, 'stocktradingapp.db')

    if not os.path.exists(db_path):
        with app.app_context():  # Correctly set application context
            db.create_all()
        print('Created Database!')

# Set this to get a refresh
def reset_database(app):
    """Closes all active database connections/sessions, deletes the database file, and creates a new one."""
    db_path = os.path.join(BASE_DIR, 'stocktradingapp.db')

    with app.app_context():
        # Close all active database sessions
        db.session.remove()

        # Dispose of the database engine (prevents lock issues)
        db.engine.dispose()

        # Delete the database file if it exists
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print("🗑️ Database wiped.")
            except PermissionError:
                print("Error: Database file is locked. Ensure no other processes are using it.")
                return

        # Recreate the database
        db.create_all()
        print("Created new database!")

        # Create an admin user if none exists
        from app.models import User, Transaction, Portfolio, MarketConfig  # Import here to prevent circular imports
        from datetime import time
        admin_email = "admin@example.com"
        existing_admin = User.query.filter_by(email=admin_email).first()

        if not existing_admin:
            admin = User(
                first_name="Admin",
                last_name="User",
                email=admin_email,
                username="admin",
                age=30,
                country="US",
                ssn=None,
                currency="USD",
                isAdministrator=True,  # Make admin
                cash_balance=10000000
                
            )
            admin.set_password("AdminPass123")  # Hash password
            db.session.add(admin)
            db.session.commit()
            print("Admin account created!")

        existing_config = MarketConfig.query.first()
        if not existing_config:
            config = MarketConfig(
                open_time=time(9,0),
                close_time=time(16,0),
                weekdays_only=True
            )
        db.session.add(config)
        db.session.commit()
        print("📈 Default market hours set: 9 AM – 4 PM (Weekdays only)")

# Function to update stock prices every minute
# @scheduler.task('interval', id='update_stock_prices', seconds=60, misfire_grace_time=10) # OLD FUNCTION, LEAVING JUST IN CASE
# def update_stock_prices():
#     from app.models import Stock
#     from app.models import StockPrice

#     with scheduler.app.app_context():
#         stocks = Stock.query.all()
#         for stock in stocks:
#             last_price = stock.current_price
#             price_change = random.uniform(-1, 1)  # Simulate small price fluctuations
#             new_price = max(0.01, last_price + price_change)  # Prevent negative prices

#             stock.current_price = new_price
#             stock.market_cap = new_price * stock.volume  # Recalculate market cap
            
#             # Store the price change in the StockPrice table
#             new_stock_price = StockPrice(stock_id=stock.id, price=new_price)
#             db.session.add(new_stock_price)
        
#         db.session.commit()
#         print("Stock prices updated!")

@scheduler.task('interval', id='update_stock_prices', seconds=60, misfire_grace_time=10)
def update_stock_prices():
    from app.models import Stock, StockPrice, PendingOrder
    from datetime import datetime

    with scheduler.app.app_context():
        stocks = Stock.query.all()
        for stock in stocks:
            try:
                last_price = stock.current_price
                price_change = random.uniform(-1, 1)
                new_price = max(0.01, last_price + price_change)

                # Track open, high, low
                if is_new_day() or stock.opening_price is None:
                    stock.opening_price = new_price
                    stock.high_price = new_price
                    stock.low_price = new_price
                else:
                    if new_price > stock.high_price:
                        stock.high_price = new_price
                    if new_price < stock.low_price:
                        stock.low_price = new_price

                # Update current stats
                stock.current_price = new_price
                stock.market_cap = new_price * stock.volume
                db.session.add(StockPrice(stock_id=stock.id, price=new_price))

                # Try completing eligible orders safely
                active_orders = PendingOrder.query.filter_by(stock_id=stock.id, is_active=True).all()
                for order in active_orders:
                    try:
                        if (
                            (order.order_type == "buy" and new_price <= order.target_price) or
                            (order.order_type == "sell" and new_price >= order.target_price)
                        ):    
                            complete_order(order)
                    except Exception as e:
                        print(f"⚠️ Failed to complete order ID {order.id}: {e}")

            except Exception as e:
                print(f"Error processing stock {stock.ticker}: {e}")

        db.session.commit()
        print("📊 Scheduler update complete at", datetime.now())

@scheduler.task('cron', id='reset_daily_stock_metrics', hour=0, minute=0)
def reset_daily_stock_metrics():
    from app.models import Stock
    from datetime import datetime

    with scheduler.app.app_context():
        stocks = Stock.query.all()
        for stock in stocks:
            stock.opening_price = None
            stock.high_price = None
            stock.low_price = None

        db.session.commit()
        print("Daily price metrics reset at midnight:", datetime.now())

def complete_order(order):
    from app.models import User, Portfolio, Transaction, Stock
    with scheduler.app.app_context():
        user = User.query.get(order.user_id)
        stock = Stock.query.get(order.stock_id)
        price = stock.current_price
        total = price * order.volume

        if order.order_type == "buy":
            if user.cash_balance >= total:
                user.cash_balance -= total
                portfolio = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
                if portfolio:
                    portfolio.shares += order.volume
                else:
                    db.session.add(Portfolio(user_id=user.id, stock_id=stock.id, shares=order.volume))

                db.session.add(Transaction(
                    buyer_id=user.id,
                    stock_id=stock.id,
                    volume=order.volume,
                    price=price,
                    status="Success"
                ))
                order.is_active = False

        elif order.order_type == "sell":
            portfolio = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
            if portfolio and portfolio.shares >= order.volume:
                portfolio.shares -= order.volume
                user.cash_balance += total

                if portfolio.shares == 0:
                    db.session.delete(portfolio)

                db.session.add(Transaction(
                    seller_id=user.id,
                    stock_id=stock.id,
                    volume=order.volume,
                    price=price,
                    status="Success"
                ))
                order.is_active = False

        db.session.commit()