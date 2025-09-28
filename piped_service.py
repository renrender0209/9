import requests
import logging

class PipedService:
    def __init__(self):
        self.instances = [
            # 既存のPipedインスタンス
            "https://nyc1.piapi.ggtyler.dev",
            "https://pipedapi.adminforge.de",
            "https://cal1.piapi.ggtyler.dev",
            "https://pol1.piapi.ggtyler.dev",
            "https://piapi.ggtyler.dev",
            "https://pipedapi.drgns.space",
            "https://api.piped.private.coffee",
            "https://pipedapi.ducks.party",
            
            # 🚀 新しい高速Pipedインスタンス追加
            "https://pipedapi.palvelus.app",
            "https://api.piped.yt",
            "https://pipedapi.smnz.de",
            "https://pipedapi.rivo.lol",
            "https://api.piped.projectsegfau.lt",
            "https://api.piped.shimul.me",
            "https://api.piped.privacy.com.de",
            "https://api.piped.astartes.nl",
            "https://pipedapi.qdi.fi",
            "https://api.piped.tokhmi.xyz",
            "https://piped-api.hostux.net",
            "https://pipedapi.syncpundit.io"
        ]
        self.timeout = 3  # 高速化のためタイムアウト短縮
        
    def _make_request(self, endpoint, params=None):
        """複数のPipedインスタンスでリクエストを試行"""
        for instance in self.instances:
            try:
                url = f"{instance}/{endpoint}"
                response = requests.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    # データが辞書形式またはリストであることを確認
                    if isinstance(data, (dict, list)):
                        return data
                    else:
                        logging.warning(f"予期しないデータ形式（文字列）を受信: {instance} - {type(data)}")
                        continue
            except requests.RequestException as e:
                logging.warning(f"Piped instance {instance} failed: {e}")
                continue
        return None
    
    def search_videos(self, query, page=1):
        """動画検索"""
        try:
            # Pipedの検索は単純なクエリパラメータ
            endpoint = f'search?q={query}&filter=videos'
            data = self._make_request(endpoint)
            if not data or 'items' not in data:
                return []
            
            videos = []
            # Pipedのレスポンス形式に合わせて調整
            items = data if isinstance(data, list) else data.get('items', [])
            for item in items:
                if item.get('type') == 'stream' or item.get('url'):
                    video = {
                        'videoId': item.get('url', '').replace('/watch?v=', ''),
                        'title': item.get('title', ''),
                        'author': item.get('uploaderName', ''),
                        'authorId': item.get('uploaderUrl', '').replace('/channel/', ''),
                        'publishedText': self._format_duration(item.get('uploadedDate')),
                        'viewCount': item.get('views', 0),
                        'lengthSeconds': item.get('duration', 0),
                        'videoThumbnails': [{'url': item.get('thumbnail', '')}] if item.get('thumbnail') else []
                    }
                    videos.append(video)
            
            return videos[:20]  # 最大20件
            
        except Exception as e:
            logging.error(f"Piped search error: {e}")
            return []
    
    def get_video_info(self, video_id):
        """動画情報取得"""
        try:
            data = self._make_request(f'streams/{video_id}')
            if not data:
                return None
            
            return {
                'videoId': video_id,
                'title': data.get('title', ''),
                'author': data.get('uploader', ''),
                'description': data.get('description', ''),
                'viewCount': data.get('views', 0),
                'publishedText': data.get('uploadDate', ''),
                'lengthSeconds': data.get('duration', 0),
                'videoThumbnails': [{'url': data.get('thumbnailUrl', '')}] if data.get('thumbnailUrl') else []
            }
            
        except Exception as e:
            logging.error(f"Piped video info error: {e}")
            return None
    
    def get_video_comments(self, video_id, continuation=None):
        """動画コメント取得"""
        try:
            endpoint = f'comments/{video_id}'
            params = {}
            if continuation:
                params['nextpage'] = continuation
            
            data = self._make_request(endpoint, params)
            if not data:
                return {'comments': [], 'continuation': None}
            
            comments = []
            for comment in data.get('comments', []):
                comments.append({
                    'author': comment.get('author', ''),
                    'authorThumbnails': [{'url': comment.get('thumbnail', '')}] if comment.get('thumbnail') else [],
                    'content': comment.get('commentText', ''),
                    'publishedText': comment.get('commentedTime', ''),
                    'likeCount': comment.get('hearted', False)
                })
            
            return {
                'comments': comments,
                'continuation': data.get('nextpage')
            }
            
        except Exception as e:
            logging.error(f"Piped comments error: {e}")
            return {'comments': [], 'continuation': None}
    
    def get_trending_videos(self, region='JP'):
        """トレンド動画取得"""
        try:
            # Pipedのトレンドエンドポイントは地域別
            endpoint = f'trending?region={region}'
            data = self._make_request(endpoint)
            if not data:
                return []
            
            videos = []
            items = data if isinstance(data, list) else []
            for item in items:
                if item.get('type') == 'stream' or item.get('url'):
                    video = {
                        'videoId': item.get('url', '').replace('/watch?v=', ''),
                        'title': item.get('title', ''),
                        'author': item.get('uploaderName', ''),
                        'authorId': item.get('uploaderUrl', '').replace('/channel/', ''),
                        'publishedText': self._format_duration(item.get('uploadedDate')),
                        'viewCount': item.get('views', 0),
                        'lengthSeconds': item.get('duration', 0),
                        'videoThumbnails': [{'url': item.get('thumbnail', '')}] if item.get('thumbnail') else []
                    }
                    videos.append(video)
            
            return videos[:50]  # 最大50件
            
        except Exception as e:
            logging.error(f"Piped trending error: {e}")
            return []
    
    def _format_duration(self, timestamp):
        """タイムスタンプをフォーマット"""
        if not timestamp:
            return ''
        
        try:
            # Pipedのタイムスタンプ形式に応じて調整
            return str(timestamp)
        except:
            return ''