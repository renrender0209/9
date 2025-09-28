import requests
import logging
import yt_dlp
import subprocess
import json
from config import YTDL_OPTIONS


class YtdlService:
    def __init__(self):
        self.node_service_url = "http://localhost:3001"
        self.ytdl_opts = YTDL_OPTIONS.copy()
    
    def get_stream_urls(self, video_id):
        """シンプルで確実な動画取得"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            logging.info(f"動画URL取得開始: {video_id}")
            
            # 最適化されたyt-dlp設定
            opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'format': 'best[height<=1080]/best',
                'noplaylist': True,
                'socket_timeout': 30,
                'retries': 3,
                'fragment_retries': 3,
                'extractor_retries': 3,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                formats = []
                available_qualities = set()
                
                # 利用可能なフォーマットを収集
                for fmt in info.get('formats', []):
                    if not fmt.get('url') or not fmt.get('height'):
                        continue
                    
                    height = fmt.get('height')
                    if height < 240:  # 240p未満は除外
                        continue
                        
                    quality = f"{height}p"
                    
                    # 重複を避ける
                    if quality in available_qualities:
                        continue
                    
                    available_qualities.add(quality)
                    
                    formats.append({
                        'url': fmt['url'],
                        'quality': quality,
                        'resolution': f"{fmt.get('width', '?')}x{height}",
                        'has_audio': fmt.get('acodec', 'none') != 'none',
                        'audio_url': None,
                        'bitrate': fmt.get('tbr', 0),
                        'fps': fmt.get('fps', 30),
                        'ext': fmt.get('ext', 'mp4')
                    })
                
                # 品質でソート（高品質から低品質へ）
                formats.sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
                
                # 音声のみのフォーマットを取得
                audio_url = self._get_audio_stream(video_id)
                
                # 音声が分離されている場合は音声URLを追加
                for fmt in formats:
                    if not fmt['has_audio'] and audio_url:
                        fmt['audio_url'] = audio_url
                
                # フォールバック：基本的な品質オプションを保証
                if not formats:
                    basic_url = info.get('url')
                    if basic_url:
                        formats = [{
                            'url': basic_url,
                            'quality': '720p',
                            'resolution': '1280x720',
                            'has_audio': True,
                            'audio_url': None,
                            'bitrate': 0,
                            'fps': 30,
                            'ext': 'mp4'
                        }]
                
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', ''),
                    'best_url': formats[0]['url'] if formats else None,
                    'formats': formats
                }
                
        except Exception as e:
            logging.error(f"動画取得エラー: {e}")
            return None
    
    def _get_audio_stream(self, video_id):
        """音声ストリームを取得"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'noplaylist': True
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('url') if info else None
                
        except Exception as e:
            logging.error(f"音声取得エラー: {e}")
            return None
    
    def get_audio_url(self, video_id):
        """音声のみのURLを取得（互換性のため）"""
        return self._get_audio_stream(video_id)