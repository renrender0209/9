import requests
import logging
import time
import json
import urllib.parse
from typing import Dict, List, Optional, Union

class CustomApiService:
    """siawaseok.duckdns.orgのAPIエンドポイントを使用した統合サービス"""
    
    def __init__(self):
        self.base_url = "https://siawaseok.duckdns.org"
        self.timeout = 2  # 🚀 高速化: 5秒→2秒に短縮（検索速度向上）
        self._cache = {}
        self._cache_timeout = 600  # 🚀 高速化: キャッシュ時間を10分に延長
        
        # siawaseok APIエンドポイント
        self.search_endpoint = "/api/search"
        self.stream_endpoint = "/api/stream"  # 動画ストリーム用
        self.trend_endpoint = "/api/trend"    # トレンド動画用  
        self.channel_endpoint = "/api/channel"  # チャンネル情報用
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """APIリクエストの実行"""
        cache_key = f"{endpoint}:{str(params) if params else ''}"
        current_time = time.time()
        
        # キャッシュチェック
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._cache_timeout:
                logging.info(f"キャッシュからデータ取得: {endpoint}")
                return cached_data
        
        try:
            url = f"{self.base_url}{endpoint}"
            logging.info(f"APIリクエスト: {url}")
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                # データが辞書形式であることを確認
                if isinstance(data, dict):
                    # キャッシュに保存
                    self._cache[cache_key] = (data, current_time)
                    logging.info(f"✅ 成功: {url}")
                    return data
                else:
                    logging.warning(f"予期しないデータ形式（文字列）を受信: {url} - {type(data)}")
                    return None
            else:
                logging.warning(f"HTTPエラー {response.status_code}: {url}")
                return None
                
        except requests.exceptions.Timeout:
            logging.warning(f"タイムアウト: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logging.warning(f"リクエストエラー: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.warning(f"JSONパースエラー: {e}")
            return None
        except Exception as e:
            logging.error(f"予期しないエラー: {e}")
            return None
    
    def search_videos(self, query: str) -> Optional[Dict]:
        """動画検索API呼び出し"""
        if not query:
            return None
            
        params = {'q': query}
        return self._make_request(self.search_endpoint, params)
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """動画情報取得API呼び出し（siawaseok streamエンドポイント使用）"""
        if not video_id:
            return None
            
        # siawaseok APIの/api/stream/{video_id}/エンドポイントを使用
        endpoint = f"{self.stream_endpoint}/{video_id}/"
        raw_data = self._make_request(endpoint)
        
        if raw_data:
            # video_idを明示的に渡してフォーマット
            return self.format_video_info(raw_data, video_id)
        
        return None
    
    def get_video_comments(self, video_id: str) -> Optional[Dict]:
        """動画コメント取得API呼び出し（siawaseok APIにはコメントエンドポイントがないため無効化）"""
        logging.warning("siawaseok APIにはコメントエンドポイントがありません。omada.cafe APIのみ使用してください。")
        return None
    
    def get_video_comments_with_priority(self, video_id: str) -> Optional[Dict]:
        """最優先でomada.cafeからコメント取得、フォールバック付き"""
        if not video_id:
            return None
        
        # 1. 最優先: yt.omada.cafe API
        try:
            omada_url = f"https://yt.omada.cafe/api/v1/comments/{video_id}"
            logging.info(f"🎯 最優先: omada.cafe APIからコメント取得試行: {omada_url}")
            
            response = requests.get(omada_url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and data:
                    logging.info(f"✅ 成功: omada.cafe APIからコメント取得完了")
                    return data
            else:
                logging.warning(f"omada.cafe API HTTPエラー {response.status_code}: {omada_url}")
        except Exception as e:
            logging.warning(f"omada.cafe API エラー: {e}")
        
        # siawaseok APIにはコメントエンドポイントがないため、omada.cafe APIのみ使用
        logging.warning(f"コメント取得失敗: omada.cafe APIが利用できません: {video_id}")
        return None
    
    def format_search_results(self, search_data: Dict) -> List[Dict]:
        """検索結果を標準形式にフォーマット"""
        if not search_data:
            return []
        
        formatted_results = []
        
        # API応答の構造に応じて調整が必要
        videos = search_data.get('videos', search_data.get('items', []))
        
        for video in videos:
            formatted_video = {
                'videoId': video.get('videoId', video.get('id')),
                'title': video.get('title', ''),
                'author': video.get('author', video.get('channel', {}).get('name', '')),
                'publishedText': video.get('publishedText', video.get('published', '')),
                'viewCount': video.get('viewCount', 0),
                'lengthSeconds': video.get('lengthSeconds', video.get('duration', 0)),
                'videoThumbnails': video.get('videoThumbnails', video.get('thumbnails', [])),
                'description': video.get('description', video.get('descriptionSnippet', ''))
            }
            formatted_results.append(formatted_video)
        
        return formatted_results
    
    def format_video_info(self, video_data: Dict, video_id: str = '') -> Optional[Dict]:
        """動画情報を標準形式にフォーマット（siawaseok API対応）"""
        if not video_data:
            return None
        
        # video_idは外部から渡されるか、レスポンスから抽出
        if not video_id:
            video_id = video_data.get('id', video_data.get('videoId', ''))
        
        # siawaseok APIの実際のフィールド構造に対応
        title = video_data.get('title', '')
        author = video_data.get('uploader', video_data.get('author', ''))
        authorId = video_data.get('uploader_id', video_data.get('authorId', ''))
        description = video_data.get('description', '')
        viewCount = video_data.get('view_count', video_data.get('viewCount', 0))
        duration = video_data.get('duration', video_data.get('lengthSeconds', 0))
        uploadDate = video_data.get('upload_date', video_data.get('publishedText', ''))
        
        # サムネイルを適切にフォーマット
        video_thumbnails = []
        if 'thumbnailUrl' in video_data:
            # siawaseok APIのthumbnailUrl形式
            thumbnail_url = video_data['thumbnailUrl']
            video_thumbnails = [
                {'url': thumbnail_url, 'quality': 'maxresdefault', 'width': 1280, 'height': 720},
                {'url': thumbnail_url, 'quality': 'sddefault', 'width': 640, 'height': 480}
            ]
        elif 'thumbnails' in video_data:
            video_thumbnails = video_data['thumbnails']
        
        # ストリームURLを適切に取得
        stream_url = ''
        format_streams = []
        adaptive_formats = []
        
        if 'videoStreams' in video_data and video_data['videoStreams']:
            # 最初の動画ストリームをメインURLとして使用
            video_streams = video_data['videoStreams']
            if video_streams:
                stream_url = video_streams[0].get('url', '')
                format_streams = video_streams
        
        if 'audioStreams' in video_data:
            adaptive_formats = video_data['audioStreams']
        
        # HLSストリームがある場合は優先
        if 'hls' in video_data:
            stream_url = video_data['hls']
        
        formatted_info = {
            'videoId': video_id,
            'title': title,
            'author': author,
            'authorId': authorId,
            'description': description,
            'viewCount': viewCount,
            'lengthSeconds': duration,
            'publishedText': uploadDate,
            'videoThumbnails': video_thumbnails,
            'formatStreams': format_streams,
            'adaptiveFormats': adaptive_formats,
            'streamUrl': stream_url,
            'youtubeeducation': self._generate_youtube_education_url(video_id),
            'hls': video_data.get('hls', ''),  # HLSストリームも追加
            'videoStreams': video_data.get('videoStreams', []),  # 元のストリーム情報も保持
            'audioStreams': video_data.get('audioStreams', [])   # 音声ストリーム情報も保持
        }
        
        return formatted_info
    
    def format_comments(self, comments_data: Dict) -> List[Dict]:
        """コメントを標準形式にフォーマット（チャンネルアイコンフォールバック付き）"""
        if not comments_data:
            return []
        
        comments = comments_data.get('comments', comments_data.get('items', []))
        formatted_comments = []
        
        for comment in comments:
            # コメント投稿者のアイコン取得（複数ソース対応）
            author_thumbnails = comment.get('authorThumbnails', [])
            author_id = comment.get('authorId', '')
            author_name = comment.get('author', '')
            
            # アイコンデータが空の場合はフォールバック処理
            if not author_thumbnails:
                # 確実に動作するYouTubeデフォルトアイコンURLを使用
                author_thumbnails = [
                    {
                        'url': 'https://yt3.ggpht.com/ytc/AOPolaDefault=s88-c-k-c0x00ffffff-no-rj',
                        'width': 88,
                        'height': 88
                    },
                    {
                        'url': 'https://yt3.ggpht.com/ytc/AOPolaDefault=s176-c-k-c0x00ffffff-no-rj',
                        'width': 176,
                        'height': 176
                    }
                ]
            
            # メインのアイコンURL設定（HTMLテンプレート用）
            authorThumbnail = ''
            if author_thumbnails and len(author_thumbnails) > 0:
                # 最初のサムネイルURLを使用
                authorThumbnail = author_thumbnails[0].get('url', '')
            
            # フォールバック: デフォルトアイコンURLを使用
            if not authorThumbnail:
                authorThumbnail = 'https://yt3.ggpht.com/ytc/AOPolaDefault=s88-c-k-c0x00ffffff-no-rj'
            
            formatted_comment = {
                'author': author_name,
                'authorId': author_id,
                'content': comment.get('content', comment.get('text', '')),
                'published': comment.get('published', comment.get('publishedText', '')),
                'likeCount': comment.get('likeCount', 0),
                'authorThumbnails': author_thumbnails,
                'authorThumbnail': authorThumbnail  # HTMLテンプレート用のメインアイコンURL
            }
            formatted_comments.append(formatted_comment)
        
        return formatted_comments
    
    def _generate_youtube_education_url(self, video_id: str) -> str:
        """YouTube Education URLを生成"""
        if not video_id:
            return ""
        
        return f"https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&mute=0&controls=1&start=0&origin=https%3A%2F%2Fcreate.kahoot.it&playsinline=1&showinfo=0&rel=0&iv_load_policy=3&modestbranding=1&fs=1&enablejsapi=1"
    
    def can_access_video_page(self, video_data: Dict) -> bool:
        """siawaseok APIから取得したデータで動画ページにアクセス可能かチェック"""
        if not video_data:
            return False
        
        # 動画情報が取得できている（videoIdは必須）
        has_video_info = bool(video_data.get('videoId'))
        
        # YouTubeEducation URLが生成されている
        has_youtube_education = bool(video_data.get('youtubeeducation'))
        
        # ストリームURLまたはHLSが利用可能
        has_stream = bool(video_data.get('streamUrl') or video_data.get('hls') or 
                         (video_data.get('videoStreams') and len(video_data.get('videoStreams', [])) > 0))
        
        # タイトルが取得できている
        has_title = bool(video_data.get('title'))
        
        return has_video_info and has_youtube_education and has_stream and has_title