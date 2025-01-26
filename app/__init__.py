from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import and register routes
    from app.routes.user_routes import user_blueprint
    from app.routes.admin_routes import admin_blueprint
    app.register_blueprint(user_blueprint)
    app.register_blueprint(admin_blueprint)
    
    return app
