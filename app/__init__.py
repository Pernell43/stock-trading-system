from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_apscheduler import APScheduler
import random
import os

# Initialize extensions (db, migrate, bcrypt, login_manager, scheduler)
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
scheduler = APScheduler()  # Initialize the scheduler

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

    create_database(app)

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
    """Closes all active database connections, deletes the database file, and creates a new one."""
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
                print("⚠️ Error: Database file is locked. Ensure no other processes are using it.")
                return

        # Recreate the database
        db.create_all()
        print("Created new database!")

        # Create an admin user if none exists
        from app.models import User  # Import here to prevent circular imports
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
                isAdministrator=True  # Make admin
            )
            admin.set_password("AdminPass123")  # Hash password
            db.session.add(admin)
            db.session.commit()
            print("Admin account created!")

# Function to update stock prices every minute
@scheduler.task('interval', id='update_stock_prices', seconds=60, misfire_grace_time=10)
def update_stock_prices():
    from app.models import Stock
    from app.models import StockPrice

    with scheduler.app.app_context():
        stocks = Stock.query.all()
        for stock in stocks:
            last_price = stock.current_price
            price_change = random.uniform(-1, 1)  # Simulate small price fluctuations
            new_price = max(0.01, last_price + price_change)  # Prevent negative prices

            stock.current_price = new_price
            stock.market_cap = new_price * stock.volume  # Recalculate market cap
            
            # Store the price change in the StockPrice table
            new_stock_price = StockPrice(stock_id=stock.id, price=new_price)
            db.session.add(new_stock_price)
        
        db.session.commit()
        print("Stock prices updated!")
