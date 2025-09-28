"""
超高速動画取得サービス - ytdl-core並列処理版
"""
import subprocess
import json
import logging
import asyncio
import concurrent.futures
from typing import List, Dict, Optional

class TurboVideoService:
    def __init__(self):
        self.node_script = 'turbo_video_service.js'
        self.max_workers = 10  # 並列処理数
        
    def get_video_stream_720p(self, video_id: str) -> Dict:
        """720p音声付きストリームを優先取得"""
        try:
            result = subprocess.run([
                'node', self.node_script, 'stream', video_id, '720p'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return self._format_stream_response(data)
            else:
                logging.error(f"Turbo stream error: {result.stderr}")
                return {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            logging.error(f"Turbo stream timeout for {video_id}")
            return {'success': False, 'error': 'Stream timeout'}
        except Exception as e:
            logging.error(f"Turbo stream exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def batch_get_videos(self, video_ids: List[str]) -> Dict:
        """複数動画を並列で高速取得"""
        try:
            video_ids_str = ','.join(video_ids)
            result = subprocess.run([
                'node', self.node_script, 'batch', video_ids_str, '720p'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get('success'):
                    formatted_videos = []
                    for video in data.get('videos', []):
                        formatted_videos.append(self._format_stream_response(video))
                    return {
                        'success': True,
                        'videos': formatted_videos,
                        'count': len(formatted_videos)
                    }
                return data
            else:
                logging.error(f"Batch turbo error: {result.stderr}")
                return {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            logging.error("Batch turbo timeout")
            return {'success': False, 'error': 'Batch timeout'}
        except Exception as e:
            logging.error(f"Batch turbo exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def turbo_search(self, query: str, max_results: int = 20) -> Dict:
        """高速検索"""
        try:
            result = subprocess.run([
                'node', self.node_script, 'search', query, str(max_results)
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data
            else:
                logging.error(f"Turbo search error: {result.stderr}")
                return {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            logging.error("Turbo search timeout")
            return {'success': False, 'error': 'Search timeout'}
        except Exception as e:
            logging.error(f"Turbo search exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def _format_stream_response(self, data: Dict) -> Dict:
        """ストリームレスポンスを標準化"""
        if not data.get('success'):
            return data
            
        formats = data.get('formats', {})
        
        # 720p音声付きを最優先
        best_stream = None
        audio_stream = None
        
        if formats.get('combined'):
            best_stream = {
                'video_url': formats['combined']['url'],
                'audio_url': None,
                'has_audio': True,
                'quality': formats['combined']['quality'],
                'container': formats['combined'].get('container', 'mp4')
            }
        elif formats.get('video') and formats.get('audio'):
            best_stream = {
                'video_url': formats['video']['url'],
                'audio_url': formats['audio']['url'],
                'has_audio': False,
                'quality': formats['video']['quality'],
                'container': formats['video'].get('container', 'mp4')
            }
        
        # 品質選択用フォーマット一覧
        quality_options = []
        if data.get('allFormats'):
            for fmt in data['allFormats']:
                if fmt.get('hasVideo') and fmt.get('quality'):
                    quality_options.append({
                        'quality': fmt['quality'],
                        'url': fmt['url'],
                        'hasAudio': fmt.get('hasAudio', False),
                        'container': fmt.get('container', 'mp4')
                    })
        
        return {
            'success': True,
            'video_id': data.get('videoId'),
            'title': data.get('title'),
            'duration': data.get('duration'),
            'author': data.get('author'),
            'thumbnail': data.get('thumbnail'),
            'stream_url': best_stream['video_url'] if best_stream else None,
            'audio_url': best_stream['audio_url'] if best_stream else None,
            'has_audio': best_stream['has_audio'] if best_stream else False,
            'quality': best_stream['quality'] if best_stream else 'unknown',
            'quality_options': quality_options[:10],  # 最大10種類の品質
            'source': 'turbo'
        }
    
    def get_multiple_qualities(self, video_id: str) -> Dict:
        """複数品質のストリームを取得"""
        stream_data = self.get_video_stream_720p(video_id)
        
        if not stream_data.get('success'):
            return stream_data
            
        # 品質別URL辞書を作成
        quality_urls = {}
        if stream_data.get('quality_options'):
            for option in stream_data['quality_options']:
                quality_urls[option['quality']] = {
                    'url': option['url'],
                    'hasAudio': option['hasAudio'],
                    'container': option['container']
                }
        
        stream_data['quality_urls'] = quality_urls
        return stream_data

    def get_youtube_education_url(self, video_id):
        """YouTube Education URLを直接生成"""
        try:
            logging.info(f"Node.js経由でYouTube Education URL生成: {video_id}")
            
            result = subprocess.run(
                ["node", "turbo_video_service.js", "youtube-education-url", video_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                if data.get('success'):
                    return data.get('url')
                    
        except Exception as e:
            logging.error(f"YouTube Education URL生成エラー: {e}")
            
        return None

    def get_playlist_info(self, playlist_url):
        """プレイリスト情報を取得（@distube/ytpl使用）"""
        try:
            logging.info(f"プレイリスト情報取得: {playlist_url}")
            
            result = subprocess.run(
                ["node", "turbo_video_service.js", "playlist", playlist_url],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                logging.info(f"プレイリスト取得結果: {data.get('success', False)}")
                return data
                
        except Exception as e:
            logging.error(f"プレイリスト取得エラー: {e}")
            
        return {"success": False, "error": "プレイリスト取得に失敗しました"}

    def get_advanced_video_info(self, video_id):
        """高度な動画情報を取得（@distube/ytdl-core使用）"""
        try:
            logging.info(f"高度な動画情報取得: {video_id}")
            
            result = subprocess.run(
                ["node", "turbo_video_service.js", "advanced-info", video_id],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                logging.info(f"高度な動画情報取得結果: {data.get('success', False)}")
                return data
                
        except Exception as e:
            logging.error(f"高度な動画情報取得エラー: {e}")
            
        return {"success": False, "error": "高度な動画情報取得に失敗しました"}

    def batch_get_playlists(self, playlist_urls):
        """複数プレイリストを一括取得"""
        try:
            logging.info(f"プレイリスト一括取得: {len(playlist_urls)}件")
            
            urls_string = ",".join(playlist_urls)
            result = subprocess.run(
                ["node", "turbo_video_service.js", "batch-playlists", urls_string],
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                logging.info(f"プレイリスト一括取得結果: {data.get('successful', 0)}/{data.get('totalRequested', 0)}")
                return data
                
        except Exception as e:
            logging.error(f"プレイリスト一括取得エラー: {e}")
            
        return {"success": False, "error": "プレイリスト一括取得に失敗しました"}

    def get_channel_playlists(self, channel_url):
        """チャンネルのプレイリスト一覧を取得"""
        try:
            logging.info(f"チャンネルプレイリスト取得: {channel_url}")
            
            result = subprocess.run(
                ["node", "turbo_video_service.js", "channel-playlists", channel_url],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                logging.info(f"チャンネルプレイリスト取得結果: {data.get('success', False)}")
                return data
                
        except Exception as e:
            logging.error(f"チャンネルプレイリスト取得エラー: {e}")
            
        return {"success": False, "error": "チャンネルプレイリスト取得に失敗しました"}