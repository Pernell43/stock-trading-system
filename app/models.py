# Import necessary modules
from . import db, bcrypt  # Import database and bcrypt from __init__.py
from flask_login import UserMixin


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


#Create more models as necessary below