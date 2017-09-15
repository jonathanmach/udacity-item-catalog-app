from flask import Flask, redirect, url_for
# Working with Blueprints
from models.itemcatalog import itemcatalog
from models.auth import auth
from models.api import api

app = Flask(__name__)

app.register_blueprint(itemcatalog)
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(api)




@app.route('/')
def main():
    """
    Returns all categories and items
    """
    return redirect(
            url_for('itemcatalog.main'))



if __name__ == "__main__":
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
