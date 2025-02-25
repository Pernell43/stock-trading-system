from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os

# Initialize extensions (db, migrate, bcrypt, login_manager)
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()

BASE_DIR = os.path.abspath(os.path.dirname(__file__)) # this routes correctly

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

    #Flask-Login Configuration
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"

    from app.models import User # import more models as we go further, just put a comma after user and type away as necessary

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
        with app.app_context():  # ✅ Correctly set application context
            db.create_all()
        print('Created Database!')