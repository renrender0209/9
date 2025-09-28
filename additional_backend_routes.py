from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Comment, Notification, SearchHistory, Download, WatchHistory, Favorite, Playlist, Rating
from vkr_downloader_service import OmadaVideoService
from multi_stream_service import MultiStreamService
from invidious_instances import invidious_manager
from datetime import datetime, timedelta
from sqlalchemy import desc, or_, func
import logging
import time

additional = Blueprint('additional', __name__)

# Omada Video サービスのインスタンス
video_service = OmadaVideoService()

# Multi Stream サービスのインスタンス
multi_stream_service = MultiStreamService()

# =============================================================================
# コメント機能
# =============================================================================

@additional.route('/api/comments/<string:video_id>', methods=['GET'])
def api_get_comments(video_id):
    """動画のコメントを取得（ログイン不要）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        comments = Comment.query.filter_by(video_id=video_id, is_deleted=False)\
            .order_by(desc(Comment.created_at))\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'comments': [comment.to_dict() for comment in comments.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': comments.total,
                'pages': comments.pages,
                'has_next': comments.has_next,
                'has_prev': comments.has_prev
            }
        })
        
    except Exception as e:
        logging.error(f"コメント取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# 通知システム
# =============================================================================

@additional.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    """通知一覧を取得"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        query = Notification.query.filter_by(user_id=current_user.id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(desc(Notification.created_at))\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'notifications': [notification.to_dict() for notification in notifications.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': notifications.total,
                'pages': notifications.pages,
                'has_next': notifications.has_next,
                'has_prev': notifications.has_prev
            },
            'unread_count': Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        })
        
    except Exception as e:
        logging.error(f"通知取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    """通知を既読にする"""
    try:
        notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
        if not notification:
            return jsonify({'success': False, 'error': '通知が見つかりません。'}), 404
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '通知を既読にしました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"通知既読エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    """全ての通知を既読にする"""
    try:
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '全ての通知を既読にしました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"全通知既読エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@login_required
def api_delete_notification(notification_id):
    """通知を削除"""
    try:
        notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
        if not notification:
            return jsonify({'success': False, 'error': '通知が見つかりません。'}), 404
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '通知を削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"通知削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# 検索履歴
# =============================================================================

@additional.route('/api/search-history', methods=['GET'])
@login_required
def api_get_search_history():
    """検索履歴を取得"""
    try:
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        history = SearchHistory.query.filter_by(user_id=current_user.id)\
            .order_by(desc(SearchHistory.searched_at))\
            .limit(limit).all()
        
        return jsonify({
            'success': True,
            'history': [item.to_dict() for item in history]
        })
        
    except Exception as e:
        logging.error(f"検索履歴取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/search-history', methods=['POST'])
@login_required
def api_add_search_history():
    """検索履歴を追加"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        results_count = data.get('results_count', 0)
        
        if not query:
            return jsonify({'success': False, 'error': '検索クエリは必須です。'}), 400
        
        if len(query) > 200:
            return jsonify({'success': False, 'error': '検索クエリは200文字以内で入力してください。'}), 400
        
        # 既存の同じクエリがあれば削除（重複を避ける）
        SearchHistory.query.filter_by(user_id=current_user.id, query=query).delete()
        
        # 新しい検索履歴を追加
        search_history = SearchHistory(
            user_id=current_user.id,
            query=query,
            results_count=results_count
        )
        
        db.session.add(search_history)
        
        # 古い検索履歴を削除（最新100件のみ保持）
        old_searches = SearchHistory.query.filter_by(user_id=current_user.id)\
            .order_by(desc(SearchHistory.searched_at))\
            .offset(100).all()
        
        for old_search in old_searches:
            db.session.delete(old_search)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '検索履歴を記録しました。',
            'history': search_history.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"検索履歴追加エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/search-history/<int:history_id>', methods=['DELETE'])
@login_required
def api_delete_search_history(history_id):
    """検索履歴を削除"""
    try:
        history = SearchHistory.query.filter_by(id=history_id, user_id=current_user.id).first()
        if not history:
            return jsonify({'success': False, 'error': '検索履歴が見つかりません。'}), 404
        
        db.session.delete(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '検索履歴を削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"検索履歴削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/search-history/clear', methods=['DELETE'])
@login_required
def api_clear_search_history():
    """検索履歴を全削除"""
    try:
        SearchHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '検索履歴を全て削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"検索履歴全削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# ダウンロード機能
# =============================================================================

@additional.route('/api/downloads', methods=['GET'])
@login_required
def api_get_downloads():
    """ダウンロード履歴を取得"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')  # pending, processing, completed, failed
        
        query = Download.query.filter_by(user_id=current_user.id)
        
        if status:
            query = query.filter_by(status=status)
        
        downloads = query.order_by(desc(Download.created_at))\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'downloads': [download.to_dict() for download in downloads.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': downloads.total,
                'pages': downloads.pages,
                'has_next': downloads.has_next,
                'has_prev': downloads.has_prev
            }
        })
        
    except Exception as e:
        logging.error(f"ダウンロード履歴取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/downloads', methods=['POST'])
@login_required
def api_request_download():
    """ダウンロードをリクエスト"""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        title = data.get('title', '').strip()
        quality = data.get('quality', '720p')
        format_type = data.get('format', 'mp4')  # mp4, webm, mp3
        
        if not video_id or not title:
            return jsonify({'success': False, 'error': '動画IDとタイトルは必須です。'}), 400
        
        if quality not in ['360p', '480p', '720p', '1080p', 'best']:
            return jsonify({'success': False, 'error': '無効な品質設定です。'}), 400
        
        if format_type not in ['mp4', 'webm', 'mp3']:
            return jsonify({'success': False, 'error': '無効なフォーマットです。'}), 400
        
        # 既存の同じダウンロードリクエストがあるかチェック
        existing_download = Download.query.filter_by(
            user_id=current_user.id,
            video_id=video_id,
            quality=quality,
            format=format_type,
            status='pending'
        ).first()
        
        if existing_download:
            return jsonify({
                'success': True,
                'message': '同じダウンロードリクエストが既に存在します。',
                'download': existing_download.to_dict()
            })
        
        download = Download(
            user_id=current_user.id,
            video_id=video_id,
            title=title,
            quality=quality,
            format=format_type,
            status='pending'
        )
        
        db.session.add(download)
        db.session.commit()
        
        # 実際のダウンロード処理はバックグラウンドタスクで実行
        # （この例では処理をスキップし、ステータスのみ管理）
        
        return jsonify({
            'success': True,
            'message': 'ダウンロードリクエストを受け付けました。',
            'download': download.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"ダウンロードリクエストエラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/downloads/<int:download_id>', methods=['DELETE'])
@login_required
def api_delete_download(download_id):
    """ダウンロード履歴を削除"""
    try:
        download = Download.query.filter_by(id=download_id, user_id=current_user.id).first()
        if not download:
            return jsonify({'success': False, 'error': 'ダウンロード履歴が見つかりません。'}), 404
        
        db.session.delete(download)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'ダウンロード履歴を削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"ダウンロード履歴削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/downloads/clear', methods=['DELETE'])
@login_required
def api_clear_downloads():
    """ダウンロード履歴を全削除"""
    try:
        Download.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'ダウンロード履歴を全て削除しました。'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"ダウンロード履歴全削除エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# 統計・分析
# =============================================================================

@additional.route('/api/stats', methods=['GET'])
@login_required
def api_get_user_stats():
    """ユーザーの利用統計を取得"""
    try:
        from models import WatchHistory, Favorite, Playlist, Rating
        
        # 各種統計を取得
        stats = {
            'total_watch_time': db.session.query(func.sum(WatchHistory.watch_duration))\
                .filter_by(user_id=current_user.id).scalar() or 0,
            'videos_watched': WatchHistory.query.filter_by(user_id=current_user.id).count(),
            'favorites_count': Favorite.query.filter_by(user_id=current_user.id).count(),
            'playlists_count': Playlist.query.filter_by(user_id=current_user.id).count(),
            'comments_count': Comment.query.filter_by(user_id=current_user.id, is_deleted=False).count(),
            'likes_given': Rating.query.filter_by(user_id=current_user.id, rating='like').count(),
            'dislikes_given': Rating.query.filter_by(user_id=current_user.id, rating='dislike').count(),
        }
        
        # 今週の視聴時間
        week_ago = datetime.utcnow() - timedelta(days=7)
        stats['this_week_watch_time'] = db.session.query(func.sum(WatchHistory.watch_duration))\
            .filter(WatchHistory.user_id == current_user.id, WatchHistory.watched_at >= week_ago)\
            .scalar() or 0
        
        # 今月の視聴時間
        month_ago = datetime.utcnow() - timedelta(days=30)
        stats['this_month_watch_time'] = db.session.query(func.sum(WatchHistory.watch_duration))\
            .filter(WatchHistory.user_id == current_user.id, WatchHistory.watched_at >= month_ago)\
            .scalar() or 0
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logging.error(f"統計取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# YouTube Education エラーコード5対策機能
# =============================================================================

@additional.route('/api/youtube-education-status', methods=['GET'])
def api_youtube_education_status():
    """YouTube Education URLキャッシュ状況確認API"""
    try:
        from multi_stream_service import MultiStreamService
        
        service = MultiStreamService()
        
        # キャッシュ状況の確認
        cache_info = {}
        if hasattr(service, 'edu_base_url_cache') and service.edu_base_url_cache:
            cache_key = "edu_base_url"
            if cache_key in service.edu_base_url_cache:
                cached_url, timestamp = service.edu_base_url_cache[cache_key]
                current_time = time.time()
                age_hours = (current_time - timestamp) / 3600
                cache_info = {
                    'cached_url': cached_url,
                    'cached_timestamp': timestamp,
                    'age_hours': round(age_hours, 2),
                    'expires_in_hours': round((service.edu_base_url_cache_timeout - (current_time - timestamp)) / 3600, 2),
                    'is_expired': (current_time - timestamp) >= service.edu_base_url_cache_timeout
                }
            
        return jsonify({
            'success': True,
            'cache_info': cache_info,
            'default_url': service.default_edu_base_url,
            'cache_timeout_hours': service.edu_base_url_cache_timeout / 3600
        })
        
    except Exception as e:
        logging.error(f"YouTube Education状況確認エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/youtube-education-refresh', methods=['POST'])
def api_youtube_education_refresh():
    """YouTube Education ベースURLキャッシュを強制更新"""
    try:
        from multi_stream_service import MultiStreamService
        
        service = MultiStreamService()
        
        # キャッシュをクリアして強制取得
        if hasattr(service, 'edu_base_url_cache'):
            service.edu_base_url_cache.clear()
        
        # 新しいベースURLを取得
        new_base_url = service._get_dynamic_edu_base_url()
        
        return jsonify({
            'success': True,
            'message': 'YouTube Education ベースURLを更新しました',
            'new_base_url': new_base_url
        })
        
    except Exception as e:
        logging.error(f"YouTube Education強制更新エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@additional.route('/api/edu-url-force-refresh', methods=['POST'])
def api_edu_url_force_refresh():
    """YouTube Education URLの強制リフレッシュ（定期更新用）"""
    try:
        from multi_stream_service import MultiStreamService
        
        service = MultiStreamService()
        
        # キャッシュをクリア
        if hasattr(service, 'edu_base_url_cache'):
            service.edu_base_url_cache.clear()
            logging.info("🔄 YouTube Education URLキャッシュを強制クリア")
        
        # 固定サンプル動画でベースURLを取得
        logging.info(f"定期更新: {service.edu_refresh_sample_video} でリフレッシュ開始")
        new_base_url = service.get_youtube_education_base_url()
        
        return jsonify({
            'status': 'success',
            'message': f'YouTube Education URLを定期更新しました (サンプル: {service.edu_refresh_sample_video})',
            'new_base_url': new_base_url,
            'refresh_time': time.time(),
            'sample_video_used': service.edu_refresh_sample_video
        })
        
    except Exception as e:
        logging.error(f"定期リフレッシュエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'定期リフレッシュに失敗しました: {str(e)}'
        }), 500

@additional.route('/api/kahoot-key-test', methods=['GET'])
def api_kahoot_key_test():
    """Kahoot APIキー取得テスト"""
    try:
        from multi_stream_service import MultiStreamService
        
        service = MultiStreamService()
        video_id = request.args.get('video_id', 'dQw4w9WgXcQ')
        
        # Kahoot キーを取得してテスト
        kahoot_key = service._get_kahoot_youtube_key()
        
        if kahoot_key:
            # Kahoot方式でURLを生成
            kahoot_url = service._generate_youtube_education_url_with_kahoot(video_id)
            
            return jsonify({
                'status': 'success',
                'kahoot_key': kahoot_key[:20] + '...' if len(kahoot_key) > 20 else kahoot_key,
                'generated_url': kahoot_url,
                'video_id': video_id,
                'message': 'Kahoot方式でのURL生成に成功しました'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Kahoot APIからキーを取得できませんでした'
            }), 500
            
    except Exception as e:
        logging.error(f"Kahoot キーテストエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Kahoot キーテストに失敗しました: {str(e)}'
        }), 500

# =============================================================================
# VKR Downloader API
# =============================================================================

@additional.route('/api/vkr-stream/<string:video_id>', methods=['GET'])
def api_get_vkr_stream(video_id):
    """VKR APIから多品質動画・音声ストリームURLを取得"""
    try:
        logging.info(f"🚀 VKR API 多品質ストリーム取得開始: {video_id}")
        
        # YouTube URLを構築
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # すべての品質を取得（360p, 480p, 720p, 1080p）
        target_qualities = ['360p', '480p', '720p', '1080p']
        
        # yt.omada.cafe APIから多品質ストリームデータを取得
        result = video_service.get_stream_urls(youtube_url, target_qualities)
        
        if not result or not result.get('success'):
            logging.warning(f"VKR API: 多品質ストリームデータを取得できませんでした: {video_id}")
            return jsonify({
                'success': False,
                'error': '多品質ストリームデータを取得できませんでした'
            }), 404
        
        # 利用可能な品質をフィルタリング
        available_qualities = {}
        for quality in target_qualities:
            quality_data = result['quality_streams'].get(quality, {})
            if quality_data.get('video_url') or quality_data.get('combined_url'):
                available_qualities[quality] = quality_data
                logging.info(f"✅ 品質 {quality} 追加済み")
            else:
                logging.info(f"❌ 品質 {quality} スキップ（URLなし）")
        
        # YouTube Education URL生成（/api/<video_id>エンドポイントと同じ方法を使用）
        try:
            youtube_education_url = multi_stream_service.get_direct_youtube_embed_url(video_id, "education")
            logging.info(f"✅ YouTube Education URL生成成功: {youtube_education_url[:100]}...")
        except Exception as e:
            logging.warning(f"⚠️ YouTube Education URL生成失敗、フォールバック使用: {e}")
            youtube_education_url = f"https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&controls=1&rel=0"
        
        youtube_education_urls = {
            "education": youtube_education_url,
            "nocookie": f"https://www.youtube-nocookie.com/embed/{video_id}",
            "education_autoplay": f"https://www.youtube.com/embed/{video_id}?rel=0&showinfo=0&modestbranding=1&autoplay=1",
            "education_playlist": f"https://www.youtube.com/embed/{video_id}?rel=0&showinfo=0&modestbranding=1&playlist={video_id}&loop=1"
        }
        
        # フロントエンドが期待するvideo_stream, audio_stream, combined_streamフィールドを追加
        video_stream = None
        audio_stream = None
        combined_stream = None
        
        # 最高品質（1080p → 720p → 480p → 360p の順）でストリームを選択
        for quality in ['1080p', '720p', '480p', '360p']:
            if quality in available_qualities:
                quality_data = available_qualities[quality]
                if quality_data.get('video_url'):
                    video_stream = {
                        'url': quality_data['video_url'],
                        'quality': quality,
                        'container': 'mp4',
                        'has_audio': quality_data.get('has_audio', False)
                    }
                    break
        
        # 音声ストリーム（best_audioから取得）
        if result.get('best_audio'):
            audio_stream = {
                'url': result['best_audio'].get('url', ''),
                'bitrate': result['best_audio'].get('bitrate', ''),
                'container': result['best_audio'].get('container', 'webm')
            }
        
        # 結合ストリーム（360pの combined_url を優先）
        if '360p' in available_qualities and available_qualities['360p'].get('combined_url'):
            combined_stream = {
                'url': available_qualities['360p']['combined_url'],
                'quality': '360p',
                'container': 'mp4',
                'has_audio': True
            }
        
        # 360p は combined_url（音声付き）、その他は video_url と audio_url を分離
        response = {
            'success': True,
            'videoId': result.get('videoId'),
            'title': result.get('title'),
            'thumbnail': result.get('thumbnail'),
            'description': result.get('description'),
            'author': result.get('author'),
            'authorId': result.get('authorId'),  # チャンネルID
            'authorUrl': result.get('authorUrl'),  # チャンネルURL
            'authorThumbnails': result.get('authorThumbnails', []),  # チャンネルアイコン
            'viewCount': result.get('viewCount'),
            'lengthSeconds': result.get('lengthSeconds'),
            'publishedText': result.get('publishedText'),
            'multi_quality': True,
            'quality_streams': available_qualities,
            'best_audio': result.get('best_audio'),
            'available_qualities': list(available_qualities.keys()),
            'youtube_education': youtube_education_urls,
            'source': 'yt.omada.cafe',
            # フロントエンドが期待するフィールドを追加
            'video_stream': video_stream,
            'audio_stream': audio_stream,
            'combined_stream': combined_stream
        }
        
        logging.info(f"✅ VKR API 多品質ストリーム取得成功: {video_id}")
        logging.info(f"   利用可能品質: {list(available_qualities.keys())}")
        logging.info(f"   チャンネル: {result.get('author', 'Unknown')}")
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"VKR API 多品質エラー: {e}")
        return jsonify({
            'success': False,
            'error': f'VKR API 多品質エラー: {str(e)}'
        }), 500

@additional.route('/api/vkr-test', methods=['GET'])
def api_vkr_test():
    """VKR API接続テスト"""
    try:
        # テスト用のYouTube動画ID
        test_video_id = request.args.get('video_id', 'gQ7l_hav-bA')  # 桜坂46 Alter ego
        youtube_url = f"https://www.youtube.com/watch?v={test_video_id}"
        
        logging.info(f"VKR API テスト開始: {test_video_id}")
        
        # Omada APIにリクエスト
        stream_data = video_service.get_stream_urls(youtube_url)
        
        if stream_data:
            # データ構造の確認
            data_info = {
                'has_data': 'data' in stream_data,
                'data_keys': list(stream_data.get('data', {}).keys()) if 'data' in stream_data else [],
                'downloads_count': len(stream_data.get('data', {}).get('downloads', [])),
                'sample_download': stream_data.get('data', {}).get('downloads', [{}])[0] if stream_data.get('data', {}).get('downloads') else None
            }
            
            return jsonify({
                'status': 'success',
                'message': 'VKR API接続成功',
                'test_video_id': test_video_id,
                'data_structure': data_info,
                'raw_response_keys': list(stream_data.keys())
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'VKR APIからデータを取得できませんでした',
                'test_video_id': test_video_id
            }), 500
            
    except Exception as e:
        logging.error(f"VKR API テストエラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'VKR API テストに失敗しました: {str(e)}'
        }), 500

# =============================================================================
# Invidious コメント機能
# =============================================================================

@additional.route('/api/invidious-comments/<string:video_id>', methods=['GET'])
def api_get_invidious_comments(video_id):
    """Invidiousインスタンスから動画コメントを取得"""
    try:
        logging.info(f"🚀 Invidiousコメント取得開始: {video_id}")
        
        # Invidiousインスタンスマネージャーからコメントを取得
        comments_data = invidious_manager.get_video_comments(video_id)
        
        if comments_data:
            comments = comments_data.get('comments', [])
            
            # コメントデータを標準形式にフォーマット
            formatted_comments = []
            for comment in comments:
                formatted_comment = {
                    'author': comment.get('author', ''),
                    'authorId': comment.get('authorId', ''),
                    'authorThumbnails': comment.get('authorThumbnails', []),
                    'content': comment.get('content', ''),
                    'publishedText': comment.get('publishedText', ''),
                    'likeCount': comment.get('likeCount', 0),
                    'replies': comment.get('replies', {}).get('replyCount', 0),
                    'isOwner': comment.get('authorIsChannelOwner', False),
                    'isPinned': comment.get('isPinned', False)
                }
                formatted_comments.append(formatted_comment)
            
            logging.info(f"✅ Invidiousコメント取得成功: {video_id} - {len(formatted_comments)}件")
            return jsonify({
                'success': True,
                'comments': formatted_comments,
                'total': len(formatted_comments),
                'continuation': comments_data.get('continuation'),
                'source': 'invidious'
            })
        else:
            logging.warning(f"Invidiousコメント取得失敗: {video_id}")
            return jsonify({
                'success': False,
                'error': 'Invidiousからコメントを取得できませんでした',
                'comments': []
            }), 404
            
    except Exception as e:
        logging.error(f"Invidiousコメント取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': f'Invidiousコメント取得エラー: {str(e)}',
            'comments': []
        }), 500

@additional.route('/api/invidious-trending', methods=['GET'])
def api_get_invidious_trending():
    """Invidiousインスタンスからトレンド動画を取得"""
    try:
        logging.info("🚀 Invidiousトレンド取得開始")
        
        trending_videos = invidious_manager.get_trending_videos()
        
        if trending_videos:
            logging.info(f"✅ Invidiousトレンド取得成功: {len(trending_videos)}件")
            return jsonify({
                'success': True,
                'trending': trending_videos,
                'total': len(trending_videos),
                'source': 'invidious'
            })
        else:
            logging.warning("Invidiousトレンド取得失敗")
            return jsonify({
                'success': False,
                'error': 'Invidiousからトレンド動画を取得できませんでした',
                'trending': []
            }), 404
            
    except Exception as e:
        logging.error(f"Invidiousトレンド取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': f'Invidiousトレンド取得エラー: {str(e)}',
            'trending': []
        }), 500