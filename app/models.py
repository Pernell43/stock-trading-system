# Import necessary modules
from . import db, bcrypt  # Import database and bcrypt from __init__.py
from flask_login import UserMixin
from datetime import datetime
from datetime import time


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)

    # Authentication
    password = db.Column(db.String(200), nullable=False)  # Hashed password

    # Additional User Details
    age = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(50), nullable=False)
    ssn = db.Column(db.String(11), nullable=True)  # Only for US users
    currency = db.Column(db.String(10), nullable=False)  # Preferred currency

    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # Auto-set creation time
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())  # Auto-update on modification

    # For Transactions
    cash_balance = db.Column(db.Float, default=0)  # Give admin $1,000,000
    portfolios = db.relationship('Portfolio', backref='owner', lazy=True)
    transactions = db.relationship('Transaction', foreign_keys='[Transaction.buyer_id]', backref='buyer', lazy=True)

    # For Administration
    isAdministrator = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        """Hashes and stores the password."""
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verifies if the entered password matches the stored hash."""
        return bcrypt.check_password_hash(self.password, password)
    
    def promote_to_admin(self):
        """Promotes user to admin (should only be called by an existing admin)."""
        self.is_admin = True

    def demote_from_admin(self):
        """Demotes an admin back to a regular user (should only be called by an existing admin)."""
        self.is_admin = False

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"


class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    initial_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    market_cap = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Will change in a second
    opening_price = db.Column(db.Float)
    high_price = db.Column(db.Float)
    low_price = db.Column(db.Float)

    # Relationship to StockPrice
    price_history = db.relationship("StockPrice", backref="stock", lazy=True)

class StockPrice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey("stock.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Will change in a second
    price = db.Column(db.Float, nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    stock = db.relationship("Stock", backref="portfolios")

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'))
    price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Success")
    stock = db.relationship("Stock", backref="transactions")



#Time is CURRENTLY UNDEFINED
class MarketConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    open_time = db.Column(db.Time, nullable=False, default=time(0, 0))    # Market opens at 9:00 AM (I can change this for now because I still need to test) (0,0 for testing, 9,0 for launch)
    close_time = db.Column(db.Time, nullable=False, default=time(23, 59))  # Market closes at 4:00 PM (23,59) for testing (16,0 for launch)
    weekdays_only = db.Column(db.Boolean, default=True)  # Disable trading on weekends

class PendingOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)

    order_type = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    volume = db.Column(db.Integer, nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='pending_orders')
    stock = db.relationship('Stock', backref='pending_orders')