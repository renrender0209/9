from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    avatar_url = db.Column(db.String(200))
    
    # リレーションシップ
    playlists = db.relationship('Playlist', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    watch_history = db.relationship('WatchHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'avatar_url': self.avatar_url
        }

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    thumbnail_url = db.Column(db.String(200))
    
    # リレーションシップ
    videos = db.relationship('PlaylistVideo', backref='playlist', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_public': self.is_public,
            'thumbnail_url': self.thumbnail_url,
            'video_count': self.videos.count(),
            'videos': [video.to_dict() for video in self.videos.limit(5)]
        }

class PlaylistVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    thumbnail_url = db.Column(db.String(200))
    duration = db.Column(db.Integer)  # 秒単位
    uploader = db.Column(db.String(100))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'thumbnail_url': self.thumbnail_url,
            'duration': self.duration,
            'uploader': self.uploader,
            'added_at': self.added_at.isoformat(),
            'position': self.position
        }

class WatchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    thumbnail_url = db.Column(db.String(200))
    uploader = db.Column(db.String(100))
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)
    watch_duration = db.Column(db.Integer)  # 視聴時間（秒）
    total_duration = db.Column(db.Integer)  # 動画の総時間（秒）
    
    # 重複を避けるためのユニーク制約
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='unique_user_video'),)

    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'thumbnail_url': self.thumbnail_url,
            'uploader': self.uploader,
            'watched_at': self.watched_at.isoformat(),
            'watch_duration': self.watch_duration,
            'total_duration': self.total_duration,
            'progress_percent': round((self.watch_duration / self.total_duration) * 100, 2) if self.total_duration else 0
        }

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    thumbnail_url = db.Column(db.String(200))
    uploader = db.Column(db.String(100))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 重複を避けるためのユニーク制約
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='unique_user_favorite'),)

    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'thumbnail_url': self.thumbnail_url,
            'uploader': self.uploader,
            'added_at': self.added_at.isoformat()
        }

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.String(10), nullable=False)  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 重複を避けるためのユニーク制約
    __table_args__ = (db.UniqueConstraint('user_id', 'video_id', name='unique_user_rating'),)

    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': {
                'username': self.author.username,
                'avatar_url': self.author.avatar_url
            },
            'video_id': self.video_id,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'likes': self.likes
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'info', 'success', 'warning', 'error'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    action_url = db.Column(db.String(200))  # オプション：クリック時のリンク先

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'action_url': self.action_url
        }

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(200), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'results_count': self.results_count,
            'searched_at': self.searched_at.isoformat()
        }

class Download(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    quality = db.Column(db.String(20), nullable=False)
    format = db.Column(db.String(10), nullable=False)  # 'mp4', 'webm', 'mp3'
    file_size = db.Column(db.BigInteger)  # バイト単位
    download_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)  # ダウンロードリンクの有効期限

    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'quality': self.quality,
            'format': self.format,
            'file_size': self.file_size,
            'download_url': self.download_url,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }