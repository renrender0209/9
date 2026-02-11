import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per day", "60 per hour"],
    storage_uri="memory://"
)

# シンプルなメモリキャッシュ
cache_store = {}
cache_timeout = {}

def cache_get(key):
    import time
    if key in cache_store:
        if time.time() - cache_timeout.get(key, 0) < 300:
            return cache_store[key]
        else:
            del cache_store[key]
            if key in cache_timeout:
                del cache_timeout[key]
    return None

def cache_set(key, value, timeout=300):
    import time
    cache_store[key] = value
    cache_timeout[key] = time.time()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    database_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインが必要です。'
    login_manager.login_message_category = 'info'
    
    CORS(app)
    
    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    import models
    db.create_all()

try:
    from auth_routes import auth
    app.register_blueprint(auth)
except ImportError:
    logging.warning("auth_routes not found")

try:
    from backend_routes import backend
    app.register_blueprint(backend)
except ImportError:
    logging.warning("backend_routes not found")

try:
    from additional_backend_routes import additional
    app.register_blueprint(additional)
except ImportError:
    logging.warning("additional_backend_routes not found")

from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)