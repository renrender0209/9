import requests
import logging
import time
import json
import urllib.parse
import base64
import urllib3
import subprocess
from typing import Dict, List, Optional, Union
from urllib.parse import quote

# SSL警告を無効化（証明書の問題があるエンドポイント用）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MultiStreamService:
    """複数のAPIエンドポイントを使用してビデオストリーム取得の高速化と冗長性を提供"""
    
    def __init__(self):
        # 🚀 大幅拡張！高速APIエンドポイント群（優先順位順）
        self.api_endpoints = [
            # メインAPIサーバー群（最高優先度）
            "https://siawaseok.duckdns.org",
            "https://3.net219117116.t-com.ne.jp",
            "https://219.117.116.3",
            
            # 🆕 新しい高速ミラーサーバー群
            "https://yt-api.p.rapidapi.com",
            "https://youtube-scrape.herokuapp.com",
            "https://yt-scrape.vercel.app",
            "https://youtube-api.cyclic.app",
            "https://youtube-dl.vercel.app",
            "https://yt-download.org",
            "https://youtube-mirror.herokuapp.com",
            "https://yt-proxy.netlify.app",
            "https://youtube-api-tau.vercel.app",
            "https://api.streamable.com",
            
            # 🆕 バックアップAPIサーバー群
            "https://watawatawata.glitch.me",
            "https://ytsr-api.vercel.app",
            "https://ytsr.vercel.app",
            "https://api.ytsr.org"
        ]
        
        self.timeout = 4  # 🚀 高速化: 6秒→4秒に短縮
        self.max_retries = 1  # 高速化のためリトライ回数削減
        self._cache = {}
        self._cache_timeout = 600  # 🚀 高速化: キャッシュ時間を10分に延長
        self._failed_endpoints = {}  # 失敗したエンドポイントの記録
        self._failure_timeout = 120  # 2分間は失敗したエンドポイントを避ける
        
        # フォールバック機能設定
        self.enable_fallback = True
        self.fallback_cache = {}  # フォールバック結果のキャッシュ
        self.fallback_cache_timeout = 600  # 10分間キャッシュ
        
        # 処理優先順位設定（True=直接生成優先、False=外部API優先）
        self.direct_generation_first = False  # デフォルトを外部API優先に変更
        
        # 直接YouTube埋め込み用設定
        self.youtube_embed_templates = [
            "https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&mute=0&controls=1&start=0&origin=https%3A%2F%2Fcreate.kahoot.it&playsinline=1&showinfo=0&rel=0&iv_load_policy=3&modestbranding=1&fs=1&enablejsapi=1",
            "https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1&controls=1&rel=0&showinfo=0&modestbranding=1",
            "https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1&rel=0&showinfo=0&modestbranding=1"
        ]
        
        # YouTube EducationベースURL動的取得用設定
        self.edu_base_url_cache = {}
        self.edu_base_url_cache_timeout = 7200  # 2時間キャッシュ（より頻繁に更新）
        self.edu_refresh_sample_video = "wfmpUlRFJGw"  # 定期更新用の固定サンプル動画
        # siawaseok APIから直接取得用の設定
        self.default_edu_base_url = "https://www.youtubeeducation.com/embed"
        
        # Kahoot YouTube Education キー取得用設定
        self.kahoot_key_cache = {}
        self.kahoot_key_cache_timeout = 1800  # 30分キャッシュ
        self.kahoot_key_api_url = "https://apis.kahoot.it/media-api/youtube/key"
        
        # Kahoot動画情報取得用設定
        self.kahoot_videos_api_url = "https://apis.kahoot.it/media-api/youtube/videos"
        self.kahoot_video_cache = {}
        self.kahoot_video_cache_timeout = 600  # 10分キャッシュ
        
        # Kahoot検索API設定
        self.kahoot_search_api_url = "https://apis.kahoot.it/media-api/youtube/search"
        self.kahoot_search_cache = {}
        self.kahoot_search_cache_timeout = 300  # 5分キャッシュ
        
        # リクエスト内でのチャンネルキャッシュ（リクエストごとにリセット）
        self._request_channel_cache = {}
    
    def clear_request_cache(self):
        """リクエスト開始時にリクエストレベルキャッシュをクリア"""
        self._request_channel_cache = {}
        logging.debug("リクエストレベルキャッシュをクリアしました")
    
    def get_cached_channel_info(self, channel_id):
        """キャッシュされたチャンネル情報を取得、なければInvidiousから取得"""
        if not channel_id:
            return None
            
        # リクエスト内キャッシュをチェック
        if channel_id in self._request_channel_cache:
            logging.debug(f"リクエストキャッシュからチャンネル情報を取得: {channel_id}")
            return self._request_channel_cache[channel_id]
        
        # Invidiousから取得（タイムアウトを短く設定）
        try:
            from invidious_service import InvidiousService
            invidious = InvidiousService()
            
            # タイムアウトを短く設定してブロッキングを防ぐ
            channel_info = invidious.get_channel_info(channel_id)
            
            if channel_info and channel_info.get('authorThumbnails'):
                # キャッシュに保存
                self._request_channel_cache[channel_id] = channel_info['authorThumbnails']
                logging.debug(f"チャンネル情報を取得してキャッシュに保存: {channel_id}")
                return channel_info['authorThumbnails']
            else:
                # 失敗した場合も空の配列をキャッシュして再リクエストを防ぐ
                self._request_channel_cache[channel_id] = []
                logging.warning(f"チャンネル情報が取得できませんでした: {channel_id}")
                return []
        except Exception as e:
            # エラーの場合も空の配列をキャッシュ
            self._request_channel_cache[channel_id] = []
            logging.warning(f"チャンネル情報取得エラー ({channel_id}): {e}")
            return []
        
        # Kahoot動画情報取得用設定
        self.kahoot_videos_api_url = "https://apis.kahoot.it/media-api/youtube/videos"
        self.kahoot_video_cache = {}
        self.kahoot_video_cache_timeout = 600  # 10分キャッシュ
        
        # Kahoot検索用設定
        self.kahoot_search_api_url = "https://apis.kahoot.it/media-api/youtube/search"
        self.kahoot_search_cache = {}
        self.kahoot_search_cache_timeout = 300  # 5分キャッシュ
    
    def _make_request(self, endpoint_path: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """複数のエンドポイントで順番にリクエストを試行"""
        # キャッシュチェック
        cache_key = f"{endpoint_path}:{str(params) if params else ''}"
        current_time = time.time()
        
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._cache_timeout:
                logging.info(f"キャッシュからデータ取得: {endpoint_path}")
                return cached_data
        
        # エンドポイントを順番に試行
        for endpoint in self.api_endpoints:
            # 失敗したエンドポイントを一時的に避ける
            if endpoint in self._failed_endpoints:
                failure_time = self._failed_endpoints[endpoint]
                if current_time - failure_time < self._failure_timeout:
                    logging.debug(f"エンドポイントをスキップ（失敗履歴）: {endpoint}")
                    continue
                else:
                    # タイムアウト経過後は再試行
                    del self._failed_endpoints[endpoint]
            
            try:
                url = f"{endpoint.rstrip('/')}/{endpoint_path}"
                logging.info(f"APIリクエスト試行: {url}")
                
                # SSL証明書の問題があるエンドポイントは検証をスキップ
                verify_ssl = not any(problematic in endpoint for problematic in ['3.net219117116.t-com.ne.jp', '219.117.116.3'])
                response = requests.get(url, params=params, timeout=self.timeout, verify=verify_ssl)
                
                if response.status_code == 200:
                    data = response.json()
                    # データが辞書形式であることを確認
                    if isinstance(data, dict):
                        # キャッシュに保存
                        self._cache[cache_key] = (data, current_time)
                        logging.info(f"✅ 成功: {endpoint} - {endpoint_path}")
                        return data
                    else:
                        logging.warning(f"予期しないデータ形式（文字列）を受信: {endpoint} - {type(data)}")
                        self._failed_endpoints[endpoint] = current_time
                        continue
                else:
                    logging.warning(f"HTTPエラー {response.status_code}: {endpoint}")
                    self._failed_endpoints[endpoint] = current_time
                    
            except requests.exceptions.Timeout:
                logging.warning(f"タイムアウト: {endpoint}")
                self._failed_endpoints[endpoint] = current_time
            except requests.exceptions.RequestException as e:
                logging.warning(f"リクエストエラー {endpoint}: {e}")
                self._failed_endpoints[endpoint] = current_time
            except json.JSONDecodeError as e:
                logging.warning(f"JSONパースエラー {endpoint}: {e}")
                self._failed_endpoints[endpoint] = current_time
            except Exception as e:
                logging.error(f"予期しないエラー {endpoint}: {e}")
                self._failed_endpoints[endpoint] = current_time
        
        logging.error(f"すべてのエンドポイントで失敗: {endpoint_path}")
        return None
    
    def get_video_stream_info(self, video_id: str) -> Optional[Dict]:
        """ビデオストリーム情報を取得（type2エンドポイント + 高速直接生成優先）"""
        try:
            # 直接生成優先の場合
            if self.direct_generation_first and self.enable_fallback:
                logging.info(f"高速直接生成優先モード: {video_id}")
                # まず高速な直接生成を試行
                fallback_result = self._get_stream_fallback(video_id)
                if fallback_result:
                    logging.info(f"直接生成成功: {video_id}")
                    return fallback_result
                
                # 直接生成が失敗した場合、外部APIを試行
                logging.info(f"直接生成失敗、外部APIに切り替え: {video_id}")
                endpoint_path = f"api/stream/{video_id}/type2"
                api_result = self._make_request(endpoint_path)
                if api_result:
                    logging.info(f"外部API成功: {video_id}")
                    return api_result
            
            # 外部API優先の場合（従来の動作）
            else:
                # まず外部APIを試行
                endpoint_path = f"api/stream/{video_id}/type2"
                result = self._make_request(endpoint_path)
                
                # 外部APIが成功した場合はそのまま返す
                if result:
                    logging.info(f"外部API成功: {video_id}")
                    return result
                
                # 外部APIが失敗した場合、フォールバック機能を使用
                if self.enable_fallback:
                    logging.info(f"外部API失敗、フォールバック開始: {video_id}")
                    fallback_result = self._get_stream_fallback(video_id)
                    if fallback_result:
                        logging.info(f"フォールバック成功: {video_id}")
                        return fallback_result
                    
            return None
        except Exception as e:
            logging.error(f"ストリーム情報取得エラー ({video_id}): {e}")
            # エラーの場合もフォールバックを試行
            if self.enable_fallback:
                return self._get_stream_fallback(video_id)
            return None
    
    def get_video_basic_stream(self, video_id: str) -> Optional[Dict]:
        """基本ストリーム情報を取得（高速直接生成優先）"""
        try:
            # 直接生成優先の場合
            if self.direct_generation_first and self.enable_fallback:
                # まず高速な直接生成を試行
                fallback_result = self._get_stream_fallback(video_id, stream_type="basic")
                if fallback_result:
                    return fallback_result
                
                # 直接生成が失敗した場合、外部APIを試行
                endpoint_path = f"api/stream/{video_id}"
                api_result = self._make_request(endpoint_path)
                if api_result:
                    return api_result
            
            # 外部API優先の場合
            else:
                # まず外部APIを試行
                endpoint_path = f"api/stream/{video_id}"
                result = self._make_request(endpoint_path)
                
                # 外部APIが成功した場合はそのまま返す
                if result:
                    return result
                    
                # 外部APIが失敗した場合、フォールバック機能を使用
                if self.enable_fallback:
                    logging.info(f"基本ストリーム外部API失敗、フォールバック開始: {video_id}")
                    return self._get_stream_fallback(video_id, stream_type="basic")
                
            return None
        except Exception as e:
            logging.error(f"基本ストリーム取得エラー ({video_id}): {e}")
            if self.enable_fallback:
                return self._get_stream_fallback(video_id, stream_type="basic")
            return None
    
    def get_trending_videos(self) -> Optional[Dict]:
        """トレンド動画を取得"""
        try:
            endpoint_path = "api/trend"
            return self._make_request(endpoint_path)
        except Exception as e:
            logging.error(f"トレンド動画取得エラー: {e}")
            return None
    
    def search_videos(self, query: str, page: int = 1) -> Optional[Dict]:
        """動画検索"""
        try:
            endpoint_path = "api/search"
            params = {"q": query, "page": page}
            return self._make_request(endpoint_path, params)
        except Exception as e:
            logging.error(f"動画検索エラー ({query}): {e}")
            return None
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """チャンネル情報を取得"""
        try:
            endpoint_path = f"api/channel/{channel_id}"
            return self._make_request(endpoint_path)
        except Exception as e:
            logging.error(f"チャンネル情報取得エラー ({channel_id}): {e}")
            return None
    
    def get_direct_youtube_embed_url(self, video_id: str, embed_type: str = "education") -> str:
        """YouTubeの直接埋め込みURLを生成（API不要）"""
        try:
            if embed_type == "education":
                # Kahoot APIを使った動的YouTube Education埋め込みURLを生成
                return self._generate_youtube_education_url_with_kahoot(video_id)
            elif embed_type == "nocookie":
                return self.youtube_embed_templates[1].format(video_id=video_id)
            else:
                return self.youtube_embed_templates[2].format(video_id=video_id)
        except Exception as e:
            logging.error(f"埋め込みURL生成エラー ({video_id}): {e}")
            return self.youtube_embed_templates[1].format(video_id=video_id)  # フォールバック
    
    def get_youtube_thumbnail_url(self, video_id: str, quality: str = "maxresdefault") -> str:
        """YouTube サムネイル画像の直接URLを生成（API不要）"""
        try:
            base_url = f"https://img.youtube.com/vi/{video_id}/"
            quality_options = {
                "maxresdefault": "maxresdefault.jpg",  # 最高画質
                "hqdefault": "hqdefault.jpg",          # 高画質
                "mqdefault": "mqdefault.jpg",          # 中画質
                "sddefault": "sddefault.jpg",          # 標準画質
                "default": "default.jpg"               # デフォルト
            }
            return base_url + quality_options.get(quality, "maxresdefault.jpg")
        except Exception as e:
            logging.error(f"サムネイルURL生成エラー ({video_id}): {e}")
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    def is_video_available_directly(self, video_id: str) -> bool:
        """動画がYouTubeで直接利用可能かチェック"""
        try:
            # 軽量なHEADリクエストでYouTubeサムネイルの存在確認
            thumbnail_url = self.get_youtube_thumbnail_url(video_id, "default")
            response = requests.head(thumbnail_url, timeout=3)
            return response.status_code == 200
        except Exception as e:
            logging.debug(f"直接利用可能性チェックエラー ({video_id}): {e}")
            return True  # エラー時はtrueとして扱う（フォールバック）
    
    def get_endpoint_status(self) -> Dict[str, Dict]:
        """各エンドポイントの状態を取得"""
        status = {}
        current_time = time.time()
        
        for endpoint in self.api_endpoints:
            if endpoint in self._failed_endpoints:
                failure_time = self._failed_endpoints[endpoint]
                time_since_failure = current_time - failure_time
                status[endpoint] = {
                    "status": "failed" if time_since_failure < self._failure_timeout else "recovered",
                    "last_failure": failure_time,
                    "time_since_failure": time_since_failure
                }
            else:
                status[endpoint] = {
                    "status": "active",
                    "last_failure": None,
                    "time_since_failure": 0
                }
        
        return status
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self._cache.clear()
        logging.info("APIキャッシュをクリアしました")
    
    def reset_failed_endpoints(self):
        """失敗したエンドポイントの記録をリセット"""
        self._failed_endpoints.clear()
        logging.info("失敗エンドポイント記録をリセットしました")
    
    def _get_dynamic_edu_base_url(self) -> str:
        """siawaseok APIからYouTube EducationのベースURLを動的に取得（1日キャッシュ）"""
        try:
            cache_key = "edu_base_url"
            current_time = time.time()
            
            # キャッシュチェック
            if cache_key in self.edu_base_url_cache:
                cached_url, timestamp = self.edu_base_url_cache[cache_key]
                if current_time - timestamp < self.edu_base_url_cache_timeout:
                    logging.info(f"YouTube Education ベースURL キャッシュから取得: {cached_url}")
                    return cached_url
            
            # siawaseok APIから動的にURLを取得
            logging.info("siawaseok APIからYouTube Education ベースURLを取得中...")
            
            # 定期更新用の固定サンプル動画を使用
            logging.info(f"定期更新用動画でベースURL取得: {self.edu_refresh_sample_video}")
            api_data = self._make_request(f"api/stream/{self.edu_refresh_sample_video}")
            
            if not api_data:
                logging.info("通常エンドポイントで失敗、type2を試行")
                api_data = self._make_request(f"api/stream/{self.edu_refresh_sample_video}/type2")
            
            if api_data:
                # APIレスポンスのキーを確認
                logging.info(f"APIレスポンスキー: {list(api_data.keys()) if isinstance(api_data, dict) else 'not dict'}")
                
                # siawaseok APIのレスポンスからYouTube Education URLを探す
                youtube_url = None
                
                # 一般的なキー名を確認
                for key in ['youtube_education_url', 'embed_url', 'youtube_url', 'education_url']:
                    if key in api_data and api_data[key]:
                        url_value = api_data[key]
                        if isinstance(url_value, str) and '/embed/' in url_value:
                            youtube_url = url_value
                            logging.info(f"✅ 発見したYouTube URL (キー: {key}): {youtube_url[:100]}...")
                            break
                
                # レスポンス内のすべての値をチェック（ネストしたオブジェクト含む）
                if not youtube_url:
                    def find_embed_url(obj, path=""):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                current_path = f"{path}.{k}" if path else k
                                if isinstance(v, str) and '/embed/' in v and any(domain in v for domain in ['youtubeeducation.com', 'youtube.com', 'youtube-nocookie.com']):
                                    return v, current_path
                                elif isinstance(v, (dict, list)):
                                    result = find_embed_url(v, current_path)
                                    if result:
                                        return result
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj):
                                current_path = f"{path}[{i}]"
                                result = find_embed_url(item, current_path)
                                if result:
                                    return result
                        return None
                    
                    url_result = find_embed_url(api_data)
                    if url_result:
                        youtube_url, found_path = url_result
                        logging.info(f"✅ ネスト検索で発見 ({found_path}): {youtube_url[:100]}...")
                
                if youtube_url and '/embed/' in youtube_url:
                    base_url = youtube_url.split('/embed/')[0] + '/embed'
                    logging.info(f"✅ YouTube Education ベースURL取得成功: {base_url}")
                    
                    # キャッシュに保存
                    self.edu_base_url_cache[cache_key] = (base_url, current_time)
                    return base_url
                else:
                    # デバッグ用にレスポンス構造を表示
                    logging.warning("YouTube Education URLが見つかりません")
                    if isinstance(api_data, dict):
                        for key, value in list(api_data.items())[:3]:
                            logging.info(f"  {key}: {str(value)[:100]}...")
                    
                    # フォールバック: デフォルトURLを使用
                    logging.info(f"デフォルトURLを使用: {self.default_edu_base_url}")
                    self.edu_base_url_cache[cache_key] = (self.default_edu_base_url, current_time)
                    return self.default_edu_base_url
            else:
                logging.warning("APIレスポンスが空またはNoneです")
            
            # フォールバック: デフォルトURLを使用
            logging.warning("siawaseok APIからベースURL取得失敗 - デフォルトを使用")
            return self.default_edu_base_url
            
        except Exception as e:
            logging.error(f"YouTube Education ベースURL取得エラー: {e}")
            return self.default_edu_base_url

    def _get_kahoot_youtube_key(self) -> Optional[str]:
        """Kahoot APIからYouTube Educationキーを取得"""
        current_time = time.time()
        cache_key = "kahoot_key"
        
        # キャッシュチェック
        if cache_key in self.kahoot_key_cache:
            cached_key, timestamp = self.kahoot_key_cache[cache_key]
            if current_time - timestamp < self.kahoot_key_cache_timeout:
                logging.info(f"Kahoot キー キャッシュから取得: {cached_key[:20]}...")
                return cached_key
        
        try:
            logging.info("Kahoot APIからYouTube Educationキーを取得中...")
            response = requests.get(self.kahoot_key_api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'key' in data:
                    key = data['key']
                    # キャッシュに保存
                    self.kahoot_key_cache[cache_key] = (key, current_time)
                    logging.info(f"✅ Kahoot キー取得成功: {key[:20]}...")
                    return key
                else:
                    logging.warning("Kahoot APIレスポンスに'key'フィールドがありません")
            else:
                logging.warning(f"Kahoot API エラー: {response.status_code}")
        
        except Exception as e:
            logging.error(f"Kahoot キー取得エラー: {e}")
        
        return None
    
    def _generate_youtube_education_url_with_kahoot(self, video_id: str) -> str:
        """Kahoot APIを使った動的YouTube Education URL生成（Google Apps Script方式）"""
        try:
            # Kahoot APIから最新のキーを取得
            kahoot_key = self._get_kahoot_youtube_key()
            
            if not kahoot_key:
                logging.warning("Kahoot キー取得失敗 - 従来の方式を使用")
                return self._generate_youtube_education_url(video_id)
            
            # Google Apps Scriptと完全に同じURL生成方式
            base_url = f"https://www.youtubeeducation.com/embed/{video_id}"
            
            # Google Apps Scriptと完全に同じ形式でURLを構築（ユーザー要求に合わせてcontrols=1に変更）
            final_url = (f"{base_url}"
                        f"?autoplay=1&mute=0&controls=1&start=0"
                        f"&origin=https%3A%2F%2Fcreate.kahoot.it"
                        f"&playsinline=1&showinfo=0&rel=0&iv_load_policy=3&modestbranding=1&fs=1"
                        f"&embed_config=%7B%22enc%22%3A%22{urllib.parse.quote(kahoot_key)}%22%2C%22hideTitle%22%3Atrue%7D"
                        f"&enablejsapi=1&widgetid=1")
            
            logging.info(f"✅ Kahoot方式でYouTube Education URL生成完了: {final_url[:100]}...")
            logging.info(f"🔑 使用したKahootキー: {kahoot_key[:20]}...")
            
            return final_url
            
        except Exception as e:
            logging.error(f"Kahoot方式URL生成エラー: {e}")
            # フォールバック: 従来の方式を使用
            return self._generate_youtube_education_url(video_id)

    def _generate_youtube_education_url(self, video_id: str) -> str:
        """完全なYouTube Education埋め込みURL生成（動的ベースURL使用）"""
        try:
            # 動的にベースURLを取得
            dynamic_base_url = self._get_dynamic_edu_base_url()
            base_url = f"{dynamic_base_url}/{video_id}"
            
            # 固定のembed_config（提供されたものと同じ）
            embed_config = {
                "enc": "AXH1ezlDMqRg2sliE-6U84LMtrXE06quNAQW8whxjmPJyEbHIYM8iJqZyL4C1dmz65fkyGT8_CAOBPxZn1TPFdfiT_MxeBVG2kj3MBZvRPd7jtEvqyDT0ozH4dAJtJE286DsFe8aJR6nRjlvfLHzxjka-T7JKf3dXQ==",
                "hideTitle": True
            }
            
            # JSONをURLエンコード
            embed_config_json = json.dumps(embed_config, separators=(',', ':'))
            embed_config_encoded = urllib.parse.quote(embed_config_json)
            
            # 完全なパラメータセット（提供されたURLと同じ）
            params = {
                'autoplay': '1',
                'mute': '0',
                'controls': '1',
                'start': '0',
                'origin': urllib.parse.quote('https://create.kahoot.it'),
                'playsinline': '1',
                'showinfo': '0',
                'rel': '0',
                'iv_load_policy': '3',
                'modestbranding': '1',
                'fs': '1',
                'embed_config': embed_config_encoded,
                'enablejsapi': '1',
                'widgetid': '1'
            }
            
            # URLを構築
            query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
            full_url = f"{base_url}?{query_string}"
            
            logging.info(f"✅ 動的ベースURL使用 YouTube Education URL生成: {full_url[:100]}...")
            logging.info(f"📋 使用したベースURL: {dynamic_base_url}")
            return full_url
            
        except Exception as e:
            logging.error(f"YouTube Education URL生成エラー ({video_id}): {e}")
            # フォールバック
            return f"https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&controls=1&rel=0"
    
    def _generate_dynamic_embed_config(self, video_id: str) -> str:
        """改良された動的埋め込み設定生成（エラーコード2対策）"""
        try:
            import hashlib
            import time
            
            # 現在時刻とビデオIDを組み合わせてユニークなハッシュを生成
            current_time = str(int(time.time()))
            video_hash = hashlib.sha256(f"{video_id}_{current_time}".encode()).hexdigest()
            
            # より有効性の高いエンコード文字列を生成
            # YouTube Educationで認識される形式に近づける
            base_string = f"YTE_{video_id}_{current_time}_{video_hash[:32]}"
            encoded_string = base64.b64encode(base_string.encode()).decode()
            
            # より確実な埋め込み設定
            embed_config = {
                "enc": encoded_string,
                "hideTitle": True,
                "autoHideControls": False,
                "enableEducationMode": True,
                "videoId": video_id,
                "timestamp": current_time
            }
            
            config_json = json.dumps(embed_config, separators=(',', ':'))
            logging.info(f"動的embed_config生成完了: {len(config_json)}文字")
            return config_json
            
        except Exception as e:
            logging.error(f"動的埋め込み設定生成エラー ({video_id}): {e}")
            # 最小限の安全な設定
            return '{"enc":"YTE_default_safe","hideTitle":true,"enableEducationMode":true}'
    
    def _get_stream_fallback(self, video_id: str, stream_type: str = "advanced") -> Optional[Dict]:
        """フォールバック: yt-dlpとytdl-coreで自前URL生成"""
        try:
            # キャッシュチェック
            cache_key = f"fallback_{video_id}_{stream_type}"
            current_time = time.time()
            
            if cache_key in self.fallback_cache:
                cached_data, timestamp = self.fallback_cache[cache_key]
                if current_time - timestamp < self.fallback_cache_timeout:
                    logging.info(f"フォールバックキャッシュから取得: {video_id}")
                    return cached_data
            
            logging.info(f"フォールバック処理開始: {video_id} - {stream_type}")
            
            # 1. ytdl-core (Node.js)で試行
            ytdl_result = self._try_ytdl_core_fallback(video_id)
            if ytdl_result:
                logging.info(f"フォールバック ytdl-core 成功: {video_id}")
                # キャッシュに保存
                self.fallback_cache[cache_key] = (ytdl_result, current_time)
                return ytdl_result
            
            # 2. yt-dlp (Python)で試行
            ytdlp_result = self._try_ytdlp_fallback(video_id)
            if ytdlp_result:
                logging.info(f"フォールバック yt-dlp 成功: {video_id}")
                # キャッシュに保存
                self.fallback_cache[cache_key] = (ytdlp_result, current_time)
                return ytdlp_result
            
            logging.error(f"フォールバック完全失敗: {video_id}")
            return None
            
        except Exception as e:
            logging.error(f"フォールバックエラー ({video_id}): {e}")
            return None
    
    def _try_ytdl_core_fallback(self, video_id: str) -> Optional[Dict]:
        """フォールバック: ytdl-core (Node.js)でストリームURL生成"""
        try:
            # Node.jsサービスを呼び出し
            result = subprocess.run([
                'node', 'turbo_video_service.js', 'stream', video_id, '720p'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('success'):
                    # siawaseok APIのフォーマットに合わせて変換
                    return self._convert_ytdl_to_siawaseok_format(data, video_id)
            else:
                logging.warning(f"ytdl-coreフォールバックエラー: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.warning(f"ytdl-coreフォールバックタイムアウト: {video_id}")
        except Exception as e:
            logging.warning(f"ytdl-coreフォールバック例外: {e}")
            
        return None
    
    def _try_ytdlp_fallback(self, video_id: str) -> Optional[Dict]:
        """フォールバック: yt-dlp (Python)でストリームURL生成"""
        try:
            # ytdl_service.pyを使用
            from ytdl_service import YtdlService
            ytdl_service = YtdlService()
            
            stream_data = ytdl_service.get_stream_urls(video_id)
            if stream_data and stream_data.get('formats'):
                # siawaseok APIのフォーマットに合わせて変換
                return self._convert_ytdlp_to_siawaseok_format(stream_data, video_id)
                
        except Exception as e:
            logging.warning(f"yt-dlpフォールバック例外: {e}")
            
        return None
    
    def _convert_ytdl_to_siawaseok_format(self, ytdl_data: Dict, video_id: str) -> Dict:
        """フォールバック: ytdl-coreデータをsiawaseokフォーマットに変換"""
        try:
            formats = ytdl_data.get('formats', {})
            all_formats = ytdl_data.get('allFormats', [])
            
            result = {
                'title': ytdl_data.get('title', ''),
                'description': '',
                'duration': ytdl_data.get('duration', 0),
                'view_count': 0,
                'author': ytdl_data.get('author', ''),
                'channel_id': '',
                'upload_date': '',
                'thumbnail': ytdl_data.get('thumbnail', ''),
                # ストリームURLを設定
                '1080p': '',
                '720p': '',
                '360p': '',
                'muxed360p': '',
                'audio': '',
                'source': 'fallback_ytdl_core'
            }
            
            # 結合フォーマットがある場合
            if formats.get('combined'):
                combined = formats['combined']
                quality = combined.get('quality', '720p')
                if '720' in quality:
                    result['720p'] = combined['url']
                elif '360' in quality:
                    result['muxed360p'] = combined['url']
                elif '1080' in quality:
                    result['1080p'] = combined['url']
            
            # 分離フォーマットがある場合
            if formats.get('video') and formats.get('audio'):
                video_format = formats['video']
                audio_format = formats['audio']
                quality = video_format.get('quality', '720p')
                
                if '720' in quality:
                    result['720p'] = video_format['url']
                elif '1080' in quality:
                    result['1080p'] = video_format['url']
                    
                result['audio'] = audio_format['url']
            
            # 全フォーマットから最適を選択
            for fmt in all_formats:
                if fmt.get('hasAudio') and fmt.get('hasVideo'):
                    quality = fmt.get('quality', '')
                    url = fmt.get('url', '')
                    if url:
                        if '720p' in quality and not result['720p']:
                            result['720p'] = url
                        elif '360p' in quality and not result['muxed360p']:
                            result['muxed360p'] = url
                        elif '1080p' in quality and not result['1080p']:
                            result['1080p'] = url
                elif fmt.get('hasAudio') and not fmt.get('hasVideo'):
                    if not result['audio']:
                        result['audio'] = fmt.get('url', '')
            
            return result
            
        except Exception as e:
            logging.error(f"ytdlデータ変換エラー: {e}")
            return {}
    
    def _convert_ytdlp_to_siawaseok_format(self, ytdlp_data: Dict, video_id: str) -> Dict:
        """フォールバック: yt-dlpデータをsiawaseokフォーマットに変換"""
        try:
            formats = ytdlp_data.get('formats', [])
            
            result = {
                'title': ytdlp_data.get('title', ''),
                'description': '',
                'duration': ytdlp_data.get('duration', 0),
                'view_count': 0,
                'author': ytdlp_data.get('uploader', ''),
                'channel_id': '',
                'upload_date': '',
                'thumbnail': ytdlp_data.get('thumbnail', ''),
                # ストリームURLを設定
                '1080p': '',
                '720p': '',
                '360p': '',
                'muxed360p': '',
                'audio': '',
                'source': 'fallback_ytdlp'
            }
            
            # フォーマットを解析
            for fmt in formats:
                quality = fmt.get('quality', '')
                url = fmt.get('url', '')
                has_audio = fmt.get('has_audio', False)
                
                if not url:
                    continue
                    
                if '720p' in quality and has_audio and not result['720p']:
                    result['720p'] = url
                elif '360p' in quality and has_audio and not result['muxed360p']:
                    result['muxed360p'] = url
                elif '1080p' in quality and has_audio and not result['1080p']:
                    result['1080p'] = url
                elif '720p' in quality and not has_audio and not result['720p']:
                    # 音声なしの場合、音声も探す
                    result['720p'] = url
                    if fmt.get('audio_url'):
                        result['audio'] = fmt['audio_url']
            
            # 最適なURLを選択
            if ytdlp_data.get('best_url'):
                if not result['720p']:
                    result['720p'] = ytdlp_data['best_url']
            
            return result
            
        except Exception as e:
            logging.error(f"yt-dlpデータ変換エラー: {e}")
            return {}
    
    def toggle_fallback(self, enable: Optional[bool] = None) -> bool:
        """フォールバック機能の有効/無効を切り替え"""
        if enable is not None:
            self.enable_fallback = enable
        else:
            self.enable_fallback = not self.enable_fallback
            
        logging.info(f"フォールバック機能: {'ON' if self.enable_fallback else 'OFF'}")
        return self.enable_fallback
    
    def clear_fallback_cache(self):
        """フォールバックキャッシュをクリア"""
        self.fallback_cache.clear()
        logging.info("フォールバックキャッシュをクリアしました")
    
    def get_kahoot_video_info(self, video_ids: Union[str, List[str]]) -> Optional[Dict]:
        """Kahoot APIから動画情報を取得"""
        try:
            # 文字列の場合はリストに変換
            if isinstance(video_ids, str):
                video_ids = [video_ids]
            
            # カンマ区切りの文字列を作成
            video_ids_str = ','.join(video_ids)
            
            # キャッシュチェック
            cache_key = f"kahoot_videos_{video_ids_str}"
            current_time = time.time()
            
            if cache_key in self.kahoot_video_cache:
                cached_data, timestamp = self.kahoot_video_cache[cache_key]
                if current_time - timestamp < self.kahoot_video_cache_timeout:
                    logging.info(f"Kahoot動画情報キャッシュから取得: {len(video_ids)} 件")
                    return cached_data
            
            # Kahoot APIにリクエスト
            logging.info(f"Kahoot APIから動画情報を取得中: {len(video_ids)} 件")
            
            params = {
                'id': video_ids_str,
                'part': 'snippet,contentDetails'
            }
            
            response = requests.get(self.kahoot_videos_api_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # キャッシュに保存
                self.kahoot_video_cache[cache_key] = (data, current_time)
                
                logging.info(f"✅ Kahoot API成功: {len(data.get('items', []))} 件の動画情報を取得")
                return data
            else:
                logging.warning(f"Kahoot API エラー: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Kahoot動画情報取得エラー: {e}")
            return None
    
    def get_video_info_from_kahoot(self, video_id: str) -> Optional[Dict]:
        """単一の動画情報をKahoot APIから取得し、既存フォーマットに変換"""
        try:
            kahoot_data = self.get_kahoot_video_info(video_id)
            if not kahoot_data or 'items' not in kahoot_data:
                return None
            
            items = kahoot_data['items']
            if not items:
                return None
            
            video_data = items[0]  # 最初の動画を取得
            snippet = video_data.get('snippet', {})
            content_details = video_data.get('contentDetails', {})
            
            # ISO 8601 duration (PT4M13S) を秒数に変換
            duration_str = content_details.get('duration', 'PT0S')
            duration_seconds = self._parse_iso_duration(duration_str)
            
            # チャンネルのサムネイル（投稿者アイコン）を取得
            channel_thumbnails = []
            channel_id = snippet.get('channelId', '')
            
            # 一時的にチャンネル情報取得を無効化（パフォーマンス向上）
            # if channel_id:
            #     # キャッシュされたチャンネル情報を取得
            #     channel_thumbnails = self.get_cached_channel_info(channel_id)
            #     if channel_thumbnails:
            #         logging.debug(f"✅ チャンネルアイコンを取得: {channel_id}")
            
            # フォールバック用のデフォルトアイコン（安全な静的画像）
            if not channel_thumbnails:
                channel_thumbnails = [
                    {
                        'url': '/static/logo.avif',  # 既存のローカル画像を使用
                        'width': 88,
                        'height': 88
                    },
                    {
                        'url': '/static/logo.avif',
                        'width': 176,
                        'height': 176
                    }
                ]

            # 既存のフォーマットに変換
            formatted_data = {
                'videoId': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'author': snippet.get('channelTitle', ''),
                'authorId': snippet.get('channelId', ''),
                'lengthSeconds': duration_seconds,
                'publishedText': snippet.get('publishedAt', ''),
                'published': snippet.get('publishedAt', ''),
                'viewCount': 0,  # Kahoot APIからは取得できない
                'videoThumbnails': [
                    {
                        'url': snippet.get('thumbnails', {}).get('maxresdefault', {}).get('url') or
                               snippet.get('thumbnails', {}).get('high', {}).get('url') or
                               snippet.get('thumbnails', {}).get('medium', {}).get('url') or
                               snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                        'quality': 'maxresdefault'
                    }
                ],
                # 投稿者アイコン（チャンネルサムネイル）を追加
                'authorThumbnails': channel_thumbnails,
                'authorThumbnail': channel_thumbnails[0]['url'] if channel_thumbnails else '',
                # Kahoot API特有の詳細情報も追加
                'categoryId': snippet.get('categoryId', ''),
                'defaultLanguage': snippet.get('defaultLanguage', ''),
                'tags': snippet.get('tags', []),
                'liveBroadcastContent': snippet.get('liveBroadcastContent', 'none'),
                'dimension': content_details.get('dimension', ''),
                'definition': content_details.get('definition', ''),
                'caption': content_details.get('caption', 'false')
            }
            
            logging.info(f"✅ Kahoot動画情報変換完了: {video_id}")
            return formatted_data
            
        except Exception as e:
            logging.error(f"Kahoot動画情報変換エラー ({video_id}): {e}")
            return None
    
    def get_related_videos_from_kahoot(self, base_video_id: str, related_video_ids: List[str]) -> List[Dict]:
        """関連動画をKahoot APIから取得"""
        try:
            if not related_video_ids:
                return []
            
            # 元の動画は除外
            filtered_ids = [vid for vid in related_video_ids if vid != base_video_id]
            
            if not filtered_ids:
                return []
            
            kahoot_data = self.get_kahoot_video_info(filtered_ids)
            if not kahoot_data or 'items' not in kahoot_data:
                return []
            
            related_videos = []
            for video_data in kahoot_data['items']:
                snippet = video_data.get('snippet', {})
                content_details = video_data.get('contentDetails', {})
                video_id = video_data.get('id', '')
                
                # ISO 8601 duration を秒数に変換
                duration_str = content_details.get('duration', 'PT0S')
                duration_seconds = self._parse_iso_duration(duration_str)
                
                # チャンネルのサムネイル（投稿者アイコン）を取得
                channel_thumbnails = []
                channel_id = snippet.get('channelId', '')
                
                # 一時的にチャンネル情報取得を無効化（パフォーマンス向上）
                # if channel_id:
                #     # キャッシュされたチャンネル情報を取得
                #     channel_thumbnails = self.get_cached_channel_info(channel_id)
                #     if channel_thumbnails:
                #         logging.debug(f"✅ 関連動画でチャンネルアイコンを取得: {channel_id}")
                
                # フォールバック用のデフォルトアイコン（安全な静的画像）
                if not channel_thumbnails:
                    channel_thumbnails = [
                        {
                            'url': '/static/logo.avif',
                            'width': 88,
                            'height': 88
                        },
                        {
                            'url': '/static/logo.avif',
                            'width': 176,
                            'height': 176
                        }
                    ]

                related_video = {
                    'videoId': video_id,
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'author': snippet.get('channelTitle', ''),
                    'authorId': snippet.get('channelId', ''),
                    'lengthSeconds': duration_seconds,
                    'publishedText': snippet.get('publishedAt', ''),
                    'published': snippet.get('publishedAt', ''),
                    'viewCount': 0,  # Kahoot APIからは取得できない
                    'videoThumbnails': [
                        {
                            'url': snippet.get('thumbnails', {}).get('maxresdefault', {}).get('url') or
                                   snippet.get('thumbnails', {}).get('high', {}).get('url') or
                                   snippet.get('thumbnails', {}).get('medium', {}).get('url') or
                                   snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                            'quality': 'maxresdefault'
                        }
                    ],
                    # 投稿者アイコン（チャンネルサムネイル）を追加
                    'authorThumbnails': channel_thumbnails,
                    'authorThumbnail': channel_thumbnails[0]['url'] if channel_thumbnails else ''
                }
                related_videos.append(related_video)
            
            logging.info(f"✅ Kahoot関連動画取得完了: {len(related_videos)} 件")
            return related_videos
            
        except Exception as e:
            logging.error(f"Kahoot関連動画取得エラー: {e}")
            return []
    
    def search_videos_with_kahoot(self, query: str, max_results: int = 50, page: int = 1) -> Optional[List[Dict]]:
        """Kahoot APIで動画検索"""
        try:
            # キャッシュチェック
            cache_key = f"search_{query}_{max_results}_{page}"
            current_time = time.time()
            
            if cache_key in self.kahoot_search_cache:
                cached_data, timestamp = self.kahoot_search_cache[cache_key]
                if current_time - timestamp < self.kahoot_search_cache_timeout:
                    logging.info(f"Kahoot検索キャッシュから取得: '{query}' - {len(cached_data)} 件")
                    return cached_data
            
            # Kahoot APIで検索（ページネーション対応）
            start_index = (page - 1) * max_results + 1 if page > 1 else 1
            logging.info(f"Kahoot APIで動画検索: '{query}' - 最大{max_results}件 (ページ{page}: {start_index}から)")
            
            params = {
                'q': query,
                'maxResults': max_results,
                'start': start_index,  # ページネーション用のオフセット
                'regionCode': 'JP',
                'type': 'video',
                'part': 'snippet',
                'safeSearch': 'moderate',
                'videoEmbeddable': 'true'
            }
            
            response = requests.get(self.kahoot_search_api_url, params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'items' in data:
                    search_results = []
                    video_ids = []
                    
                    # 初期データ収集
                    for item in data['items']:
                        snippet = item.get('snippet', {})
                        video_id = item.get('id', {}).get('videoId', '') if isinstance(item.get('id'), dict) else item.get('id', '')
                        
                        if video_id:
                            video_ids.append(video_id)
                            video_result = {
                                'videoId': video_id,
                                'title': snippet.get('title', ''),
                                'description': snippet.get('description', ''),
                                'author': snippet.get('channelTitle', ''),
                                'authorId': snippet.get('channelId', ''),
                                'lengthSeconds': 0,  # 後で詳細APIから取得
                                'viewCount': 0,  # 後で詳細APIから取得
                                'publishedText': snippet.get('publishedAt', ''),
                                'published': snippet.get('publishedAt', ''),
                                'videoThumbnails': [
                                    {
                                        'url': snippet.get('thumbnails', {}).get('maxresdefault', {}).get('url') or
                                               snippet.get('thumbnails', {}).get('high', {}).get('url') or
                                               snippet.get('thumbnails', {}).get('medium', {}).get('url') or
                                               snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                                        'quality': 'maxresdefault'
                                    }
                                ],
                                # Kahoot API特有の情報
                                'categoryId': snippet.get('categoryId', ''),
                                'liveBroadcastContent': snippet.get('liveBroadcastContent', 'none'),
                                'tags': snippet.get('tags', [])
                            }
                            search_results.append(video_result)
                    
                    # Kahoot APIから詳細情報を取得して視聴回数と時間長を補完
                    if video_ids and len(video_ids) <= 50:  # API制限を考慮
                        try:
                            # 複数の動画IDを一括でKahoot APIから取得
                            video_ids_str = ','.join(video_ids)
                            params_detail = {
                                'id': video_ids_str,
                                'part': 'snippet,contentDetails,statistics'
                            }
                            
                            response_detail = requests.get(self.kahoot_videos_api_url, params=params_detail, timeout=15)
                            
                            if response_detail.status_code == 200:
                                detail_data = response_detail.json()
                                
                                if 'items' in detail_data:
                                    # 詳細情報でsearch_resultsを更新
                                    for item in detail_data['items']:
                                        video_id = item.get('id', '')
                                        statistics = item.get('statistics', {})
                                        content_details = item.get('contentDetails', {})
                                        
                                        # 該当する検索結果を更新
                                        for i, video in enumerate(search_results):
                                            if video['videoId'] == video_id:
                                                # 視聴回数を取得
                                                view_count = statistics.get('viewCount', 0)
                                                try:
                                                    view_count = int(view_count) if view_count else 0
                                                except (ValueError, TypeError):
                                                    view_count = 0
                                                
                                                # 動画時間を取得・変換
                                                duration = content_details.get('duration', '')
                                                length_seconds = self._parse_iso_duration(duration)
                                                
                                                search_results[i].update({
                                                    'lengthSeconds': length_seconds,
                                                    'viewCount': view_count
                                                })
                                                break
                                    
                                    logging.info(f"✅ {len(detail_data['items'])} 件の動画詳細情報を補完")
                                
                        except Exception as e:
                            logging.warning(f"Kahoot詳細情報取得エラー: {e}")
                    
                    # キャッシュに保存
                    self.kahoot_search_cache[cache_key] = (search_results, current_time)
                    
                    logging.info(f"✅ Kahoot検索成功: '{query}' - {len(search_results)} 件の動画を取得")
                    return search_results
                else:
                    logging.warning(f"Kahoot検索レスポンスに'items'がありません: {data}")
                    return []
            else:
                logging.warning(f"Kahoot検索API エラー: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Kahoot動画検索エラー: {e}")
            return None
    
    def _parse_iso_duration(self, duration_str: str) -> int:
        """ISO 8601 duration (PT4M13S) を秒数に変換"""
        try:
            if not duration_str or duration_str == 'PT0S':
                return 0
            
            import re
            # PT4M13S のような形式をパース
            pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
            match = re.match(pattern, duration_str)
            
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
            
            return 0
        except Exception as e:
            logging.warning(f"Duration解析エラー: {duration_str}, エラー: {e}")
            return 0
    
    def get_fallback_status(self) -> Dict:
        """フォールバック機能の状態を取得"""
        return {
            'enabled': self.enable_fallback,
            'direct_generation_first': self.direct_generation_first,
            'processing_mode': 'direct_first' if self.direct_generation_first else 'api_first',
            'cache_size': len(self.fallback_cache),
            'cache_timeout': self.fallback_cache_timeout,
            'available_methods': ['ytdl-core', 'yt-dlp']
        }
    
    def toggle_processing_mode(self, direct_first: Optional[bool] = None) -> str:
        """処理優先順位の切り替え（直接生成優先 ↔ 外部API優先）"""
        if direct_first is not None:
            self.direct_generation_first = direct_first
        else:
            self.direct_generation_first = not self.direct_generation_first
            
        mode = 'direct_first' if self.direct_generation_first else 'api_first'
        mode_text = '高速直接生成優先' if self.direct_generation_first else '外部API優先'
        logging.info(f"処理モード変更: {mode_text}")
        return mode