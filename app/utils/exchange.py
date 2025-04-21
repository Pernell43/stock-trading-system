from app.models import Portfolio, Transaction, User
from flask_login import current_user
from datetime import datetime

def complete_order(order):
    from app import db
    user = User.query.get(order.user_id)
    stock = order.stock  # thanks to the backref
    price = stock.current_price
    total = price * order.volume

    if order.order_type == "buy":
        if user.cash_balance >= total:
            user.cash_balance -= total

            # Add to or update portfolio
            portfolio_item = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
            if portfolio_item:
                portfolio_item.shares += order.volume
            else:
                portfolio_item = Portfolio(user_id=user.id, stock_id=stock.id, shares=order.volume)
                db.session.add(portfolio_item)

            # Record transaction
            transaction = Transaction(
                buyer_id=user.id,
                seller_id=None,  # 'market' or null
                stock_id=stock.id,
                price=price,
                volume=order.volume,
                status="Success",
                timestamp=datetime.utcnow()
            )
            db.session.add(transaction)
            order.is_active = False
        else:
            print(f"[!] Insufficient funds for {user.username}'s buy order")
    
    elif order.order_type == "sell":
        portfolio_item = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
        if portfolio_item and portfolio_item.shares >= order.volume:
            portfolio_item.shares -= order.volume
            user.cash_balance += total

            # Remove empty holding
            if portfolio_item.shares == 0:
                db.session.delete(portfolio_item)

            # Record transaction
            transaction = Transaction(
                buyer_id=None,
                seller_id=user.id,
                stock_id=stock.id,
                price=price,
                volume=order.volume,
                status="Success",
                timestamp=datetime.utcnow()
            )
            db.session.add(transaction)
            order.is_active = False
        else:
            print(f"[!] Not enough shares to fulfill sell order for {user.username}")
    
    db.session.commit()
