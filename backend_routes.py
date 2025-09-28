from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from models import (
    Playlist, PlaylistVideo, WatchHistory, Favorite, Rating, Comment, 
    Notification, SearchHistory, Download
)
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import logging

backend = Blueprint('backend', __name__)

# =============================================================================
# ユーザー統計データ
# =============================================================================

@backend.route('/api/stats', methods=['GET'])
@login_required
def api_get_user_stats():
    """ユーザーの利用統計を取得"""
    try:
        # 視聴動画数
        videos_watched = WatchHistory.query.filter_by(user_id=current_user.id).count()
        
        # お気に入り数
        favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
        
        # プレイリスト数
        playlists_count = Playlist.query.filter_by(user_id=current_user.id).count()
        
        # 総視聴時間（秒）
        total_watch_time = db.session.query(func.sum(WatchHistory.watch_duration)).filter_by(user_id=current_user.id).scalar() or 0
        
        # いいね数
        likes_count = Rating.query.filter_by(user_id=current_user.id, rating='like').count()
        
        # コメント数
        comments_count = Comment.query.filter_by(user_id=current_user.id, is_deleted=False).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'videos_watched': videos_watched,
                'favorites_count': favorites_count,
                'playlists_count': playlists_count,
                'total_watch_time': total_watch_time,
                'likes_count': likes_count,
                'comments_count': comments_count
            }
        })
    except Exception as e:
        logging.error(f"ユーザー統計取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# プレイリスト管理
# =============================================================================

@backend.route('/api/playlists', methods=['GET'])
@login_required
def api_get_playlists():
    """ユーザーのプレイリスト一覧を取得"""
    try:
        playlists = Playlist.query.filter_by(user_id=current_user.id).order_by(desc(Playlist.updated_at)).all()
        return jsonify({
            'success': True,
            'playlists': [playlist.to_dict() for playlist in playlists]
        })
    except Exception as e:
        logging.error(f"プレイリスト取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/playlists', methods=['POST'])
@login_required
def api_create_playlist():
    """プレイリスト作成"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        is_public = data.get('is_public', False)
        
        if not name:
            return jsonify({'success': False, 'error': 'プレイリスト名を入力してください。'}), 400
        
        if len(name) > 100:
            return jsonify({'success': False, 'error': 'プレイリスト名は100文字以内で入力してください。'}), 400
        
        playlist = Playlist(
            name=name,
            description=description,
            user_id=current_user.id,
            is_public=is_public
        )
        
        db.session.add(playlist)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'プレイリストが作成されました。',
            'playlist': playlist.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"プレイリスト作成エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/playlists/<int:playlist_id>', methods=['PUT'])
@login_required
def api_update_playlist(playlist_id):
    """プレイリスト更新"""
    try:
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
        if not playlist:
            return jsonify({'success': False, 'error': 'プレイリストが見つかりません。'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'success': False, 'error': 'プレイリスト名を入力してください。'}), 400
            if len(name) > 100:
                return jsonify({'success': False, 'error': 'プレイリスト名は100文字以内で入力してください。'}), 400
            playlist.name = name
        
        if 'description' in data:
            playlist.description = data['description'].strip()
        
        if 'is_public' in data:
            playlist.is_public = data['is_public']
        
        playlist.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'プレイリストが更新されました。',
            'playlist': playlist.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"プレイリスト更新エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/playlists/<int:playlist_id>', methods=['DELETE'])
@login_required
def api_delete_playlist(playlist_id):
    """プレイリスト削除"""
    try:
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
        if not playlist:
            return jsonify({'success': False, 'error': 'プレイリストが見つかりません。'}), 404
        
        db.session.delete(playlist)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'プレイリストが削除されました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"プレイリスト削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/playlists/<int:playlist_id>/videos', methods=['POST'])
@login_required
def api_add_video_to_playlist(playlist_id):
    """プレイリストに動画を追加"""
    try:
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
        if not playlist:
            return jsonify({'success': False, 'error': 'プレイリストが見つかりません。'}), 404
        
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        title = data.get('title', '').strip()
        thumbnail_url = data.get('thumbnail_url', '')
        duration = data.get('duration', 0)
        uploader = data.get('uploader', '').strip()
        
        if not video_id or not title:
            return jsonify({'success': False, 'error': '動画IDとタイトルは必須です。'}), 400
        
        # 重複チェック
        existing_video = PlaylistVideo.query.filter_by(
            playlist_id=playlist_id, 
            video_id=video_id
        ).first()
        
        if existing_video:
            return jsonify({'success': False, 'error': 'この動画は既にプレイリストに追加されています。'}), 400
        
        # 位置を決定（最後に追加）
        max_position = db.session.query(func.max(PlaylistVideo.position)).filter_by(playlist_id=playlist_id).scalar() or 0
        
        playlist_video = PlaylistVideo(
            playlist_id=playlist_id,
            video_id=video_id,
            title=title,
            thumbnail_url=thumbnail_url,
            duration=duration,
            uploader=uploader,
            position=max_position + 1
        )
        
        db.session.add(playlist_video)
        playlist.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'プレイリストに動画を追加しました。',
            'video': playlist_video.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"プレイリスト動画追加エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/playlists/<int:playlist_id>/videos/<int:video_id>', methods=['DELETE'])
@login_required
def api_remove_video_from_playlist(playlist_id, video_id):
    """プレイリストから動画を削除"""
    try:
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
        if not playlist:
            return jsonify({'success': False, 'error': 'プレイリストが見つかりません。'}), 404
        
        playlist_video = PlaylistVideo.query.filter_by(id=video_id, playlist_id=playlist_id).first()
        if not playlist_video:
            return jsonify({'success': False, 'error': '動画が見つかりません。'}), 404
        
        db.session.delete(playlist_video)
        playlist.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'プレイリストから動画を削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"プレイリスト動画削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# 視聴履歴
# =============================================================================

@backend.route('/api/watch-history', methods=['GET'])
@login_required
def api_get_watch_history():
    """視聴履歴を取得"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        history = WatchHistory.query.filter_by(user_id=current_user.id)\
            .order_by(desc(WatchHistory.watched_at))\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'history': [item.to_dict() for item in history.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': history.total,
                'pages': history.pages,
                'has_next': history.has_next,
                'has_prev': history.has_prev
            }
        })
        
    except Exception as e:
        logging.error(f"視聴履歴取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/watch-history', methods=['POST'])
@login_required
def api_add_watch_history():
    """視聴履歴を追加"""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        title = data.get('title', '').strip()
        thumbnail_url = data.get('thumbnail_url', '')
        uploader = data.get('uploader', '').strip()
        watch_duration = data.get('watch_duration', 0)
        total_duration = data.get('total_duration', 0)
        
        if not video_id or not title:
            return jsonify({'success': False, 'error': '動画IDとタイトルは必須です。'}), 400
        
        # 既存の履歴があれば更新、なければ新規作成
        history = WatchHistory.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        
        if history:
            history.watched_at = datetime.utcnow()
            history.watch_duration = watch_duration
            history.total_duration = total_duration
        else:
            history = WatchHistory(
                user_id=current_user.id,
                video_id=video_id,
                title=title,
                thumbnail_url=thumbnail_url,
                uploader=uploader,
                watch_duration=watch_duration,
                total_duration=total_duration
            )
            db.session.add(history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '視聴履歴を記録しました。',
            'history': history.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"視聴履歴追加エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/watch-history/<string:video_id>', methods=['DELETE'])
@login_required
def api_delete_watch_history(video_id):
    """視聴履歴を削除"""
    try:
        history = WatchHistory.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        if not history:
            return jsonify({'success': False, 'error': '視聴履歴が見つかりません。'}), 404
        
        db.session.delete(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '視聴履歴を削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"視聴履歴削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/watch-history/clear', methods=['DELETE'])
@login_required
def api_clear_watch_history():
    """視聴履歴を全削除"""
    try:
        WatchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '視聴履歴を全て削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"視聴履歴全削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# お気に入り機能
# =============================================================================

@backend.route('/api/favorites', methods=['GET'])
@login_required
def api_get_favorites():
    """お気に入り一覧を取得"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        favorites = Favorite.query.filter_by(user_id=current_user.id)\
            .order_by(desc(Favorite.added_at))\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'favorites': [favorite.to_dict() for favorite in favorites.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': favorites.total,
                'pages': favorites.pages,
                'has_next': favorites.has_next,
                'has_prev': favorites.has_prev
            }
        })
        
    except Exception as e:
        logging.error(f"お気に入り取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/favorites', methods=['POST'])
@login_required
def api_add_favorite():
    """お気に入りに追加"""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        title = data.get('title', '').strip()
        thumbnail_url = data.get('thumbnail_url', '')
        uploader = data.get('uploader', '').strip()
        
        if not video_id or not title:
            return jsonify({'success': False, 'error': '動画IDとタイトルは必須です。'}), 400
        
        # 重複チェック
        existing_favorite = Favorite.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        if existing_favorite:
            return jsonify({'success': False, 'error': 'この動画は既にお気に入りに追加されています。'}), 400
        
        favorite = Favorite(
            user_id=current_user.id,
            video_id=video_id,
            title=title,
            thumbnail_url=thumbnail_url,
            uploader=uploader
        )
        
        db.session.add(favorite)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'お気に入りに追加しました。',
            'favorite': favorite.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"お気に入り追加エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/favorites/<string:video_id>', methods=['DELETE'])
@login_required
def api_remove_favorite(video_id):
    """お気に入りから削除"""
    try:
        favorite = Favorite.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        if not favorite:
            return jsonify({'success': False, 'error': 'お気に入りが見つかりません。'}), 404
        
        db.session.delete(favorite)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'お気に入りから削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"お気に入り削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/favorites/status/<string:video_id>', methods=['GET'])
@login_required
def api_check_favorite_status(video_id):
    """お気に入り状態をチェック"""
    try:
        favorite = Favorite.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        return jsonify({
            'success': True,
            'is_favorite': favorite is not None
        })
        
    except Exception as e:
        logging.error(f"お気に入り状態チェックエラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# 評価機能
# =============================================================================

@backend.route('/api/ratings', methods=['POST'])
@login_required
def api_rate_video():
    """動画を評価（いいね/よくない）"""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        rating = data.get('rating', '').strip()  # 'like' or 'dislike'
        
        if not video_id:
            return jsonify({'success': False, 'error': '動画IDは必須です。'}), 400
        
        if rating not in ['like', 'dislike']:
            return jsonify({'success': False, 'error': '評価は"like"または"dislike"で指定してください。'}), 400
        
        # 既存の評価があれば更新、なければ新規作成
        existing_rating = Rating.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        
        if existing_rating:
            if existing_rating.rating == rating:
                # 同じ評価なら削除（取り消し）
                db.session.delete(existing_rating)
                message = '評価を取り消しました。'
                current_rating = None
            else:
                # 異なる評価なら更新
                existing_rating.rating = rating
                existing_rating.created_at = datetime.utcnow()
                message = f'評価を{"いいね" if rating == "like" else "よくない"}に変更しました。'
                current_rating = rating
        else:
            # 新規評価
            new_rating = Rating(
                user_id=current_user.id,
                video_id=video_id,
                rating=rating
            )
            db.session.add(new_rating)
            message = f'{"いいね" if rating == "like" else "よくない"}を追加しました。'
            current_rating = rating
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'current_rating': current_rating
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"評価エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/ratings/<string:video_id>', methods=['GET'])
@login_required
def api_get_video_rating(video_id):
    """動画の評価状態を取得"""
    try:
        rating = Rating.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        return jsonify({
            'success': True,
            'rating': rating.rating if rating else None
        })
        
    except Exception as e:
        logging.error(f"評価取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/api/favorites/toggle', methods=['POST'])
@login_required
def api_toggle_favorite():
    """お気に入りの切り替え（追加/削除）"""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        title = data.get('title', '').strip()
        thumbnail_url = data.get('thumbnail_url', '')
        uploader = data.get('uploader', '')
        
        if not video_id or not title:
            return jsonify({'success': False, 'error': '動画IDとタイトルは必須です。'}), 400
        
        # 既存のお気に入りをチェック
        existing_favorite = Favorite.query.filter_by(user_id=current_user.id, video_id=video_id).first()
        
        if existing_favorite:
            # 削除
            db.session.delete(existing_favorite)
            message = 'お気に入りから削除しました'
            is_favorite = False
        else:
            # 追加
            favorite = Favorite(
                user_id=current_user.id,
                video_id=video_id,
                title=title,
                thumbnail_url=thumbnail_url,
                uploader=uploader
            )
            db.session.add(favorite)
            message = 'お気に入りに追加しました'
            is_favorite = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'is_favorite': is_favorite
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"お気に入り切り替えエラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@backend.route('/liked-videos')
@login_required
def liked_videos():
    """評価した動画ページ"""
    try:
        page = request.args.get('page', 1, type=int)
        
        # いいねした動画を取得
        liked_ratings = Rating.query.filter_by(
            user_id=current_user.id, 
            rating='like'
        ).order_by(Rating.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('liked_videos.html', 
                             liked_ratings=liked_ratings,
                             page=page)
        
    except Exception as e:
        logging.error(f"評価した動画取得エラー: {e}")
        return render_template('liked_videos.html', 
                             liked_ratings=None, 
                             error="評価した動画を取得できませんでした。")

