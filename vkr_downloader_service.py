import requests
import logging
import time
import json
import urllib.parse
from typing import Dict, List, Optional, Union

class OmadaVideoService:
    """Omada APIを使用した動画・音声ストリーム取得サービス"""
    
    def __init__(self):
        self.base_url = "https://yt.omada.cafe"
        self.timeout = 6  # 🚀 高速化: 15秒→6秒に短縮
        self._cache = {}
        self._cache_timeout = 600  # 🚀 高速化: キャッシュ時間を10分に延長
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """APIリクエストの実行（キャッシュ付き）"""
        cache_key = f"{endpoint}:{str(params) if params else ''}"
        current_time = time.time()
        
        # キャッシュチェック
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._cache_timeout:
                logging.info(f"VKRDownloader: キャッシュからデータ取得: {endpoint}")
                return cached_data
        
        try:
            url = f"{self.base_url}{endpoint}"
            logging.info(f"VKRDownloader APIリクエスト: {url}")
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                # レスポンステキストをログ出力（デバッグ用）
                logging.info(f"VKRDownloader レスポンス（最初の200文字）: {response.text[:200]}")
                
                # JSONかどうか確認
                content_type = response.headers.get('content-type', '').lower()
                if 'application/json' in content_type or response.text.strip().startswith('{'):
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            # キャッシュに保存
                            self._cache[cache_key] = (data, current_time)
                            logging.info(f"✅ VKRDownloader API成功: {url}")
                            return data
                        else:
                            logging.warning(f"VKRDownloader: 予期しないデータ形式: {url} - {type(data)}")
                            return None
                    except json.JSONDecodeError as e:
                        logging.warning(f"VKRDownloader JSON解析エラー: {e}")
                        logging.warning(f"レスポンステキスト: {response.text[:500]}")
                        return None
                else:
                    # HTMLやその他の形式の場合
                    logging.warning(f"VKRDownloader: JSONでないレスポンス: {content_type}")
                    logging.warning(f"レスポンステキスト: {response.text[:500]}")
                    return None
            else:
                logging.warning(f"VKRDownloader HTTPエラー {response.status_code}: {url}")
                logging.warning(f"エラーレスポンス: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logging.warning(f"VKRDownloader タイムアウト: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logging.warning(f"VKRDownloader リクエストエラー: {e}")
            return None
        except Exception as e:
            logging.error(f"VKRDownloader 予期しないエラー: {e}")
            return None
    
    def get_stream_urls(self, video_input: str, target_qualities: List[str] = None) -> Optional[Dict]:
        """YouTube URLまたは動画IDから多品質動画・音声ストリームURLを取得
        
        Args:
            video_input: YouTube URLまたは動画ID
            target_qualities: 対象品質のリスト ['360p', '480p', '720p', '1080p']
        """
        if not video_input:
            return None
            
        if target_qualities is None:
            target_qualities = ['360p', '480p', '720p', '1080p']
            
        # 動画IDを抽出（URLの場合）または直接使用（IDの場合）
        if 'youtube.com' in video_input or 'youtu.be' in video_input:
            # 完全なURLの場合、IDを抽出
            video_id = self.get_video_id_from_url(video_input)
        else:
            # 単純なIDの場合、そのまま使用
            video_id = video_input
        
        if not video_id:
            return None
            
        logging.info(f"🚀 yt.omada.cafe API - 多品質動画取得開始: {video_id}, 対象品質: {target_qualities}")
        
        # 新しいAPIエンドポイントを使用
        endpoint = f'/api/v1/videos/{video_id}'
        response_data = self._make_request(endpoint)
        
        if response_data:
            # フォーマットしたデータを返す
            formatted_data = self.format_multi_quality_stream_data(response_data, video_id, target_qualities)
            if formatted_data:
                logging.info(f"✅ yt.omada.cafe API - 多品質ストリームデータ取得成功: {video_id}")
                return formatted_data
            else:
                logging.warning(f"⚠️ yt.omada.cafe API - データフォーマット失敗: {video_id}")
        
        return None
    
    def get_video_id_from_url(self, youtube_url: str) -> Optional[str]:
        """YouTube URLから動画IDを抽出"""
        try:
            if 'youtube.com/watch' in youtube_url:
                parsed_url = urllib.parse.urlparse(youtube_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            elif 'youtu.be/' in youtube_url:
                return youtube_url.split('youtu.be/')[-1].split('?')[0]
            return None
        except Exception as e:
            logging.error(f"動画ID抽出エラー: {e}")
            return None
    
    def _extract_quality_from_size(self, size_str):
        """sizeフィールド（例："426x240"）から品質ラベル（例："240p"）を抽出"""
        if not size_str or 'x' not in size_str:
            return None
        try:
            _, height = size_str.split('x')
            return f"{int(height)}p"
        except (ValueError, IndexError):
            return None
    
    def format_multi_quality_stream_data(self, stream_data: Dict, video_id: str, target_qualities: List[str]) -> Optional[Dict]:
        """多品質ストリームデータを標準形式にフォーマット（360p以外は音声分離対応）"""
        if not stream_data:
            return None
        
        try:
            # 基本情報
            formatted_data = {
                'videoId': video_id,
                'success': True,
                'multi_quality': True,
                'quality_streams': {},  # 品質別ストリーム
                'best_audio': None,     # 最高品質音声（360p以外用）
                'title': stream_data.get('title', ''),
                'thumbnail': stream_data.get('videoThumbnails', [{}])[0].get('url', '') if stream_data.get('videoThumbnails') else '',
                'description': stream_data.get('description', ''),
                'author': stream_data.get('author', ''),
                'authorId': stream_data.get('authorId', ''),
                'viewCount': stream_data.get('viewCount', 0),
                'lengthSeconds': stream_data.get('lengthSeconds', 0),
                'publishedText': stream_data.get('publishedText', '')
            }
            
            # 対象品質毎のストリーム情報を収集
            for quality in target_qualities:
                formatted_data['quality_streams'][quality] = {
                    'video_url': None,
                    'audio_url': None,
                    'combined_url': None,
                    'has_audio': False  # 後で結合ストリームがあれば更新
                }
            
            # 最高品質の音声ストリーム（360p以外用）を取得
            adaptive_formats = stream_data.get('adaptiveFormats', [])
            logging.info(f"🔍 デバッグ: adaptiveFormats 数 = {len(adaptive_formats)}")
            audio_streams = []
            
            for i, format_item in enumerate(adaptive_formats):
                if not format_item.get('url'):
                    logging.info(f"🔍 Format {i}: URLなし")
                    continue
                    
                format_type = format_item.get('type', '')
                height = format_item.get('height')
                logging.info(f"🔍 Format {i}: type={format_type}, height={height}")
                    
                # 音声のみのストリーム
                if 'audioQuality' in format_item or 'audio' in format_type.lower():
                    audio_info = {
                        'url': format_item.get('url', ''),
                        'bitrate': format_item.get('bitrate', 0),
                        'container': format_item.get('container', 'mp4')
                    }
                    audio_streams.append(audio_info)
                    logging.info(f"🔍 音声ストリーム追加: bitrate={format_item.get('bitrate', 0)}")
                
                # 動画のみのストリーム（品質別）
                elif 'video' in format_type.lower():
                    # yt.omada.cafe APIでは qualityLabel, resolution, または size から品質を取得
                    quality_label = (format_item.get('qualityLabel') or 
                                   format_item.get('resolution') or
                                   self._extract_quality_from_size(format_item.get('size', '')))
                    
                    logging.info(f"🔍 動画ストリーム発見: {quality_label}")
                    
                    if quality_label in target_qualities:
                        if formatted_data['quality_streams'][quality_label]['video_url'] is None:
                            formatted_data['quality_streams'][quality_label]['video_url'] = format_item.get('url', '')
                            logging.info(f"✅ {quality_label}動画URL設定完了")
            
            # 最高品質音声を選択
            if audio_streams:
                formatted_data['best_audio'] = max(audio_streams, key=lambda x: x.get('bitrate', 0))
                
                # 360p以外の品質に最高品質音声を割り当て
                for quality in target_qualities:
                    if quality != '360p':
                        formatted_data['quality_streams'][quality]['audio_url'] = formatted_data['best_audio']['url']
            
            # formatStreams（結合ストリーム）処理 - 全品質対応
            format_streams = stream_data.get('formatStreams', [])
            for format_item in format_streams:
                if not format_item.get('url'):
                    continue
                    
                quality_label = self._parse_quality_label(format_item.get('qualityLabel', format_item.get('quality', 'medium')))
                quality_str = f"{quality_label}p"
                
                # すべての品質で結合ストリーム（音声付き）を優先
                if quality_str in target_qualities:
                    formatted_data['quality_streams'][quality_str]['combined_url'] = format_item.get('url', '')
                    formatted_data['quality_streams'][quality_str]['has_audio'] = True
                    logging.info(f"✅ {quality_str}結合ストリーム（音声付き）設定完了")
            
            # 利用可能な品質をログ出力
            available_qualities = [q for q in target_qualities 
                                 if formatted_data['quality_streams'][q]['video_url'] or 
                                    formatted_data['quality_streams'][q]['combined_url']]
            logging.info(f"✅ 利用可能品質: {available_qualities}")
            
            return formatted_data
            
        except Exception as e:
            logging.error(f"Omada 多品質ストリームデータフォーマットエラー: {e}")
            return None

    def format_stream_data(self, stream_data: Dict, video_id: str) -> Optional[Dict]:
        """ストリームデータを標準形式にフォーマット（Omada API応答構造に対応）"""
        if not stream_data:
            return None
        
        try:
            # Omada APIの応答構造: 直接rootにデータ
            formatted_data = {
                'videoId': video_id,
                'success': True,
                'video_streams': [],
                'audio_streams': [],
                'combined_streams': [],
                'title': stream_data.get('title', ''),
                'thumbnail': stream_data.get('videoThumbnails', [{}])[0].get('url', '') if stream_data.get('videoThumbnails') else '',
                'description': stream_data.get('description', ''),
                'author': stream_data.get('author', ''),
                'authorId': stream_data.get('authorId', ''),
                'viewCount': stream_data.get('viewCount', 0),
                'lengthSeconds': stream_data.get('lengthSeconds', 0),
                'publishedText': stream_data.get('publishedText', '')
            }
            
            # adaptiveFormats（分離された動画/音声）を処理
            adaptive_formats = stream_data.get('adaptiveFormats', [])
            for format_item in adaptive_formats:
                if not format_item.get('url'):
                    continue
                
                # 適切な品質表示を生成
                quality_label = self._get_quality_from_adaptive_format(format_item)
                
                format_info = {
                    'url': format_item.get('url', ''),
                    'itag': format_item.get('itag', ''),
                    'container': format_item.get('container', 'mp4'),
                    'quality': quality_label,
                    'quality_height': format_item.get('height', 0),
                    'quality_width': format_item.get('width', 0),
                    'bitrate': format_item.get('bitrate', 0),
                    'fps': format_item.get('fps', 30),
                    'has_video': 'encoding' in format_item and 'audio' not in format_item.get('type', '').lower(),
                    'has_audio': 'audioQuality' in format_item or 'audio' in format_item.get('type', '').lower()
                }
                
                # 動画か音声かを判定
                if format_info['has_video'] and not format_info['has_audio']:
                    formatted_data['video_streams'].append(format_info)
                elif not format_info['has_video'] and format_info['has_audio']:
                    formatted_data['audio_streams'].append(format_info)
            
            # formatStreams（結合された動画+音声）を処理
            format_streams = stream_data.get('formatStreams', [])
            for format_item in format_streams:
                if not format_item.get('url'):
                    continue
                
                format_info = {
                    'url': format_item.get('url', ''),
                    'itag': format_item.get('itag', ''),
                    'container': format_item.get('container', 'mp4'),
                    'quality': self._parse_quality_label(format_item.get('qualityLabel', format_item.get('quality', 'medium'))),
                    'resolution': format_item.get('resolution', ''),
                    'fps': format_item.get('fps', 30),
                    'has_video': True,
                    'has_audio': True
                }
                
                formatted_data['combined_streams'].append(format_info)
            
            # 品質順でソート（数値による高さでソート）
            formatted_data['video_streams'].sort(key=lambda x: x.get('quality_height', 0), reverse=True)
            formatted_data['audio_streams'].sort(key=lambda x: x.get('bitrate', 0), reverse=True)
            # combined_streamsのソート修正（文字列と整数の比較エラー対策）
            formatted_data['combined_streams'].sort(key=lambda x: self._parse_quality_label(x.get('quality', '')), reverse=True)
            
            return formatted_data
            
        except Exception as e:
            logging.error(f"Omada ストリームデータフォーマットエラー: {e}")
            return None
    
    def _parse_format_id(self, format_id: str) -> Dict:
        """format_idから品質と形式情報を解析"""
        result = {
            'quality': 0,
            'format': 'mp4',
            'resolution': 'unknown',
            'has_video': True,
            'has_audio': True
        }
        
        if not format_id:
            return result
        
        format_id_lower = format_id.lower()
        
        # 品質を抽出（360p, 720p, 1080p, 1440p, 2160p）
        if '2160p' in format_id_lower:
            result['quality'] = 2160
            result['resolution'] = '3840x2160'
        elif '1440p' in format_id_lower:
            result['quality'] = 1440
            result['resolution'] = '2560x1440'
        elif '1080p' in format_id_lower:
            result['quality'] = 1080
            result['resolution'] = '1920x1080'
        elif '720p' in format_id_lower:
            result['quality'] = 720
            result['resolution'] = '1280x720'
        elif '480p' in format_id_lower:
            result['quality'] = 480
            result['resolution'] = '854x480'
        elif '360p' in format_id_lower:
            result['quality'] = 360
            result['resolution'] = '640x360'
        elif '240p' in format_id_lower:
            result['quality'] = 240
            result['resolution'] = '426x240'
        
        # 形式を抽出
        if 'webm' in format_id_lower:
            result['format'] = 'webm'
        elif 'mp4' in format_id_lower:
            result['format'] = 'mp4'
        
        # VKR APIの場合、通常は動画と音声が両方含まれる
        # 特別な指定がない限り、両方があると仮定
        result['has_video'] = True
        result['has_audio'] = True
        
        return result
    
    def _parse_quality_label(self, quality_label: str) -> int:
        """品質ラベルから数値を抽出"""
        if not quality_label:
            return 0
        
        quality_map = {
            'small': 240,
            'medium': 360,
            'large': 480,
            'hd720': 720,
            'hd1080': 1080,
            'hd1440': 1440,
            'hd2160': 2160
        }
        
        # 数値が直接含まれている場合（例：720p, 1080p）
        import re
        match = re.search(r'(\d+)', quality_label)
        if match:
            return int(match.group(1))
        
        # テキストラベルから変換
        return quality_map.get(quality_label.lower(), 360)
    
    def _get_quality_from_adaptive_format(self, format_item: Dict) -> str:
        """adaptiveFormatから適切な品質ラベルを生成"""
        # 数値変換を安全に行う
        try:
            height = int(format_item.get('height', 0)) if format_item.get('height') else 0
        except (ValueError, TypeError):
            height = 0
            
        try:
            width = int(format_item.get('width', 0)) if format_item.get('width') else 0
        except (ValueError, TypeError):
            width = 0
            
        try:
            fps = int(format_item.get('fps', 30)) if format_item.get('fps') else 30
        except (ValueError, TypeError):
            fps = 30
        
        # 高さベースの品質判定
        if height >= 2160:
            quality = "2160p"  # 4K
        elif height >= 1440:
            quality = "1440p"  # 2K
        elif height >= 1080:
            quality = "1080p"  # Full HD
        elif height >= 720:
            quality = "720p"   # HD
        elif height >= 480:
            quality = "480p"   # SD
        elif height >= 360:
            quality = "360p"   # Low
        elif height >= 240:
            quality = "240p"   # Very Low
        else:
            # 高さが不明な場合、bitrateから推定
            try:
                bitrate = int(format_item.get('bitrate', 0)) if format_item.get('bitrate') else 0
            except (ValueError, TypeError):
                bitrate = 0
                
            if bitrate > 5000000:      # 5Mbps以上
                quality = "1080p"
            elif bitrate > 2500000:    # 2.5Mbps以上
                quality = "720p"
            elif bitrate > 1000000:    # 1Mbps以上
                quality = "480p"
            elif bitrate > 500000:     # 500kbps以上
                quality = "360p"
            else:
                quality = "240p"
        
        # フレームレートが60fpsの場合は表示に追加
        if fps and fps >= 60:
            quality += "60"
        
        return quality
    
    def get_best_quality_streams(self, youtube_url: str) -> Optional[Dict]:
        """最高品質の動画・音声ストリームを取得"""
        stream_data = self.get_stream_urls(youtube_url)
        if not stream_data:
            return None
        
        video_id = self.get_video_id_from_url(youtube_url)
        if not video_id:
            logging.warning(f"動画IDを取得できませんでした: {youtube_url}")
            return None
        formatted_data = self.format_stream_data(stream_data, video_id)
        
        if not formatted_data:
            return None
        
        result = {
            'videoId': video_id,
            'title': formatted_data.get('title', ''),
            'thumbnail': formatted_data.get('thumbnail', ''),
            'duration': formatted_data.get('duration', ''),
            'uploader': formatted_data.get('uploader', ''),
            'best_video': None,
            'best_audio': None,
            'combined_stream': None,
            'all_formats': formatted_data
        }
        
        # 最高品質の動画ストリームを選択
        if formatted_data['video_streams']:
            result['best_video'] = formatted_data['video_streams'][0]
        
        # 最高品質の音声ストリームを選択
        if formatted_data['audio_streams']:
            result['best_audio'] = formatted_data['audio_streams'][0]
        
        # 組み合わせストリーム（利用可能な場合）
        if formatted_data['combined_streams']:
            result['combined_stream'] = formatted_data['combined_streams'][0]
        
        return result