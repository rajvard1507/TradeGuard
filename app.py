from flask import Flask, redirect, url_for
from config import SECRET_KEY
from routes import auth, trader, admin

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.register_blueprint(auth.bp)
app.register_blueprint(trader.bp, url_prefix="/trader")
app.register_blueprint(admin.bp, url_prefix="/admin")

@app.get("/")
def index():
    if "role" in __import__("flask").session:
        if __import__("flask").session["role"] == "admin":
            return redirect(url_for("admin.queue"))
        return redirect(url_for("trader.dashboard"))
    return redirect(url_for("auth.login"))

if __name__ == "__main__":
    app.run(debug=True)
