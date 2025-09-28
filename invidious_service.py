import requests
import logging
import time
from functools import lru_cache
from config import INVIDIOUS_INSTANCES, REQUEST_TIMEOUT
import random

class InvidiousService:
    def __init__(self):
        self.instances = INVIDIOUS_INSTANCES.copy()
        # 優先インスタンスを使用するため、シャッフルしない
        self._cache = {}
        self._cache_timeout = 300  # 5分間キャッシュ
        self._failed_instances = {}  # 失敗したインスタンスを一時的に記録
        self._failure_timeout = 60  # 1分間は失敗したインスタンスを避ける（高速化）
    
    def _make_request(self, endpoint, params=None, max_instances=5):
        """複数のインスタンスでリクエストを試行（キャッシュ付き、高速化のため制限付き）"""
        # キャッシュキーを作成
        cache_key = f"{endpoint}:{str(params) if params else ''}"
        current_time = time.time()
        
        # キャッシュチェック
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if current_time - timestamp < self._cache_timeout:
                return cached_data
        
        # キャッシュがない場合はAPIリクエスト（高速化のため制限）
        tried_instances = 0
        for instance in self.instances:
            if tried_instances >= max_instances:
                logging.debug(f"最大インスタンス数({max_instances})に達したため停止")
                break
            tried_instances += 1
            # 失敗したインスタンスを一時的に避ける
            if instance in self._failed_instances:
                failure_time = self._failed_instances[instance]
                if current_time - failure_time < self._failure_timeout:
                    continue
                else:
                    # タイムアウト経過後は再試行
                    del self._failed_instances[instance]
            
            try:
                url = f"{instance.rstrip('/')}/api/v1/{endpoint}"
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    data = response.json()
                    # データが辞書またはリスト形式であることを確認。検索結果はリスト、動画情報は辞書
                    if isinstance(data, (dict, list)):
                        # キャッシュに保存
                        self._cache[cache_key] = (data, current_time)
                        return data
                    else:
                        logging.debug(f"予期しないデータ形式を受信: {instance} - {type(data)}")
                        self._failed_instances[instance] = current_time
                        continue
                else:
                    # HTTPエラーも記録
                    self._failed_instances[instance] = current_time
            except Exception as e:
                logging.warning(f"インスタンス {instance} でエラー: {e}")
                self._failed_instances[instance] = current_time
                continue
        
        logging.warning(f"試行した{tried_instances}個のInvidiousインスタンスで失敗しました")
        return None
    
    def search_videos(self, query, page=1, sort_by='relevance'):
        """動画検索（高速化版）"""
        params = {
            'q': query,
            'page': page,
            'sort_by': sort_by,
            'type': 'video'
        }
        
        try:
            # 高速化のため最大3インスタンスのみ試行
            results = self._make_request('search', params, max_instances=3)
            return results if results else []
        except Exception as e:
            logging.debug(f"検索エラー: {e}")
            return []

    def search_all(self, query, page=1, sort_by='relevance'):
        """動画とチャンネルを両方検索（高速化版）"""
        params = {
            'q': query,
            'page': page,
            'sort_by': sort_by,
            'type': 'all'
        }
        
        try:
            # 高速化のため最大3インスタンスのみ試行
            results = self._make_request('search', params, max_instances=3)
            if results:
                # 結果をタイプ別に分離
                videos = [item for item in results if item.get('type') == 'video']
                channels = [item for item in results if item.get('type') == 'channel']
                return {
                    'videos': videos,
                    'channels': channels
                }
            return {'videos': [], 'channels': []}
        except Exception as e:
            logging.error(f"統合検索エラー: {e}")
            return {'videos': [], 'channels': []}
    
    def get_video_info(self, video_id):
        """動画情報取得"""
        try:
            return self._make_request(f'videos/{video_id}')
        except Exception as e:
            logging.error(f"動画情報取得エラー: {e}")
            return None
    
    def get_video_formats(self, video_id):
        """動画フォーマット取得"""
        try:
            video_info = self.get_video_info(video_id)
            if video_info and 'formatStreams' in video_info:
                return video_info['formatStreams']
            return []
        except Exception as e:
            logging.error(f"フォーマット取得エラー: {e}")
            return []
    
    def get_stream_urls(self, video_id):
        """Invidiousから直接ストリームURLを取得"""
        try:
            video_info = self.get_video_info(video_id)
            if not video_info:
                return None
            
            # フォーマットストリームを取得
            format_streams = video_info.get('formatStreams', [])
            adaptive_formats = video_info.get('adaptiveFormats', [])
            
            formats = []
            
            # 通常のフォーマット（音声付き） - 全て音声付きとして扱う
            for fmt in format_streams:
                if fmt.get('url') and fmt.get('qualityLabel'):
                    quality = fmt['qualityLabel']
                    # 全ての format_streams は音声付きとして扱う（YouTubeの仕様）
                    formats.append({
                        'url': fmt['url'],
                        'quality': quality,
                        'resolution': fmt.get('resolution', f"{fmt.get('width', '?')}x{fmt.get('height', '?')}"),
                        'has_audio': True,  # formatStreamsは音声付き
                        'audio_url': None,  # 音声は統合済み
                        'bitrate': fmt.get('bitrate', 0),
                        'fps': fmt.get('fps', 30),
                        'ext': fmt.get('container', 'mp4')
                    })
            
            # アダプティブフォーマット（高品質、音声分離）
            video_formats = [f for f in adaptive_formats if f.get('type', '').startswith('video/')]
            audio_formats = [f for f in adaptive_formats if f.get('type', '').startswith('audio/')]
            
            # 最高品質の音声を取得
            best_audio = None
            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get('bitrate', 0))
            
            # 動画フォーマットを追加
            for fmt in video_formats:
                if fmt.get('url') and fmt.get('qualityLabel'):
                    formats.append({
                        'url': fmt['url'],
                        'quality': fmt['qualityLabel'],
                        'resolution': fmt.get('resolution', f"{fmt.get('width', '?')}x{fmt.get('height', '?')}"),
                        'has_audio': False,
                        'audio_url': best_audio['url'] if best_audio else None,
                        'bitrate': fmt.get('bitrate', 0),
                        'fps': fmt.get('fps', 30),
                        'ext': fmt.get('container', 'mp4')
                    })
            
            # アダプティブフォーマットに音声URLを設定（音声が分離されている場合）
            if best_audio:
                for fmt in formats:
                    if not fmt['has_audio'] and fmt.get('audio_url') is None:
                        fmt['audio_url'] = best_audio['url']
            
            # 重複を除去し、品質でソート（音声付き優先）
            unique_formats = []
            seen_qualities = set()
            
            # 音声付きフォーマットを最初に処理
            for fmt in formats:
                if fmt['has_audio'] and fmt['quality'] not in seen_qualities:
                    seen_qualities.add(fmt['quality'])
                    unique_formats.append(fmt)
            
            # 次に音声分離フォーマットを処理（音声URLがある場合のみ）
            for fmt in formats:
                if not fmt['has_audio'] and fmt.get('audio_url') and fmt['quality'] not in seen_qualities:
                    seen_qualities.add(fmt['quality'])
                    unique_formats.append(fmt)
            
            # 品質順でソート（数字を抽出して降順）
            def extract_quality_number(quality):
                import re
                match = re.search(r'(\d+)', quality)
                return int(match.group(1)) if match else 0
            
            unique_formats.sort(key=lambda x: extract_quality_number(x['quality']), reverse=True)
            
            if not unique_formats:
                return None
            
            # 最良のストリーム（音声付き優先、高品質優先）を選択
            best_stream = unique_formats[0]
            logging.info(f"選択されたストリーム: {best_stream['quality']}, 音声: {best_stream['has_audio']}")
            
            final_formats = unique_formats
            
            return {
                'title': video_info.get('title', ''),
                'duration': video_info.get('lengthSeconds', 0),
                'thumbnail': video_info.get('videoThumbnails', [{}])[0].get('url', ''),
                'uploader': video_info.get('author', ''),
                'best_url': best_stream['url'],
                'has_audio': best_stream['has_audio'],
                'audio_url': best_stream['audio_url'],
                'formats': final_formats
            }
            
        except Exception as e:
            logging.error(f"Invidiousストリーム取得エラー: {e}")
            return None
    
    def get_channel_info(self, channel_id):
        """チャンネル情報を取得"""
        try:
            endpoint = f"api/v1/channels/{channel_id}"
            
            # 各インスタンスで試行
            for instance in self.instances:
                try:
                    url = f"{instance}{endpoint}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            'author': data.get('author', ''),
                            'authorId': data.get('authorId', channel_id),
                            'description': data.get('description', ''),
                            'subCount': data.get('subCount', 0),
                            'totalViews': data.get('totalViews', 0),
                            'videoCount': data.get('videoCount', 0),
                            'joined': data.get('joined', 0),
                            'authorThumbnails': data.get('authorThumbnails', []),
                            'authorBanners': data.get('authorBanners', []),
                            'autoGenerated': data.get('autoGenerated', False)
                        }
                except requests.RequestException as e:
                    logging.warning(f"チャンネル情報取得失敗 {instance}: {e}")
                    continue
                    
            logging.error(f"全てのインスタンスでチャンネル情報取得に失敗: {channel_id}")
            return None
            
        except Exception as e:
            logging.error(f"チャンネル情報取得エラー: {str(e)}")
            return None
    
    def get_channel_videos(self, channel_id, page=1, sort='newest'):
        """チャンネルの動画一覧を取得"""
        try:
            endpoint = f"/api/v1/channels/{channel_id}/videos"
            params = {
                'page': page,
                'sort_by': sort
            }
            data = self._make_request(endpoint, params)
            
            if data:
                videos = []
                for video in data:
                    videos.append({
                        'videoId': video.get('videoId', ''),
                        'title': video.get('title', ''),
                        'description': video.get('description', ''),
                        'videoThumbnails': video.get('videoThumbnails', []),
                        'lengthSeconds': video.get('lengthSeconds', 0),
                        'viewCount': video.get('viewCount', 0),
                        'author': video.get('author', ''),
                        'authorId': video.get('authorId', ''),
                        'publishedText': video.get('publishedText', ''),
                        'published': video.get('published', 0)
                    })
                return videos
        except Exception as e:
            logging.error(f"チャンネル動画取得エラー: {str(e)}")
            return []

    def get_trending_videos(self, region='JP'):
        """トレンド動画を取得（件数を増加）"""
        try:
            # 通常のトレンド動画を取得
            endpoint = "trending"
            params = {'region': region}
            data = self._make_request(endpoint, params)
            
            all_videos = []
            if data:
                for video in data[:30]:  # 30件に増加
                    all_videos.append({
                        'videoId': video.get('videoId', ''),
                        'title': video.get('title', ''),
                        'description': video.get('description', ''),
                        'videoThumbnails': video.get('videoThumbnails', []),
                        'lengthSeconds': video.get('lengthSeconds', 0),
                        'viewCount': video.get('viewCount', 0),
                        'author': video.get('author', ''),
                        'authorId': video.get('authorId', ''),
                        'publishedText': video.get('publishedText', ''),
                        'published': video.get('published', 0)
                    })
            
            # 追加のカテゴリからも取得
            try:
                for category in ['Music', 'Gaming']:
                    cat_params = {'region': region, 'type': category}
                    cat_data = self._make_request(endpoint, cat_params)
                    if cat_data:
                        for video in cat_data[:10]:
                            all_videos.append({
                                'videoId': video.get('videoId', ''),
                                'title': video.get('title', ''),
                                'description': video.get('description', ''),
                                'videoThumbnails': video.get('videoThumbnails', []),
                                'lengthSeconds': video.get('lengthSeconds', 0),
                                'viewCount': video.get('viewCount', 0),
                                'author': video.get('author', ''),
                                'authorId': video.get('authorId', ''),
                                'publishedText': video.get('publishedText', ''),
                                'published': video.get('published', 0)
                            })
            except:
                pass
                
            return all_videos
        except Exception as e:
            logging.error(f"トレンド動画取得エラー: {str(e)}")
            return []

    def get_video_comments(self, video_id, continuation=None):
        """動画のコメントを取得"""
        try:
            endpoint = f"comments/{video_id}"
            params = {}
            if continuation:
                params['continuation'] = continuation
                
            data = self._make_request(endpoint, params)
            
            if data:
                comments = []
                for comment in data.get('comments', []):
                    # コメント投稿者のアイコン取得（フォールバック付き）
                    author_thumbnails = comment.get('authorThumbnails', [])
                    author_id = comment.get('authorId', '')
                    author_name = comment.get('author', '')
                    
                    # アイコンデータが空の場合はフォールバック処理
                    if not author_thumbnails and author_id:
                        # チャンネルIDからアイコンURLを生成
                        author_thumbnails = [
                            {
                                'url': f'https://yt3.ggpht.com/ytc/{author_id}=s88-c-k-c0x00ffffff-no-rj',
                                'width': 88,
                                'height': 88
                            },
                            {
                                'url': f'https://yt3.ggpht.com/ytc/{author_id}=s176-c-k-c0x00ffffff-no-rj',
                                'width': 176,
                                'height': 176
                            }
                        ]
                    elif not author_thumbnails:
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
                    
                    comments.append({
                        'author': author_name,
                        'authorId': author_id,
                        'authorThumbnails': author_thumbnails,
                        'authorThumbnail': authorThumbnail,  # HTMLテンプレート用のメインアイコンURL
                        'content': comment.get('content', ''),
                        'published': comment.get('published', 0),
                        'publishedText': comment.get('publishedText', ''),
                        'likeCount': comment.get('likeCount', 0),
                        'replies': comment.get('replies', {}).get('replyCount', 0),
                        'isOwner': comment.get('authorIsChannelOwner', False),
                        'isPinned': comment.get('isPinned', False)
                    })
                
                return {
                    'comments': comments,
                    'continuation': data.get('continuation'),
                    'commentCount': data.get('commentCount', 0)
                }
            return {'comments': [], 'continuation': None, 'commentCount': 0}
        except Exception as e:
            logging.error(f"コメント取得エラー: {str(e)}")
            return {'comments': [], 'continuation': None, 'commentCount': 0}
