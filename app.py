import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase

# ログ設定
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# データベース設定
db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # データベース設定
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # デフォルトのSQLiteデータベース
        database_url = "sqlite:///app.db"
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインが必要です。'
    login_manager.login_message_category = 'info'
    
    # CORS設定
    CORS(app)
    
    return app

app = create_app()

# ユーザーローダー
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# データベースモデルのインポート
with app.app_context():
    import models
    db.create_all()

# ブループリントの登録
try:
    from auth_routes import auth
    app.register_blueprint(auth)
except ImportError:
    logging.warning("auth_routes not found, skipping")

try:
    from backend_routes import backend
    app.register_blueprint(backend)
except ImportError:
    logging.warning("backend_routes not found, skipping")

try:
    from additional_backend_routes import additional
    app.register_blueprint(additional)
except ImportError:
    logging.warning("additional_backend_routes not found, skipping")

# ルートをインポート
from routes import *

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)