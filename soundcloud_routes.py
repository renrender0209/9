from flask import Blueprint, request, jsonify, render_template
import requests
import logging
from functools import wraps
from invidious_service import InvidiousService

soundcloud_bp = Blueprint('soundcloud', __name__, url_prefix='/soundcloud')

# Invidious サービスを使用してYouTube Music機能を提供
invidious_service = InvidiousService()

def handle_service_error(f):
    """音楽サービスのエラーを処理するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"音楽サービスエラー: {str(e)}")
            return jsonify({
                'error': 'サービスエラーが発生しました',
                'tracks': [],
                'total': 0
            }), 500
    return decorated_function

@soundcloud_bp.route('/')
def soundcloud_home():
    """SoundCloud音楽ストリーミングホームページ"""
    return render_template('soundcloud/home.html')

@soundcloud_bp.route('/search')
@handle_service_error
def soundcloud_search():
    """音楽検索ページ（YouTube Music経由）"""
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    limit = 20
    
    tracks = []
    total = 0
    has_more = False
    
    if query:
        # 音楽関連の検索キーワードを追加して精度を向上
        music_query = f"{query} music song audio"
        search_results = invidious_service.search_videos(music_query, page)
        
        if search_results:
            # Invidiousの検索結果は直接リストで返される
            videos = search_results if isinstance(search_results, list) else []
            
            # 音楽コンテンツをフィルタリング
            for video in videos[:limit]:
                duration = video.get('lengthSeconds', 0)
                # 30秒以上20分以下の動画を音楽として扱う
                if 30 <= duration <= 1200:
                    tracks.append({
                        'id': video.get('videoId'),
                        'title': video.get('title', ''),
                        'artist': video.get('author', 'Unknown Artist'),
                        'duration': duration,
                        'artwork_url': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                        'permalink_url': f"https://youtube.com/watch?v={video.get('videoId')}",
                        'playback_count': video.get('viewCount', 0),
                        'likes_count': 0,
                        'genre': 'Music',
                        'tag_list': '',
                        'created_at': '',
                        'description': video.get('description', '')
                    })
            
            total = len(tracks)
            has_more = len(videos) >= limit
    
    return render_template('soundcloud/search.html', 
                         query=query, 
                         tracks=tracks, 
                         total=total,
                         page=page,
                         has_more=has_more)

@soundcloud_bp.route('/trending')
@handle_service_error
def soundcloud_trending():
    """トレンド音楽ページ（YouTube Music経由）"""
    genre = request.args.get('genre', '')
    
    # YouTube Musicのトレンドを取得
    trending_videos = invidious_service.get_trending_videos(region='JP')
    tracks = []
    
    if trending_videos and 'videos' in trending_videos:
        videos = trending_videos['videos']
        
        # 音楽コンテンツをフィルタリング
        for video in videos:
            duration = video.get('lengthSeconds', 0)
            title = video.get('title', '').lower()
            
            # 音楽関連キーワードで判定し、30秒以上20分以下の動画を音楽として扱う
            is_music = any(keyword in title for keyword in ['music', 'song', 'mv', 'official', 'audio', '歌', '音楽', 'ミュージック'])
            
            if is_music and 30 <= duration <= 1200:
                tracks.append({
                    'id': video.get('videoId'),
                    'title': video.get('title', ''),
                    'artist': video.get('author', 'Unknown Artist'),
                    'duration': duration,
                    'artwork_url': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                    'permalink_url': f"https://youtube.com/watch?v={video.get('videoId')}",
                    'playback_count': video.get('viewCount', 0),
                    'likes_count': 0,
                    'genre': 'Music',
                    'tag_list': '',
                    'created_at': '',
                    'description': video.get('description', '')
                })
                
                # 最大30件まで
                if len(tracks) >= 30:
                    break
    
    return render_template('soundcloud/trending.html', 
                         tracks=tracks, 
                         genre=genre)

# API エンドポイント
@soundcloud_bp.route('/api/search')
@handle_service_error
def api_soundcloud_search():
    """音楽検索API（YouTube Music経由）"""
    query = request.args.get('q')
    limit = int(request.args.get('limit', 20))
    
    if not query:
        return jsonify({'error': '検索クエリが必要です', 'tracks': [], 'total': 0}), 400
    
    music_query = f"{query} music song audio"
    search_results = invidious_service.search_videos(music_query, 1)
    tracks = []
    
    if search_results and 'videos' in search_results:
        videos = search_results['videos']
        
        for video in videos[:limit]:
            duration = video.get('lengthSeconds', 0)
            if 30 <= duration <= 1200:
                tracks.append({
                    'id': video.get('videoId'),
                    'title': video.get('title', ''),
                    'artist': video.get('author', 'Unknown Artist'),
                    'duration': duration,
                    'artwork_url': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                    'permalink_url': f"https://youtube.com/watch?v={video.get('videoId')}",
                    'playback_count': video.get('viewCount', 0),
                    'likes_count': 0,
                    'genre': 'Music',
                    'created_at': '',
                    'description': video.get('description', '')
                })
    
    return jsonify({'tracks': tracks, 'total': len(tracks), 'query': query})

@soundcloud_bp.route('/api/track/<track_id>')
@handle_service_error
def api_soundcloud_track(track_id):
    """楽曲情報API（YouTube経由）"""
    video_info = invidious_service.get_video_info(track_id)
    
    if video_info:
        track_data = {
            'id': video_info.get('videoId'),
            'title': video_info.get('title', ''),
            'artist': video_info.get('author', 'Unknown Artist'),
            'duration': video_info.get('lengthSeconds', 0),
            'artwork_url': f"https://img.youtube.com/vi/{track_id}/hqdefault.jpg",
            'permalink_url': f"https://youtube.com/watch?v={track_id}",
            'playback_count': video_info.get('viewCount', 0),
            'likes_count': video_info.get('likeCount', 0),
            'genre': 'Music',
            'description': video_info.get('description', '')
        }
        return jsonify(track_data)
    else:
        return jsonify({'error': '楽曲が見つかりません'}), 404

@soundcloud_bp.route('/api/trending')
@handle_service_error
def api_soundcloud_trending():
    """トレンドAPI（YouTube Music経由）"""
    genre = request.args.get('genre', '')
    limit = int(request.args.get('limit', 20))
    
    trending_videos = invidious_service.get_trending_videos(region='JP')
    tracks = []
    
    if trending_videos and 'videos' in trending_videos:
        videos = trending_videos['videos']
        
        for video in videos:
            duration = video.get('lengthSeconds', 0)
            title = video.get('title', '').lower()
            
            is_music = any(keyword in title for keyword in ['music', 'song', 'mv', 'official', 'audio', '歌', '音楽', 'ミュージック'])
            
            if is_music and 30 <= duration <= 1200:
                tracks.append({
                    'id': video.get('videoId'),
                    'title': video.get('title', ''),
                    'artist': video.get('author', 'Unknown Artist'),
                    'duration': duration,
                    'artwork_url': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                    'permalink_url': f"https://youtube.com/watch?v={video.get('videoId')}",
                    'playback_count': video.get('viewCount', 0),
                    'likes_count': 0,
                    'genre': 'Music'
                })
                
                if len(tracks) >= limit:
                    break
    
    return jsonify({'tracks': tracks, 'total': len(tracks), 'genre': genre})

@soundcloud_bp.route('/api/embed/<track_id>')
@handle_service_error
def api_soundcloud_embed(track_id):
    """埋め込みURL取得API（YouTube経由）"""
    embed_url = f"https://www.youtube.com/embed/{track_id}?autoplay=1&controls=1&rel=0"
    return jsonify({'embedUrl': embed_url})

@soundcloud_bp.route('/player/<track_id>')
@handle_service_error
def soundcloud_player(track_id):
    """音楽プレイヤーページ（YouTube経由）"""
    video_info = invidious_service.get_video_info(track_id)
    track = None
    embed_url = None
    
    if video_info:
        track = {
            'id': video_info.get('videoId'),
            'title': video_info.get('title', ''),
            'artist': video_info.get('author', 'Unknown Artist'),
            'duration': video_info.get('lengthSeconds', 0),
            'artwork_url': f"https://img.youtube.com/vi/{track_id}/hqdefault.jpg",
            'permalink_url': f"https://youtube.com/watch?v={track_id}",
            'description': video_info.get('description', '')
        }
        embed_url = f"https://www.youtube.com/embed/{track_id}?autoplay=1&controls=1&rel=0"
    
    return render_template('soundcloud/player.html', 
                         track=track, 
                         track_id=track_id,
                         embed_url=embed_url)