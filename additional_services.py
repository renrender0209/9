import requests
import logging
from urllib.parse import quote

class AdditionalStreamServices:
    def __init__(self):
        self.timeout = 8  # 高速化のためタイムアウト短縮
    
    def get_ytsr_stream(self, video_id):
        """YTSRサービスからストリームを取得"""
        try:
            # 🚀 超高速APIエンドポイント大幅追加（最新2025年版）
            urls_to_try = [
                # YTSRサービス群
                f"https://ytsr-api.vercel.app/api/video/{video_id}",
                f"https://ytsr.vercel.app/api/video/{video_id}",
                f"https://api.ytsr.org/video/{video_id}",
                
                # 🆕 Cobalt Tools API (高速)
                f"https://co.wuk.sh/api/json",  # POST with {"url": "https://youtube.com/watch?v={video_id}"}
                
                # 🆕 YouTube Scrape APIs
                f"https://youtube-scrape.herokuapp.com/api/video/{video_id}",
                f"https://yt-scrape.vercel.app/api/video/{video_id}",
                f"https://youtube-api.cyclic.app/video/{video_id}",
                
                # 🆕 Alternative YouTube APIs  
                f"https://returnyoutubedislike.com/api/votes?videoId={video_id}",
                f"https://yt.lemnoslife.com/videos?part=snippet&id={video_id}",
                f"https://noembed.com/embed?url=https://youtube.com/watch?v={video_id}",
                
                # 🆕 Fast Stream APIs
                f"https://api.streamable.com/videos/{video_id}",
                f"https://youtube-dl.vercel.app/api/video/{video_id}",
                f"https://yt-download.org/api/v1/info/{video_id}",
                
                # 🆕 Mirror/Proxy APIs
                f"https://youtube-mirror.herokuapp.com/api/video/{video_id}",
                f"https://yt-proxy.netlify.app/video/{video_id}",
                f"https://youtube-api-tau.vercel.app/video/{video_id}"
            ]
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_ytsr_response(data, video_id)
                except Exception as e:
                    logging.debug(f"YTSR URL {url} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"YTSRサービスエラー: {e}")
            return None
    
    def get_ytpl_stream(self, video_id):
        """YTPLサービスからストリームを取得"""
        try:
            # YTPLサービスのエンドポイント（一般的なパターン）
            urls_to_try = [
                f"https://ytpl-api.vercel.app/api/video/{video_id}",
                f"https://ytpl.vercel.app/api/video/{video_id}",
                f"https://api.ytpl.org/video/{video_id}"
            ]
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        # データが辞書形式であることを確認
                        if isinstance(data, dict):
                            return self._parse_ytpl_response(data, video_id)
                        else:
                            logging.warning(f"予期しないデータ形式（文字列）を受信: {url} - {type(data)}")
                            continue
                except Exception as e:
                    logging.debug(f"YTPL URL {url} failed: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logging.error(f"YTPLサービスエラー: {e}")
            return None
    
    def get_wakame_high_quality_stream(self, video_id):
        """高画質ストリーム取得（wakame API）"""
        try:
            url = f"https://watawatawata.glitch.me/api/{video_id}?token=wakameoishi"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                # データが辞書形式であることを確認
                if isinstance(data, dict):
                    return self._parse_wakame_response(data, video_id)
                else:
                    logging.warning(f"予期しないデータ形式（文字列）を受信: {url} - {type(data)}")
                    return None
            
            return None
            
        except Exception as e:
            logging.error(f"Wakame高画質サービスエラー: {e}")
            return None
    
    def _parse_ytsr_response(self, data, video_id):
        """YTSR APIレスポンスを解析"""
        try:
            formats = []
            
            if 'formats' in data:
                for fmt in data['formats']:
                    if fmt.get('url') and fmt.get('qualityLabel'):
                        formats.append({
                            'url': fmt['url'],
                            'quality': fmt['qualityLabel'],
                            'resolution': fmt.get('resolution', ''),
                            'has_audio': fmt.get('hasAudio', True),
                            'audio_url': fmt.get('audioUrl'),
                            'bitrate': fmt.get('bitrate', 0),
                            'fps': fmt.get('fps', 30),
                            'ext': fmt.get('ext', 'mp4')
                        })
            
            if formats:
                return {
                    'title': data.get('title', ''),
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnail', ''),
                    'uploader': data.get('uploader', ''),
                    'best_url': formats[0]['url'],
                    'formats': formats,
                    'source': 'YTSR'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"YTSR解析エラー: {e}")
            return None
    
    def _parse_ytpl_response(self, data, video_id):
        """YTPL APIレスポンスを解析"""
        try:
            formats = []
            
            if 'videoDetails' in data and 'formats' in data['videoDetails']:
                for fmt in data['videoDetails']['formats']:
                    if fmt.get('url') and fmt.get('qualityLabel'):
                        formats.append({
                            'url': fmt['url'],
                            'quality': fmt['qualityLabel'],
                            'resolution': fmt.get('resolution', ''),
                            'has_audio': fmt.get('hasAudio', True),
                            'audio_url': fmt.get('audioUrl'),
                            'bitrate': fmt.get('bitrate', 0),
                            'fps': fmt.get('fps', 30),
                            'ext': fmt.get('ext', 'mp4')
                        })
            
            if formats:
                video_details = data.get('videoDetails', {})
                return {
                    'title': video_details.get('title', ''),
                    'duration': video_details.get('lengthSeconds', 0),
                    'thumbnail': video_details.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', ''),
                    'uploader': video_details.get('author', ''),
                    'best_url': formats[0]['url'],
                    'formats': formats,
                    'source': 'YTPL'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"YTPL解析エラー: {e}")
            return None
    
    def _parse_wakame_response(self, data, video_id):
        """Wakame高画質APIレスポンスを解析"""
        try:
            formats = []
            
            # Wakame APIの構造に応じて調整
            if 'videoUrl' in data:
                formats.append({
                    'url': data['videoUrl'],
                    'quality': data.get('quality', '1080p'),
                    'resolution': data.get('resolution', '1920x1080'),
                    'has_audio': True,
                    'audio_url': data.get('audioUrl'),
                    'bitrate': data.get('bitrate', 0),
                    'fps': data.get('fps', 60),
                    'ext': 'mp4'
                })
            elif 'formats' in data:
                for fmt in data['formats']:
                    if fmt.get('url'):
                        formats.append({
                            'url': fmt['url'],
                            'quality': fmt.get('quality', 'high'),
                            'resolution': fmt.get('resolution', ''),
                            'has_audio': fmt.get('hasAudio', True),
                            'audio_url': fmt.get('audioUrl'),
                            'bitrate': fmt.get('bitrate', 0),
                            'fps': fmt.get('fps', 60),
                            'ext': fmt.get('ext', 'mp4')
                        })
            
            if formats:
                return {
                    'title': data.get('title', ''),
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnail', ''),
                    'uploader': data.get('uploader', ''),
                    'best_url': formats[0]['url'],
                    'formats': formats,
                    'source': 'Wakame High Quality'
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Wakame解析エラー: {e}")
            return None
    
    def get_cobalt_stream(self, video_id):
        """🚀 Cobalt Tools API - 超高速ストリーム取得"""
        try:
            url = "https://co.wuk.sh/api/json"
            payload = {
                "url": f"https://youtube.com/watch?v={video_id}",
                "vQuality": "max",
                "aFormat": "mp3",
                "isAudioOnly": False,
                "disableMetadata": True
            }
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return self._parse_cobalt_response(data, video_id)
            
            return None
            
        except Exception as e:
            logging.error(f"Cobalt Tools APIエラー: {e}")
            return None
    
    def get_noembed_stream(self, video_id):
        """🚀 Noembed API - 軽量高速取得"""
        try:
            url = f"https://noembed.com/embed?url=https://youtube.com/watch?v={video_id}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_noembed_response(data, video_id)
            
            return None
            
        except Exception as e:
            logging.error(f"Noembed APIエラー: {e}")
            return None
    
    def get_lemnoslife_stream(self, video_id):
        """🚀 LemnosLife API - YouTube互換高速API"""
        try:
            url = f"https://yt.lemnoslife.com/videos?part=snippet,contentDetails&id={video_id}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_lemnoslife_response(data, video_id)
            
            return None
            
        except Exception as e:
            logging.error(f"LemnosLife APIエラー: {e}")
            return None
    
    def _parse_cobalt_response(self, data, video_id):
        """Cobalt Tools APIレスポンスを解析"""
        try:
            if data.get('status') == 'success' and data.get('url'):
                return {
                    'title': data.get('filename', ''),
                    'duration': 0,
                    'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                    'uploader': '',
                    'best_url': data['url'],
                    'formats': [{
                        'url': data['url'],
                        'quality': data.get('quality', 'max'),
                        'resolution': '',
                        'has_audio': not data.get('isAudioOnly', False),
                        'audio_url': data.get('audioUrl'),
                        'bitrate': 0,
                        'fps': 30,
                        'ext': 'mp4'
                    }],
                    'source': 'Cobalt Tools'
                }
            return None
        except Exception as e:
            logging.error(f"Cobalt解析エラー: {e}")
            return None
    
    def _parse_noembed_response(self, data, video_id):
        """Noembed APIレスポンスを解析"""
        try:
            if data.get('type') == 'video':
                return {
                    'title': data.get('title', ''),
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnail_url', ''),
                    'uploader': data.get('author_name', ''),
                    'best_url': data.get('url', ''),
                    'formats': [{
                        'url': data.get('url', ''),
                        'quality': 'embed',
                        'resolution': f"{data.get('width', 1280)}x{data.get('height', 720)}",
                        'has_audio': True,
                        'audio_url': None,
                        'bitrate': 0,
                        'fps': 30,
                        'ext': 'embed'
                    }],
                    'source': 'Noembed'
                }
            return None
        except Exception as e:
            logging.error(f"Noembed解析エラー: {e}")
            return None
    
    def _parse_lemnoslife_response(self, data, video_id):
        """LemnosLife APIレスポンスを解析"""
        try:
            if 'items' in data and len(data['items']) > 0:
                item = data['items'][0]
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})
                
                return {
                    'title': snippet.get('title', ''),
                    'duration': self._parse_duration(content_details.get('duration', '')),
                    'thumbnail': snippet.get('thumbnails', {}).get('maxres', {}).get('url', ''),
                    'uploader': snippet.get('channelTitle', ''),
                    'best_url': f'https://youtube.com/watch?v={video_id}',
                    'formats': [{
                        'url': f'https://youtube.com/watch?v={video_id}',
                        'quality': 'api',
                        'resolution': '',
                        'has_audio': True,
                        'audio_url': None,
                        'bitrate': 0,
                        'fps': 30,
                        'ext': 'ref'
                    }],
                    'source': 'LemnosLife'
                }
            return None
        except Exception as e:
            logging.error(f"LemnosLife解析エラー: {e}")
            return None
    
    def _parse_duration(self, duration_str):
        """YouTube duration format (PT1M30S) を秒に変換"""
        try:
            import re
            if not duration_str.startswith('PT'):
                return 0
            
            hours = re.search(r'(\d+)H', duration_str)
            minutes = re.search(r'(\d+)M', duration_str)
            seconds = re.search(r'(\d+)S', duration_str)
            
            total_seconds = 0
            if hours:
                total_seconds += int(hours.group(1)) * 3600
            if minutes:
                total_seconds += int(minutes.group(1)) * 60
            if seconds:
                total_seconds += int(seconds.group(1))
                
            return total_seconds
        except:
            return 0