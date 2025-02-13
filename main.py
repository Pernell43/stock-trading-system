from flask import Flask, render_template, request, url_for
import os

app = Flask(__name__, static_folder="app\\static", template_folder=os.path.join(os.getcwd(), "app\\templates"))

# app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "app", "templates")) Use this line instead of the above if on mac


@app.route("/")
def home():
    return render_template("index.html") #renders templates in the folder we establish when creating app variable

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        return f"Received login for {username}"  # Temporary feedback

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        return f"User {username} registered with {email}"  # Temporary feedback

    return render_template("register.html")

# Portfolio Page
@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")

# Market Overview Page (Extra: Could show live stock data in the future)
@app.route("/market")
def market():
    return render_template("market.html")

# Settings Page (Future use)
@app.route("/settings")
def settings():
    return render_template("settings.html")


if __name__ == "__main__":
    app.run(debug=True)
