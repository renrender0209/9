from flask import render_template, request, jsonify, redirect, url_for
from app import app
from invidious_service import InvidiousService
import datetime
from piped_service import PipedService
from ytdl_service import YtdlService
from additional_services import AdditionalStreamServices
from turbo_video_service import TurboVideoService
from multi_stream_service import MultiStreamService
from custom_api_service import CustomApiService
from vkr_downloader_service import OmadaVideoService
from user_preferences import user_prefs
import requests
import logging
import json
import urllib.parse

@app.template_filter('format_view_count')
def format_view_count(count):
    """再生回数を日本語形式でフォーマット"""
    if not count or count == 0:
        return 'N/A'
    
    try:
        count = int(count)
        if count >= 100000000:  # 1億以上
            return f"{count // 100000000}億{(count % 100000000) // 10000:,}万" if (count % 100000000) // 10000 > 0 else f"{count // 100000000}億"
        elif count >= 10000:  # 1万以上
            return f"{count // 10000}万{count % 10000:,}" if count % 10000 > 0 else f"{count // 10000}万"
        else:
            return f"{count:,}"
    except (ValueError, TypeError):
        return 'N/A'

@app.template_filter('format_view_count_with_suffix')
def format_view_count_with_suffix(count):
    """再生回数を「回視聴」付きでフォーマット"""
    formatted = format_view_count(count)
    if formatted == 'N/A':
        return '視聴回数不明'
    return f"{formatted}回視聴"

@app.template_filter('format_duration_japanese')
def format_duration_japanese_filter(seconds):
    """テンプレート用の動画時間日本語フォーマット"""
    return format_duration_japanese(seconds)

@app.template_filter('format_published_japanese')
def format_published_japanese_filter(published_text):
    """テンプレート用の公開日日本語フォーマット"""
    return format_published_japanese(published_text)

def format_duration_japanese(seconds):
    """動画時間を日本語形式でフォーマット（例：28秒、4分28秒、1時間30分）"""
    if not seconds or seconds == 0:
        return ''
    
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            if minutes > 0:
                return f"{hours}時間{minutes}分"
            else:
                return f"{hours}時間"
        elif minutes > 0:
            if secs > 0:
                return f"{minutes}分{secs}秒"
            else:
                return f"{minutes}分"
        else:
            return f"{secs}秒"
    except (ValueError, TypeError):
        return ''

def format_published_japanese(published_text):
    """公開日を日本語形式でフォーマット"""
    if not published_text:
        return ''
    
    try:
        # ISO形式の日付を解析
        if 'T' in published_text and published_text.endswith('Z'):
            from datetime import datetime, timezone
            published_date = datetime.fromisoformat(published_text.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            diff = now - published_date
            
            # 時間差を日本語で表現
            if diff.days >= 365:
                years = diff.days // 365
                return f"{years}年前"
            elif diff.days >= 30:
                months = diff.days // 30
                return f"{months}ヶ月前"
            elif diff.days > 0:
                return f"{diff.days}日前"
            elif diff.seconds >= 3600:
                hours = diff.seconds // 3600
                return f"{hours}時間前"
            elif diff.seconds >= 60:
                minutes = diff.seconds // 60
                return f"{minutes}分前"
            else:
                return "たった今"
        else:
            # 既に日本語形式の場合はそのまま返す
            return published_text
            
    except Exception as e:
        logging.warning(f"日付フォーマットエラー: {published_text}, エラー: {e}")
        return published_text

invidious = InvidiousService()
piped = PipedService()
ytdl = YtdlService()
additional_services = AdditionalStreamServices()
turbo_service = TurboVideoService()
multi_stream_service = MultiStreamService()
custom_api_service = CustomApiService()
video_service = OmadaVideoService()

def suggest(keyword: str):
    """Google/YouTube検索予測変換API"""
    try:
        url = f"http://www.google.com/complete/search?client=youtube&hl=ja&ds=yt&q={urllib.parse.quote(keyword)}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            # JSONPの形式から実際のJSONデータを抽出
            json_text = response.text[19:-1]  # 前後の不要な部分を削除
            data = json.loads(json_text)
            suggestions = [item[0] for item in data[1]]
            return suggestions
        else:
            return []
    except Exception as e:
        logging.error(f"検索予測変換エラー: {e}")
        return []

@app.route('/test')
def test():
    """テスト用診断ページ"""
    import os
    return f'''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <title>診断ページ - れんれんtube</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .status {{ padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .success {{ background: #d4edda; border: 1px solid #c3e6cb; }}
            .info {{ background: #d1ecf1; border: 1px solid #bee5eb; }}
            .danger {{ background: #f8d7da; border: 1px solid #f5c6cb; }}
            h1 {{ color: #333; }}
            pre {{ background: #fff; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <h1>🎬 れんれんtube - 診断ページ</h1>
        
        <div class="status success">
            <h3>✅ Flask アプリケーション動作中</h3>
            <p>このページが表示されていることは、アプリケーションが正常に動作していることを意味します。</p>
        </div>
        
        <div class="status info">
            <h3>📊 システム情報</h3>
            <p><strong>ポート:</strong> 5000</p>
            <p><strong>環境:</strong> Python Flask</p>
            <p><strong>現在時刻:</strong> {datetime.datetime.now()}</p>
        </div>
        
        <div class="status info">
            <h3>🔗 ナビゲーション</h3>
            <p><a href="/" style="color: #007bff;">メインページ（トレンド動画）</a></p>
            <p><a href="/search?q=music" style="color: #007bff;">検索テスト（music）</a></p>
        </div>
        
        <div class="status info">
            <h3>✅ 実装済み機能</h3>
            <ul>
                <li>✓ れんれんtube API統合</li>
                <li>✓ チャンネルページ対応</li>
                <li>✓ ログイン機能削除</li>
                <li>✓ 画質設定追加</li>
                <li>✓ Invidious API機能（コメント・関連動画）</li>
                <li>✓ SNS共有機能（Discord対応）</li>
                <li>✓ フォールバック機能（API失敗時も動画表示）</li>
            </ul>
        </div>
        
        <div class="status info">
            <h3>🚀 開発完了</h3>
            <p>動画ストリーミングアプリケーションの開発が完了しました。</p>
            <p><strong>メインページ</strong>でトレンド動画が表示され、動画視聴、検索、チャンネル閲覧、共有機能が利用できます。</p>
        </div>
    </body>
    </html>
    '''

def get_fallback_trending_videos():
    """フォールバック用のサンプルトレンド動画"""
    return [
        {
            'videoId': 'dQw4w9WgXcQ',
            'title': 'Rick Astley - Never Gonna Give You Up (Official Video)',
            'author': 'Rick Astley',
            'authorId': 'UCuAXFkgsw1L7xaCfnd5JJOw',
            'lengthSeconds': 212,
            'viewCount': 1400000000,
            'publishedText': '1 year ago',
            'videoThumbnails': [
                {'url': 'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg'},
                {'url': 'https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg'}
            ]
        },
        {
            'videoId': 'L_jWHffIx5E',
            'title': 'Smash Mouth - All Star (Official Music Video)',
            'author': 'SmashMouthVEVO',
            'authorId': 'UCN1hnUccO4FD5WfM7ithXaw',
            'lengthSeconds': 201,
            'viewCount': 800000000,
            'publishedText': '2 years ago',
            'videoThumbnails': [
                {'url': 'https://img.youtube.com/vi/L_jWHffIx5E/maxresdefault.jpg'},
                {'url': 'https://img.youtube.com/vi/L_jWHffIx5E/hqdefault.jpg'}
            ]
        },
        {
            'videoId': 'kJQP7kiw5Fk',
            'title': 'Despacito ft. Daddy Yankee',
            'author': 'Luis Fonsi',
            'authorId': 'UCmBA_wu8xGg1OfOkfW13Q0Q',
            'lengthSeconds': 281,
            'viewCount': 8000000000,
            'publishedText': '6 years ago',
            'videoThumbnails': [
                {'url': 'https://img.youtube.com/vi/kJQP7kiw5Fk/maxresdefault.jpg'},
                {'url': 'https://img.youtube.com/vi/kJQP7kiw5Fk/hqdefault.jpg'}
            ]
        },
        {
            'videoId': 'ZEHk7UXxhIs',
            'title': '【実況】最恐の脱出ゲーム「POPPY PLAYTIME」をやる！ Part1',
            'author': 'HikakinGames',
            'authorId': 'UCsFn6flPnvnGLY1JbSnAFIg',
            'lengthSeconds': 1456,
            'viewCount': 5200000,
            'publishedText': '2 months ago',
            'videoThumbnails': [
                {'url': 'https://img.youtube.com/vi/ZEHk7UXxhIs/maxresdefault.jpg'},
                {'url': 'https://img.youtube.com/vi/ZEHk7UXxhIs/hqdefault.jpg'}
            ]
        },
        {
            'videoId': 'WPvGqX-TXP0',
            'title': '【ドッキリ】もしもヒカキンの家の床が全部バナナの皮だったら',
            'author': 'HikakinTV',
            'authorId': 'UCZf__ehlCEBPop-_sldpBUQ',
            'lengthSeconds': 932,
            'viewCount': 3800000,
            'publishedText': '1 month ago',
            'videoThumbnails': [
                {'url': 'https://img.youtube.com/vi/WPvGqX-TXP0/maxresdefault.jpg'},
                {'url': 'https://img.youtube.com/vi/WPvGqX-TXP0/hqdefault.jpg'}
            ]
        }
    ]

@app.route('/')
def index():
    """メインページ - siawaseok APIトレンド表示（フォールバック付き）"""
    trending_videos = []
    
    try:
        # マルチエンドポイントでトレンドを高速取得
        logging.info("高速マルチエンドポイントでトレンド動画を取得中...")
        trend_data = multi_stream_service.get_trending_videos()
        
        if trend_data:
            logging.info(f"siawaseok trend API data type: {type(trend_data)}")
            logging.info(f"siawaseok trend API keys: {list(trend_data.keys()) if isinstance(trend_data, dict) else 'not dict'}")
            
            videos_list = []
            
            # APIレスポンスの構造を確認して適切に処理
            if isinstance(trend_data, dict):
                # siawaseok trend APIの構造: trending, music, gaming, updated
                if 'trending' in trend_data:
                    videos_list = trend_data['trending']
                    logging.info(f"Using 'trending' key with {len(videos_list) if isinstance(videos_list, list) else 'not list'} items")
                elif 'music' in trend_data:
                    videos_list = trend_data['music']
                    logging.info(f"Using 'music' key with {len(videos_list) if isinstance(videos_list, list) else 'not list'} items")
                elif 'gaming' in trend_data:
                    videos_list = trend_data['gaming']
                    logging.info(f"Using 'gaming' key with {len(videos_list) if isinstance(videos_list, list) else 'not list'} items")
                else:
                    # 他のキーを確認
                    for key, value in trend_data.items():
                        if isinstance(value, list) and len(value) > 0:
                            videos_list = value
                            logging.info(f"Using key '{key}' as videos list with {len(value)} items")
                            break
            elif isinstance(trend_data, list):
                videos_list = trend_data
            
            if videos_list:
                seen_ids = set()
                
                for video_data in videos_list[:100]:  # 最大100件に増加
                    if isinstance(video_data, dict):
                        video_id = video_data.get('videoId') or video_data.get('id')
                        
                        if video_id and video_id not in seen_ids:
                            seen_ids.add(video_id)
                            
                            # duration値を安全に変換
                            duration_raw = video_data.get('lengthSeconds') or video_data.get('duration', 0)
                            try:
                                if isinstance(duration_raw, str):
                                    # 時間文字列（例: "3:45"）を秒に変換
                                    if ':' in duration_raw:
                                        parts = duration_raw.split(':')
                                        if len(parts) == 2:  # mm:ss
                                            duration_seconds = int(parts[0]) * 60 + int(parts[1])
                                        elif len(parts) == 3:  # hh:mm:ss
                                            duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                        else:
                                            duration_seconds = 0
                                    else:
                                        duration_seconds = int(duration_raw)
                                else:
                                    duration_seconds = int(duration_raw) if duration_raw else 0
                            except (ValueError, TypeError):
                                duration_seconds = 0

                            # viewCount値を安全に変換
                            view_count_raw = video_data.get('viewCount') or video_data.get('view_count', 0)
                            try:
                                view_count = int(view_count_raw) if view_count_raw else 0
                            except (ValueError, TypeError):
                                view_count = 0

                            # チャンネル名とIDを適切に取得（siawaseok APIの実際の構造に合わせて）
                            author_name = None
                            author_id = None
                            
                            # siawaseok APIの構造に基づいた取得
                            if video_data.get('author'):
                                author_name = video_data['author']
                            elif video_data.get('uploader'):
                                author_name = video_data['uploader']
                            elif video_data.get('uploaderName'):  # siawaseok APIで使われる可能性
                                author_name = video_data['uploaderName']
                            elif video_data.get('channel'):
                                if isinstance(video_data['channel'], dict):
                                    author_name = video_data['channel'].get('name') or video_data['channel'].get('title')
                                elif isinstance(video_data['channel'], str):
                                    author_name = video_data['channel']
                            elif video_data.get('channelName'):  # siawaseok APIで使われる可能性
                                author_name = video_data['channelName']
                            
                            # チャンネルIDを取得
                            if video_data.get('authorId'):
                                author_id = video_data['authorId']
                            elif video_data.get('uploader_id'):
                                author_id = video_data['uploader_id']
                            elif video_data.get('uploaderId'):  # siawaseok APIで使われる可能性
                                author_id = video_data['uploaderId']
                            elif video_data.get('channelId'):  # siawaseok APIで使われる可能性
                                author_id = video_data['channelId']
                            elif video_data.get('channel') and isinstance(video_data['channel'], dict):
                                author_id = video_data['channel'].get('id') or video_data['channel'].get('channelId')
                            
                            # デフォルト値設定
                            if not author_name:
                                author_name = 'チャンネル名不明'
                            if not author_id:
                                author_id = ''

                            # 統一された動画形式に変換
                            video = {
                                'videoId': video_id,
                                'title': video_data.get('title', f'Video {video_id}'),
                                'author': author_name,
                                'authorId': author_id,
                                'lengthSeconds': duration_seconds,
                                'viewCount': view_count,
                                'publishedText': video_data.get('publishedText') or video_data.get('upload_date', ''),
                                'videoThumbnails': [
                                    {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'},
                                    {'url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'}
                                ]
                            }
                            trending_videos.append(video)
            
                logging.info(f"Processed {len(trending_videos)} trending videos from siawaseok API")
            else:
                logging.warning("No videos found in siawaseok trend data")
                
    except Exception as e:
        logging.error(f"siawaseok API接続エラー: {e}")
    
    # siawaseok APIで動画が取得できなかった場合のフォールバック
    if not trending_videos:
        logging.info("siawaseok APIからデータ取得できず、フォールバックデータを使用")
        try:
            # まずInvidiousからトレンドを取得
            trending_videos = invidious.get_trending_videos()
            logging.info(f"Invidious APIから {len(trending_videos)} 件のトレンド動画を取得")
        except Exception as e2:
            logging.error(f"Invidious APIも失敗: {e2}")
            # 最終フォールバック: サンプル動画を表示
            trending_videos = get_fallback_trending_videos()
            logging.info(f"フォールバックサンプル動画 {len(trending_videos)} 件を表示")
    
    return render_template('index.html', trending_videos=trending_videos)

@app.route('/search')
def search():
    # リクエスト開始時にキャッシュをクリア（パフォーマンス向上）
    multi_stream_service.clear_request_cache()
    
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    
    if not query:
        return redirect(url_for('index'))
    
    try:
        # 🆕 カスタムAPIサービス（siawaseok.duckdns.org）から検索結果を最優先取得
        logging.info(f"検索クエリ: '{query}' - CustomApiService (siawaseok.duckdns.org) を使用（最優先）")
        
        search_videos = []
        channels = []
        
        # 1. 高速化: まずKahoot APIで検索（最も安定）
        try:
            max_results = 50 if page == 1 else 30  # 1ページ目は多め
            kahoot_results = multi_stream_service.search_videos_with_kahoot(query, max_results=max_results, page=page)
            
            if kahoot_results:
                search_videos = kahoot_results
                logging.info(f"✅ 高速化: Kahoot APIから {len(search_videos)} 件の検索結果を取得")
            
        except Exception as e:
            logging.warning(f"Kahoot API検索エラー: {e}")
        
        # 2. フォールバック: CustomApiService（Kahoot APIが失敗した場合のみ）
        if not search_videos:
            try:
                custom_search_data = custom_api_service.search_videos(query)
                
                if custom_search_data:
                    custom_videos = custom_api_service.format_search_results(custom_search_data)
                    if custom_videos:
                        search_videos = custom_videos
                        logging.info(f"✅ フォールバック: CustomApiService (siawaseok.duckdns.org) から {len(search_videos)} 件の検索結果を取得")
                
            except Exception as e:
                logging.warning(f"CustomApiService検索エラー: {e}")
        
        # 3. 🚀 高速化: Invidiousは検索結果が少ない場合のみ補完で使用
        if len(search_videos) < 10:  # 十分な結果がある場合はInvidiousをスキップ
            try:
                logging.info(f"Invidiousからチャンネル情報と補完動画を取得: '{query}'")
                search_results = invidious.search_all(query, page=page)
                
                if isinstance(search_results, dict):
                    invidious_videos = search_results.get('videos', [])
                    channels = search_results.get('channels', [])  # チャンネル情報は常に取得
                    
                    # Kahoot APIの結果と重複しないものを追加
                    kahoot_video_ids = set(v.get('videoId') for v in search_videos)
                    for video in invidious_videos:
                        if video.get('videoId') not in kahoot_video_ids:
                            search_videos.append(video)
                    
                    logging.info(f"Invidiousから追加動画 {len(invidious_videos)} 件、チャンネル {len(channels)} 件を取得")
                    
                elif search_results:  # 動画のみのリスト
                    invidious_videos = search_results
                    # 重複回避
                    kahoot_video_ids = set(v.get('videoId') for v in search_videos)
                    for video in invidious_videos:
                        if video.get('videoId') not in kahoot_video_ids:
                            search_videos.append(video)
                    logging.info(f"Invidiousから追加動画 {len(invidious_videos)} 件を取得")
                
            except Exception as e:
                logging.debug(f"Invidious API検索エラー: {e}")
                # 高速化のため、チャンネル情報の追加取得はスキップ
        else:
            logging.info(f"十分な検索結果({len(search_videos)}件)があるため、Invidiousをスキップ")
        
        # 4. 最終フォールバック: 検索結果が極端に少ない場合のみsiawaseok APIを試す
        if not search_videos or len(search_videos) < 3:
            try:
                logging.info(f"最終フォールバック: マルチエンドポイント検索使用 - {query}")
                
                search_data = multi_stream_service.search_videos(query, 1)
                
                if search_data:
                    videos_list = []
                    if isinstance(search_data, dict) and 'results' in search_data:
                        videos_list = search_data['results']
                    elif isinstance(search_data, list):
                        videos_list = search_data
                    
                    if videos_list:
                        # 重複回避
                        existing_video_ids = set(v.get('videoId') for v in search_videos)
                        added_count = 0
                        
                        for video_data in videos_list[:20]:
                            if isinstance(video_data, dict):
                                video_id = video_data.get('videoId') or video_data.get('id')
                                if video_id and video_id not in existing_video_ids:
                                    existing_video_ids.add(video_id)
                                    search_videos.append({
                                        'videoId': video_id,
                                        'title': video_data.get('title', f'Video {video_id}'),
                                        'author': video_data.get('author', 'Unknown'),
                                        'authorId': video_data.get('authorId', ''),
                                        'lengthSeconds': video_data.get('lengthSeconds', 0),
                                        'viewCount': video_data.get('viewCount', 0),
                                        'publishedText': video_data.get('publishedText', ''),
                                        'videoThumbnails': [
                                            {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'}
                                        ]
                                    })
                                    added_count += 1
                        logging.info(f"siawaseok APIから追加で {added_count} 件を取得")
            except Exception as e2:
                logging.error(f"siawaseok フォールバックエラー: {e2}")
        
        # タイトルと投稿時間の改善処理
        improved_videos = []
        for video in search_videos:
            # タイトルをInvidious APIから確実に取得
            title = video.get('title', '')
            if not title or title == 'Unknown':
                title = f'動画 {video.get("videoId", "")}'
            
            # 投稿時間を正確に取得
            published_text = video.get('publishedText', '')
            if not published_text or published_text == 'Unknown':
                published = video.get('published', 0)
                if published:
                    from datetime import datetime, timedelta
                    try:
                        published_date = datetime.fromtimestamp(published)
                        now = datetime.now()
                        diff = now - published_date
                        if diff.days > 365:
                            years = diff.days // 365
                            published_text = f"{years}年前"
                        elif diff.days > 30:
                            months = diff.days // 30
                            published_text = f"{months}か月前"
                        elif diff.days > 0:
                            published_text = f"{diff.days}日前"
                        else:
                            hours = diff.seconds // 3600
                            published_text = f"{hours}時間前" if hours > 0 else "1時間未満前"
                    except:
                        published_text = "投稿日時不明"
            
            improved_video = video.copy()
            improved_video['title'] = title
            improved_video['publishedText'] = published_text
            improved_videos.append(improved_video)
        
        # Invidiousの場合、1ページあたり20件が標準なので、最大20ページまで表示
        results_per_page = 20
        total_pages = 20  # 最大20ページ
        has_next = len(improved_videos) >= results_per_page and page < total_pages
        has_prev = page > 1
        
        return render_template('search.html', 
                             results=improved_videos,
                             channels=channels,
                             query=query, 
                             page=page,
                             total_pages=total_pages,
                             total_results=len(improved_videos),
                             has_next=has_next,
                             has_prev=has_prev)
    except Exception as e:
        logging.error(f"検索処理エラー: {e}")
        return render_template('search.html', 
                             results=[], 
                             channels=[],
                             query=query, 
                             page=page)

@app.route('/api/search')
def api_search():
    """Ajax検索API - JSON形式で高速検索結果を返す"""
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    
    if not query:
        return jsonify({'error': 'クエリが必要です'}), 400
    
    try:
        logging.info(f"Ajax検索: '{query}' - ページ {page}")
        multi_stream_service.clear_request_cache()
        
        search_videos = []
        channels = []
        
        # 1. 高速検索: Kahoot API優先
        try:
            max_results = 30
            kahoot_results = multi_stream_service.search_videos_with_kahoot(query, max_results=max_results, page=page)
            
            if kahoot_results:
                search_videos = kahoot_results
                logging.info(f"✅ Ajax検索: Kahoot APIから {len(search_videos)} 件を高速取得")
        except Exception as e:
            logging.warning(f"Ajax Kahoot検索エラー: {e}")
        
        # 2. チャンネル情報を補完
        if len(search_videos) >= 10:  # 十分な結果がある場合
            try:
                search_results = invidious.search_all(query, page=page)
                if isinstance(search_results, dict) and 'channels' in search_results:
                    channels = search_results['channels'][:5]  # 最大5チャンネル
                    logging.info(f"✅ Ajax検索: チャンネル {len(channels)} 件を追加")
            except Exception as e:
                logging.debug(f"Ajax Invidiousチャンネル取得エラー: {e}")
        
        return jsonify({
            'videos': search_videos,
            'channels': channels,
            'query': query,
            'page': page
        })
    
    except Exception as e:
        logging.error(f"Ajax検索処理エラー: {e}")
        return jsonify({'error': '検索中にエラーが発生しました'}), 500

@app.route('/api/comments/<video_id>')
def get_comments(video_id):
    """コメント取得API - siawaseok APIからコメントを取得"""
    try:
        # siawaseok APIからコメントを取得
        api_url = f"https://siawaseok.duckdns.org/api/comments/{video_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"✅ siawaseok APIからコメント取得成功: {video_id}")
            return jsonify({
                'success': True,
                'comments': data,
                'source': 'siawaseok'
            })
        else:
            logging.warning(f"siawaseok APIコメント取得失敗: {response.status_code}")
    except Exception as e:
        logging.error(f"siawaseok APIコメント取得エラー: {e}")
    
    # フォールバック: 空のコメントリストを返す
    return jsonify({
        'success': False,
        'comments': [],
        'source': 'fallback'
    })

@app.route('/api/invidious-comments/<video_id>')
def get_invidious_comments(video_id):
    """Invidiousからコメント取得"""
    try:
        invidious_comments = invidious.get_comments(video_id)
        
        if invidious_comments:
            logging.info(f"✅ Invidiousからコメント取得成功: {len(invidious_comments)} 件")
            return jsonify({
                'success': True,
                'comments': invidious_comments,
                'source': 'invidious'
            })
    except Exception as e:
        logging.error(f"Invidiousコメント取得エラー: {e}")
    
    return jsonify({
        'success': False,
        'comments': [],
        'source': 'invidious'
    })

@app.route('/api/comments/<comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    """コメントいいね機能"""
    try:
        # 簡単な実装：現在のいいね数を返す（実際のデータベース更新は省略）
        return jsonify({
            'success': True,
            'likes': 1,  # 固定値
            'message': 'いいねしました'
        })
    except Exception as e:
        logging.error(f"コメントいいねエラー: {e}")
        return jsonify({
            'success': False,
            'message': 'いいねに失敗しました'
        }), 500

@app.route('/api/video-author/<video_id>')
def get_video_author_info(video_id):
    """Invidious APIから動画投稿者の情報とアイコンを取得"""
    try:
        # Invidiousから動画詳細を取得
        video_info = invidious.get_video_info(video_id)
        
        if video_info:
            author_info = {
                'author': video_info.get('author', 'Unknown Author'),
                'authorId': video_info.get('authorId', ''),
                'authorUrl': video_info.get('authorUrl', ''),
                'authorThumbnails': video_info.get('authorThumbnails', [])
            }
            
            # 投稿者のアイコンURLを取得（最高品質優先）
            avatar_url = ''
            if author_info['authorThumbnails']:
                # 最大サイズのサムネイルを選択
                thumbnails = sorted(author_info['authorThumbnails'], 
                                  key=lambda x: x.get('width', 0) * x.get('height', 0), 
                                  reverse=True)
                if thumbnails:
                    avatar_url = thumbnails[0].get('url', '')
            
            author_info['avatar_url'] = avatar_url
            
            logging.info(f"✅ 動画投稿者情報取得成功: {video_id} - {author_info['author']}")
            return jsonify({
                'success': True,
                'author_info': author_info,
                'source': 'invidious'
            })
        else:
            logging.warning(f"Invidious動画情報取得失敗: {video_id}")
    except Exception as e:
        logging.error(f"動画投稿者情報取得エラー: {e}")
    
    return jsonify({
        'success': False,
        'author_info': None,
        'source': 'invidious'
    })

@app.route('/api/siawaseok-comments/<video_id>')
def get_siawaseok_comments(video_id):
    """siawaseok APIからコメント取得"""
    try:
        api_url = f"https://siawaseok.duckdns.org/api/comments/{video_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"✅ siawaseok APIからコメント取得成功: {video_id} - {len(data)} 件")
            return jsonify({
                'success': True,
                'comments': data,
                'source': 'siawaseok'
            })
        else:
            logging.warning(f"siawaseok APIコメント取得失敗: {response.status_code}")
    except Exception as e:
        logging.error(f"siawaseok APIコメント取得エラー: {e}")
    
    return jsonify({
        'success': False,
        'comments': [],
        'source': 'siawaseok'
    })

@app.route('/api/omada-comments/<video_id>')
def get_omada_comments(video_id):
    """yt.omada.cafe APIからコメント取得"""
    try:
        api_url = f"https://yt.omada.cafe/api/v1/comments/{video_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # omada APIのコメント構造に対応
            comments = data.get('comments', [])
            logging.info(f"✅ omada APIからコメント取得成功: {video_id} - {len(comments)} 件")
            return jsonify({
                'success': True,
                'comments': comments,
                'source': 'omada'
            })
        else:
            logging.warning(f"omada APIコメント取得失敗: {response.status_code}")
    except Exception as e:
        logging.error(f"omada APIコメント取得エラー: {e}")
    
    return jsonify({
        'success': False,
        'comments': [],
        'source': 'omada'
    })

@app.route('/watch')
def watch():
    """動画視聴ページ - siawaseok API専用版"""
    video_id = request.args.get('v')
    if not video_id:
        return redirect(url_for('index'))
    
    try:
        # 🚀 超高速並列処理: 全てのAPIリクエストを同時に開始
        import concurrent.futures
        import threading
        
        logging.info(f"🚀 超高速並列処理開始: {video_id}")
        
        # 並列処理用の結果保存
        results = {}
        
        def get_omada_api_info():
            """🚀 yt.omada.cafe API - 最優先（多品質対応）"""
            try:
                if video_id:  # video_idの存在を確認
                    # 🚀 多品質ストリーム取得 (360p, 480p, 720p, 1080p)
                    target_qualities = ['360p', '480p', '720p', '1080p']
                    omada_data = video_service.get_stream_urls(video_id, target_qualities)
                    if omada_data:
                        results['omada_api'] = omada_data
                        logging.info(f"✅ Omada API (yt.omada.cafe) 多品質取得完了 - 最優先")
                    else:
                        results['omada_api'] = None
                else:
                    results['omada_api'] = None
            except Exception as e:
                logging.warning(f"Omada API (yt.omada.cafe) 失敗: {e}")
                results['omada_api'] = None

        def get_custom_api_info():
            try:
                if video_id:  # video_idの存在を確認
                    custom_data = custom_api_service.get_video_info(video_id)
                    if custom_data:
                        results['custom_api'] = custom_api_service.format_video_info(custom_data)
                        logging.info(f"✅ CustomApiService (siawaseok.duckdns.org) API完了")
                    else:
                        results['custom_api'] = None
                else:
                    results['custom_api'] = None
            except Exception as e:
                logging.warning(f"CustomApiService API失敗: {e}")
                results['custom_api'] = None

        def get_kahoot_video_info():
            try:
                if video_id:  # video_idの存在を確認
                    results['kahoot'] = multi_stream_service.get_video_info_from_kahoot(video_id)
                    logging.info(f"✅ Kahoot API完了")
                else:
                    results['kahoot'] = None
            except Exception as e:
                logging.warning(f"Kahoot API失敗: {e}")
                results['kahoot'] = None
        
        def get_stream_info():
            try:
                if video_id:  # video_idの存在を確認
                    results['stream'] = multi_stream_service.get_video_stream_info(video_id)
                    logging.info(f"✅ Stream API完了")
                else:
                    results['stream'] = None
            except Exception as e:
                logging.warning(f"Stream API失敗: {e}")
                results['stream'] = None
        
        def get_invidious_info():
            try:
                if video_id:  # video_idの存在を確認
                    results['invidious'] = invidious.get_video_info(video_id)
                    logging.info(f"✅ Invidious API完了")
                else:
                    results['invidious'] = None
            except Exception as e:
                logging.warning(f"Invidious API失敗: {e}")
                results['invidious'] = None
        
        def get_additional_streams():
            """🚀 追加の高速APIサービス群を並列実行（簡素化）"""
            try:
                from additional_services import AdditionalStreamServices
                additional_services = AdditionalStreamServices()
                
                # 順次実行でスレッドプール問題を回避
                try:
                    result = additional_services.get_noembed_stream(video_id)
                    if result:
                        results['additional_noembed'] = result
                        logging.info(f"✅ Noembed API成功")
                except:
                    pass
                
                try:
                    result = additional_services.get_lemnoslife_stream(video_id)
                    if result:
                        results['additional_lemnoslife'] = result
                        logging.info(f"✅ LemnosLife API成功")
                except:
                    pass
                
                logging.info(f"✅ 追加API群処理完了")
            except Exception as e:
                logging.warning(f"追加API群失敗: {e}")
        
        # 🚀 メインAPI + 追加API群を安全な並列で実行
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(get_omada_api_info),     # 🚀 最優先: yt.omada.cafe
                    executor.submit(get_custom_api_info),    # 2番目: CustomApiService
                    executor.submit(get_kahoot_video_info),  # 3番目: Kahoot
                    executor.submit(get_stream_info),        # 4番目: Stream
                    executor.submit(get_invidious_info)      # 5番目: Invidious
                ]
                
                # 🚀 最大3秒で全API処理完了（超高速化重視）
                done, not_done = concurrent.futures.wait(futures, timeout=3.0)
                
                # 完了していないフューチャーをキャンセル
                for future in not_done:
                    future.cancel()
            
            # 追加APIを別途実行
            get_additional_streams()
        except Exception as e:
            logging.error(f"並列処理エラー: {e}")
            # フォールバック: 順次実行
            get_omada_api_info()      # 🚀 最優先
            get_custom_api_info()
            get_kahoot_video_info()
            get_stream_info() 
            get_invidious_info()
            get_additional_streams()
        
        # 成功したAPI数を計算
        successful_apis = len([k for k, v in results.items() if v is not None and not k.startswith('additional_')])
        total_apis = 5  # OmadaAPI, CustomApiService, Kahoot, Stream, Invidious
        additional_apis = len([k for k in results.keys() if k.startswith('additional_')])
        
        logging.info(f"🚀 超高速並列処理完了: メインAPI {successful_apis}/{total_apis}, 追加API {additional_apis}個成功")
        
        # 結果を取得（🚀 yt.omada.cafe を最優先）
        omada_api_data = results.get('omada_api')
        custom_api_video_info = results.get('custom_api')
        kahoot_video_info = results.get('kahoot')
        api_data = results.get('stream')
        invidious_video_info = results.get('invidious')
        
        # 🆕 InvidiousからもStreamURLを取得
        invidious_stream_data = None
        try:
            if invidious_video_info:
                logging.info(f"🚀 InvidiousからStreamURL取得開始: {video_id}")
                invidious_stream_data = invidious.get_stream_urls(video_id)
                if invidious_stream_data:
                    logging.info(f"✅ InvidiousからStreamURL取得成功: {len(invidious_stream_data.get('formats', []))} 種類")
                else:
                    logging.warning(f"⚠️ InvidiousStreamURL取得失敗: {video_id}")
        except Exception as e:
            logging.warning(f"InvidiousStreamURL取得エラー: {e}")
        
        video_info = None
        stream_data = None
        
        # 🚀 yt.omada.cafe API結果を最優先で使用 - マルチ品質対応
        if omada_api_data and omada_api_data.get('success') and omada_api_data.get('multi_quality'):
            logging.info(f"✅ yt.omada.cafe API から多品質動画情報を最優先使用: {video_id}")
            
            # 新しいマルチ品質形式から最適なURLを選択（360pを優先）
            quality_streams = omada_api_data.get('quality_streams', {})
            best_url = ''
            has_audio = True
            
            # 360pがあれば結合ストリームとして優先
            if '360p' in quality_streams and quality_streams['360p'].get('combined_url'):
                best_url = quality_streams['360p']['combined_url']
                has_audio = True
                logging.info("360p結合ストリームを最適URLとして選択")
            # 他の品質で動画URLがあるものを選択
            elif quality_streams:
                for quality in ['1080p', '720p', '480p']:
                    if quality in quality_streams and quality_streams[quality].get('video_url'):
                        best_url = quality_streams[quality]['video_url']
                        has_audio = False  # 分離音声
                        logging.info(f"{quality}分離ストリームを最適URLとして選択")
                        break
            
            # YouTube Education URLを/api/<video_id>エンドポイントと同じ方法で生成（直接呼び出し）
            try:
                # 内部API呼び出しの代わりに直接multi_stream_serviceを使用（より高速）
                youtube_education_url = multi_stream_service.get_direct_youtube_embed_url(video_id, "education")
                logging.info(f"✅ multi_stream_serviceから直接YouTube Education URL取得成功")
            except Exception as e:
                youtube_education_url = f'https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&controls=1&rel=0'
                logging.warning(f"⚠️ YouTube Education URL生成エラー、フォールバック使用: {e}")

            # Omada APIからのマルチ品質情報を設定
            stream_data = {
                'title': omada_api_data.get('title', f'Video {video_id}'),
                'author': omada_api_data.get('author', 'Unknown'),
                'authorId': omada_api_data.get('authorId', ''),
                'description': omada_api_data.get('description', ''),
                'viewCount': omada_api_data.get('viewCount', 0),
                'lengthSeconds': omada_api_data.get('lengthSeconds', 0),
                'publishedText': omada_api_data.get('publishedText', ''),
                'multi_quality': True,
                'quality_streams': quality_streams,
                'best_audio': omada_api_data.get('best_audio'),
                'best_url': best_url,
                'has_audio': has_audio,
                'can_access_video_page': True,
                'success': True,
                'type': 'omada_api_multi_quality',
                'youtube_education_url': youtube_education_url
            }
            
            # video_infoも設定
            video_info = {
                'videoId': video_id,
                'title': omada_api_data.get('title', f'Video {video_id}'),
                'author': omada_api_data.get('author', 'Unknown'),
                'authorId': omada_api_data.get('authorId', ''),
                'lengthSeconds': omada_api_data.get('lengthSeconds', 0),
                'viewCount': omada_api_data.get('viewCount', 0),
                'publishedText': omada_api_data.get('publishedText', ''),
                'description': omada_api_data.get('description', ''),
                'videoThumbnails': [
                    {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'},
                    {'url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'}
                ]
            }
                
            logging.info(f"yt.omada.cafe多品質結果: タイトル={stream_data['title']}, 利用可能品質={list(quality_streams.keys())}")
            
        # 🚀 フォールバック: Omada APIから旧形式データが返された場合
        elif omada_api_data and omada_api_data.get('formatStreams'):
            logging.info(f"✅ yt.omada.cafe API から従来形式動画情報を使用: {video_id}")
            
            # Omada APIからの基本情報を設定（従来形式）
            stream_data = {
                'title': omada_api_data.get('title', f'Video {video_id}'),
                'author': omada_api_data.get('author', 'Unknown'),
                'authorId': omada_api_data.get('authorId', ''),
                'description': omada_api_data.get('description', ''),
                'viewCount': omada_api_data.get('viewCount', 0),
                'lengthSeconds': omada_api_data.get('lengthSeconds', 0),
                'publishedText': omada_api_data.get('publishedText', ''),
                'formatStreams': omada_api_data.get('formatStreams', []),
                'adaptiveFormats': omada_api_data.get('adaptiveFormats', []),
                'hlsUrl': omada_api_data.get('hlsUrl', ''),
                'dashUrl': omada_api_data.get('dashUrl', ''),
                'best_url': '',  # formatStreamsから最適なURLを選択
                'can_access_video_page': True,
                'success': True,
                'type': 'omada_api'
            }
            
            # formatStreamsから最適なストリームURLを選択
            if omada_api_data.get('formatStreams'):
                # 最高品質のストリームを選択
                best_stream = max(omada_api_data['formatStreams'], 
                                key=lambda x: x.get('qualityLabel', '720p'))
                stream_data['best_url'] = best_stream.get('url', '')
                
            # video_infoも設定（従来形式）
            video_info = {
                'videoId': video_id,
                'title': omada_api_data.get('title', f'Video {video_id}'),
                'author': omada_api_data.get('author', 'Unknown'),
                'authorId': omada_api_data.get('authorId', ''),
                'lengthSeconds': omada_api_data.get('lengthSeconds', 0),
                'viewCount': omada_api_data.get('viewCount', 0),
                'publishedText': omada_api_data.get('publishedText', ''),
                'description': omada_api_data.get('description', ''),
                'videoThumbnails': [
                    {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'},
                    {'url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'}
                ]
            }
            
            logging.info(f"yt.omada.cafe従来形式結果: タイトル={stream_data['title']}, フォーマット数={len(stream_data['formatStreams'])}")
            
        # 🚀 CustomApiService結果を2番目優先で使用
        elif custom_api_video_info and custom_api_service.can_access_video_page(custom_api_video_info):
            logging.info(f"✅ CustomApiService (siawaseok.duckdns.org) から動画情報を最優先使用: {video_id}")
            video_info = custom_api_video_info
            
            # CustomApiServiceから基本的なstream情報を生成
            stream_data = {
                'title': video_info.get('title', f'Video {video_id}'),
                'author': video_info.get('author', 'Unknown'),
                'authorId': video_info.get('authorId', ''),
                'description': video_info.get('description', ''),
                'viewCount': video_info.get('viewCount', 0),
                'lengthSeconds': video_info.get('lengthSeconds', 0),
                'publishedText': video_info.get('publishedText', ''),
                'streamUrl': video_info.get('streamUrl', ''),
                'best_url': video_info.get('streamUrl', ''),  # ストリームURLがあれば使用
                'youtube_education_url': video_info.get('youtubeeducation', ''),  # テンプレート用のフィールド名に統一
                'formats': video_info.get('formatStreams', []),
                'can_access_video_page': True,  # CustomApiServiceが成功した場合は動画ページアクセス可能
                'success': True,
                'type': 'custom_api'
            }
            
            logging.info(f"CustomApiService結果: タイトル={stream_data['title']}, YouTubeEducation={bool(stream_data['youtube_education_url'])}")
            
        elif api_data:
            logging.info(f"マルチAPIデータ受信成功")
            
            # duration値を安全に変換
            duration_raw = api_data.get('duration', 0)
            try:
                if isinstance(duration_raw, str):
                    if ':' in duration_raw:
                        parts = duration_raw.split(':')
                        if len(parts) == 2:
                            duration_seconds = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        else:
                            duration_seconds = 0
                    else:
                        duration_seconds = int(duration_raw)
                else:
                    duration_seconds = int(duration_raw) if duration_raw else 0
            except (ValueError, TypeError):
                duration_seconds = 0

            # viewCount値を安全に変換（複数のフィールドをチェック）
            view_count_raw = (api_data.get('view_count') or 
                            api_data.get('viewCount') or 
                            api_data.get('views') or 
                            api_data.get('view_count_text', '').replace(',', '').replace('回視聴', '').replace('回再生', '').strip() or
                            0)
            try:
                # 文字列の場合、数字以外を削除してから変換
                if isinstance(view_count_raw, str):
                    # 日本語の数字記号を除去して数字のみ抽出
                    import re
                    view_count_clean = re.sub(r'[^\d]', '', view_count_raw)
                    view_count = int(view_count_clean) if view_count_clean else 0
                else:
                    view_count = int(view_count_raw) if view_count_raw else 0
            except (ValueError, TypeError):
                view_count = 0

            # チャンネル名とIDを適切に取得
            author_name = (api_data.get('uploader') or 
                         api_data.get('author') or
                         api_data.get('channel', {}).get('name') if isinstance(api_data.get('channel'), dict) else None or
                         api_data.get('channel_name') or
                         'Unknown')
            
            author_id = (api_data.get('uploader_id') or 
                       api_data.get('authorId') or
                       api_data.get('channel', {}).get('id') if isinstance(api_data.get('channel'), dict) else None or
                       api_data.get('channel_id') or
                       '')
            
            # siawaseok APIから動画の説明欄を取得
            video_description = api_data.get('description', '')
            
            # 🚀 並列処理で取得済みのInvidious情報を活用
            if invidious_video_info:
                # Invidiousから取得した情報で補完
                if author_name == 'Unknown' and invidious_video_info.get('author'):
                    author_name = invidious_video_info['author']
                if not author_id and invidious_video_info.get('authorId'):
                    author_id = invidious_video_info['authorId']
                # より詳細な説明文があれば使用
                if not video_description and invidious_video_info.get('description'):
                    video_description = invidious_video_info['description']
                
                # より信頼性の高い視聴回数があれば更新
                invidious_view_count = invidious_video_info.get('viewCount', 0)
                try:
                    invidious_view_count = int(invidious_view_count) if invidious_view_count else 0
                    # Invidiousの方が大きい値か、siawaseokが0の場合はInvidiousの値を使用
                    if invidious_view_count > view_count or view_count == 0:
                        view_count = invidious_view_count
                        logging.info(f"Invidiousから視聴回数を更新: {invidious_view_count:,}回")
                except (ValueError, TypeError):
                    pass
                
                logging.info(f"🚀 並列処理完了Invidiousデータ活用: 投稿者={author_name}, ID={author_id}")
            
            logging.info(f"動画説明文の長さ: {len(video_description)} 文字")
            logging.info(f"チャンネル情報: 名前={author_name}, ID={author_id}")
            
            # 🚀 チャンネル情報も必要時のみ高速取得（Unknownの場合のみ）
            channel_info = None  # 変数を初期化
            if author_id and author_name == 'Unknown':
                try:
                    channel_api_url = f"https://siawaseok.duckdns.org/api/channel/{author_id}"
                    logging.info(f"🚀 高速チャンネル情報取得: {channel_api_url}")
                    channel_response = requests.get(channel_api_url, timeout=3)  # タイムアウト短縮
                    if channel_response.status_code == 200:
                        channel_info = channel_response.json()
                        if channel_info and 'name' in channel_info:
                            author_name = channel_info.get('name', author_name)
                            logging.info(f"✅ チャンネル情報取得成功: {author_name}")
                except Exception as e:
                    logging.warning(f"チャンネル情報取得スキップ: {e}")

            # 動画タイトルを複数のソースから優先的に取得
            title = api_data.get('title')
            
            # まずInvidiousから取得を試みる（より信頼性が高い）
            if not title or title == f'Video {video_id}' or title == f'動画 {video_id}':
                if invidious_video_info and invidious_video_info.get('title'):
                    title = invidious_video_info['title']
                    logging.info(f"優先: Invidiousからタイトル取得: {title}")
            
            # それでも取得できない場合、代替APIを試す
            if not title or title == f'Video {video_id}' or title == f'動画 {video_id}':
                try:
                    detail_url = f"https://siawaseok.duckdns.org/api/stream/{video_id}"
                    detail_response = requests.get(detail_url, timeout=10)
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        if detail_data.get('title'):
                            title = detail_data['title']
                            logging.info(f"代替APIからタイトル取得: {title}")
                except Exception as e:
                    logging.warning(f"代替API失敗: {e}")
            
            # 🆕 動画情報を優先順位で統合（Kahoot API > Invidious > siawaseok）
            final_title = title
            final_author = author_name
            final_author_id = author_id
            final_description = video_description
            final_published_text = ''
            final_thumbnails = []
            final_length_seconds = duration_seconds
            
            # 1. Kahoot APIからの情報を最優先
            if kahoot_video_info:
                if kahoot_video_info.get('title'):
                    final_title = kahoot_video_info['title']
                    logging.info(f"✅ Kahoot APIからタイトル取得: {final_title}")
                if kahoot_video_info.get('author'):
                    final_author = kahoot_video_info['author']
                    logging.info(f"✅ Kahoot APIから投稿者取得: {final_author}")
                if kahoot_video_info.get('authorId'):
                    final_author_id = kahoot_video_info['authorId']
                if kahoot_video_info.get('description'):
                    final_description = kahoot_video_info['description']
                    logging.info(f"✅ Kahoot APIから説明文取得: {len(final_description)} 文字")
                if kahoot_video_info.get('publishedText'):
                    final_published_text = kahoot_video_info['publishedText']
                if kahoot_video_info.get('videoThumbnails'):
                    final_thumbnails = kahoot_video_info['videoThumbnails']
                if kahoot_video_info.get('lengthSeconds'):
                    final_length_seconds = kahoot_video_info['lengthSeconds']
            
            # 2. Invidiousで補完
            if not final_title or final_title == f'動画 {video_id}':
                if invidious_video_info and invidious_video_info.get('title'):
                    final_title = invidious_video_info['title']
                    logging.info(f"Invidiousからタイトル補完: {final_title}")
            
            if final_author == 'Unknown' or not final_author:
                if invidious_video_info and invidious_video_info.get('author'):
                    final_author = invidious_video_info['author']
                    logging.info(f"Invidiousから投稿者補完: {final_author}")
            
            if not final_description:
                if invidious_video_info and invidious_video_info.get('description'):
                    final_description = invidious_video_info['description']
            
            if not final_published_text:
                if invidious_video_info and invidious_video_info.get('publishedText'):
                    final_published_text = invidious_video_info['publishedText']
                elif api_data.get('upload_date'):
                    upload_date = api_data.get('upload_date')
                    if upload_date and upload_date != 'N/A':
                        final_published_text = upload_date
            
            if not final_thumbnails:
                if invidious_video_info and invidious_video_info.get('videoThumbnails'):
                    final_thumbnails = invidious_video_info['videoThumbnails']
                else:
                    final_thumbnails = [
                        {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'},
                        {'url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'}
                    ]
            
            # 3. 最終的なフォールバック処理
            if not final_title or final_title == f'動画 {video_id}':
                try:
                    fallback_response = requests.get(f"https://siawaseok.duckdns.org/api/stream/{video_id}", timeout=10)
                    if fallback_response.status_code == 200:
                        fallback_data = fallback_response.json()
                        if fallback_data.get('title'):
                            final_title = fallback_data['title']
                            logging.info(f"フォールバックからタイトル取得: {final_title}")
                except Exception as e:
                    logging.warning(f"フォールバックタイトル取得失敗: {e}")
            
            if not final_title or final_title == f'動画 {video_id}':
                final_title = "タイトル未取得"
                logging.warning(f"動画 {video_id} のタイトルを取得できませんでした")
            
            # 🆕 複数のAPIソースからチャンネルアイコン（authorThumbnails）を取得
            final_author_thumbnails = []
            
            # 1. Kahoot APIから取得（小さいサイズから大きいサイズの順序でテンプレートの期待に合わせる）
            if kahoot_video_info and kahoot_video_info.get('snippet', {}).get('thumbnails'):
                thumbnail_sizes = ['default', 'medium', 'high']  # 最小→最大の順序に修正
                for size in thumbnail_sizes:
                    if kahoot_video_info['snippet']['thumbnails'].get(size, {}).get('url'):
                        final_author_thumbnails.append({
                            'url': kahoot_video_info['snippet']['thumbnails'][size]['url'],
                            'width': kahoot_video_info['snippet']['thumbnails'][size].get('width', 88),
                            'height': kahoot_video_info['snippet']['thumbnails'][size].get('height', 88)
                        })
            
            # 2. Invidious APIから取得（フォールバック）
            if not final_author_thumbnails and invidious_video_info and invidious_video_info.get('authorThumbnails'):
                final_author_thumbnails = invidious_video_info['authorThumbnails']
            
            # 3. siawaseok APIのチャンネル情報から取得（フォールバック）
            if not final_author_thumbnails and channel_info and channel_info.get('avatarUrl'):
                final_author_thumbnails.append({
                    'url': channel_info['avatarUrl'],
                    'width': 176,
                    'height': 176
                })
            
            # 4. 最終フォールバック：YouTubeの標準チャンネルアイコンURL生成
            if not final_author_thumbnails and final_author_id:
                final_author_thumbnails.append({
                    'url': f'https://yt3.ggpht.com/ytc/default_user=s176-c-k-c0x00ffffff-no-rj',
                    'width': 176,
                    'height': 176
                })
            
            # 5. 完全なフォールバック：デフォルトアバター
            if not final_author_thumbnails:
                final_author_thumbnails.append({
                    'url': 'https://via.placeholder.com/176x176/cccccc/ffffff?text=USER',
                    'width': 176,
                    'height': 176
                })

            video_info = {
                'videoId': video_id,
                'title': final_title,
                'author': final_author,
                'authorId': final_author_id,
                'lengthSeconds': final_length_seconds,
                'viewCount': view_count,
                'publishedText': final_published_text,
                'description': final_description,
                'videoThumbnails': final_thumbnails,
                'authorThumbnails': final_author_thumbnails,
                'subCountText': invidious_video_info.get('subCountText', '') if invidious_video_info else '',
                'channel_info': channel_info,  # siawaseok APIから取得
                # 🆕 Kahoot API特有の情報も追加
                'kahoot_data': kahoot_video_info if kahoot_video_info else None
            }
            
            # 新しいtype2 APIレスポンス構造に対応したストリーム情報設定
            formats = []
            best_url = None
            has_audio = False
            
            # muxed360p（音声付き360p）- 最高の互換性
            if 'muxed360p' in api_data and api_data['muxed360p']:
                if isinstance(api_data['muxed360p'], dict) and 'url' in api_data['muxed360p']:
                    muxed_url = api_data['muxed360p']['url']
                    muxed_container = api_data['muxed360p'].get('container', 'mp4')
                    muxed_mime = api_data['muxed360p'].get('mimeType', 'video/mp4')
                else:
                    muxed_url = api_data['muxed360p']
                    muxed_container = 'mp4'
                    muxed_mime = 'video/mp4'
                
                formats.append({
                    'url': muxed_url,
                    'quality': '360p',
                    'resolution': '640x360',
                    'container': muxed_container,
                    'has_audio': True,
                    'audio_url': '',
                    'fps': '30',
                    'mimeType': muxed_mime,
                    'label': '360p (音声付き)',
                    'itag': 18
                })
                best_url = muxed_url
                has_audio = True
                logging.info(f"✓ muxed360p取得: {len(muxed_url)} 文字のURL")
            
            # 720p（高画質、分離音声）
            if '720p' in api_data and api_data['720p']:
                video_url = None
                audio_url = None
                video_container = 'mp4'
                video_mime = 'video/mp4'
                
                if isinstance(api_data['720p'], dict):
                    if 'video' in api_data['720p'] and isinstance(api_data['720p']['video'], dict):
                        video_info_720p = api_data['720p']['video']
                        video_url = video_info_720p.get('url')
                        video_container = video_info_720p.get('container', 'mp4')
                        video_mime = video_info_720p.get('mimeType', 'video/mp4')
                    if 'audio' in api_data['720p'] and isinstance(api_data['720p']['audio'], dict):
                        audio_url = api_data['720p']['audio'].get('url')
                
                if video_url and audio_url:
                    formats.append({
                        'url': video_url,
                        'quality': '720p',
                        'resolution': '1280x720',
                        'container': video_container,
                        'has_audio': False,
                        'audio_url': audio_url,
                        'fps': '30',
                        'mimeType': video_mime,
                        'label': '720p (高画質)',
                        'itag': 136
                    })
                    if not has_audio:  # 720pを優先として設定（360pがない場合）
                        best_url = video_url
                    logging.info(f"✓ 720p取得: 動画={len(video_url)} 文字, 音声={len(audio_url)} 文字")
            
            # 1080p（最高画質、分離音声）
            if '1080p' in api_data and api_data['1080p']:
                video_url = None
                audio_url = None
                video_container = 'mp4'
                video_mime = 'video/mp4'
                
                if isinstance(api_data['1080p'], dict):
                    if 'video' in api_data['1080p'] and isinstance(api_data['1080p']['video'], dict):
                        video_info_1080p = api_data['1080p']['video']
                        video_url = video_info_1080p.get('url')
                        video_container = video_info_1080p.get('container', 'mp4')
                        video_mime = video_info_1080p.get('mimeType', 'video/mp4')
                    if 'audio' in api_data['1080p'] and isinstance(api_data['1080p']['audio'], dict):
                        audio_url = api_data['1080p']['audio'].get('url')
                
                if video_url and audio_url:
                    formats.append({
                        'url': video_url,
                        'quality': '1080p',
                        'resolution': '1920x1080',
                        'container': video_container,
                        'has_audio': False,
                        'audio_url': audio_url,
                        'fps': '30',
                        'mimeType': video_mime,
                        'label': '1080p (最高画質)',
                        'itag': 137
                    })
                    # 1080pが利用可能で360pがない場合は1080pを優先
                    if not has_audio:
                        best_url = video_url
                    logging.info(f"✓ 1080p取得: 動画={len(video_url)} 文字, 音声={len(audio_url)} 文字")
            
            # 480p（中画質、分離音声）
            if '480p' in api_data and api_data['480p']:
                video_url = None
                audio_url = None
                video_container = 'mp4'
                video_mime = 'video/mp4'
                
                if isinstance(api_data['480p'], dict):
                    if 'video' in api_data['480p'] and isinstance(api_data['480p']['video'], dict):
                        video_info_480p = api_data['480p']['video']
                        video_url = video_info_480p.get('url')
                        video_container = video_info_480p.get('container', 'mp4')
                        video_mime = video_info_480p.get('mimeType', 'video/mp4')
                    if 'audio' in api_data['480p'] and isinstance(api_data['480p']['audio'], dict):
                        audio_url = api_data['480p']['audio'].get('url')
                
                if video_url and audio_url:
                    formats.append({
                        'url': video_url,
                        'quality': '480p',
                        'resolution': '854x480',
                        'container': video_container,
                        'has_audio': False,
                        'audio_url': audio_url,
                        'fps': '30',
                        'mimeType': video_mime,
                        'label': '480p (標準)',
                        'itag': 135
                    })
                    logging.info(f"✓ 480p取得: 動画={len(video_url)} 文字, 音声={len(audio_url)} 文字")
            
            # 240p（低画質、分離音声）
            if '240p' in api_data and api_data['240p']:
                video_url = None
                audio_url = None
                video_container = 'mp4'
                video_mime = 'video/mp4'
                
                if isinstance(api_data['240p'], dict):
                    if 'video' in api_data['240p'] and isinstance(api_data['240p']['video'], dict):
                        video_info_240p = api_data['240p']['video']
                        video_url = video_info_240p.get('url')
                        video_container = video_info_240p.get('container', 'mp4')
                        video_mime = video_info_240p.get('mimeType', 'video/mp4')
                    if 'audio' in api_data['240p'] and isinstance(api_data['240p']['audio'], dict):
                        audio_url = api_data['240p']['audio'].get('url')
                
                if video_url and audio_url:
                    formats.append({
                        'url': video_url,
                        'quality': '240p',
                        'resolution': '426x240',
                        'container': video_container,
                        'has_audio': False,
                        'audio_url': audio_url,
                        'fps': '30',
                        'mimeType': video_mime,
                        'label': '240p (低画質)',
                        'itag': 133
                    })
                    logging.info(f"✓ 240p取得: 動画={len(video_url)} 文字, 音声={len(audio_url)} 文字")
            
            # 直接YouTube Education埋め込みURLを生成（API不要）
            youtube_education_embed_url = multi_stream_service.get_direct_youtube_embed_url(video_id, "education")
            logging.info(f"YouTube Education URL直接生成成功: {youtube_education_embed_url[:100]}...")

            if formats:
                # 画質オプションを優先順位でソート
                quality_priority = {'1080p': 5, '720p': 4, '480p': 3, '360p': 2, '240p': 1}
                formats.sort(key=lambda x: quality_priority.get(x['quality'], 0), reverse=True)
                
                # 最適なURLを決定
                if not best_url and formats:
                    # 音声付きフォーマットを優先
                    audio_formats = [f for f in formats if f.get('has_audio', False)]
                    if audio_formats:
                        best_url = audio_formats[0]['url']
                        logging.info(f"音声付きを優先: {audio_formats[0]['quality']}")
                    else:
                        best_url = formats[0]['url']
                        logging.info(f"最高画質を選択: {formats[0]['quality']}")
                
                stream_data = {
                    'success': True,
                    'best_url': best_url,
                    'formats': formats,
                    'has_audio': has_audio,
                    'quality': formats[0]['quality'] if formats else '360p',
                    'type': 'direct',
                    'youtube_education_url': youtube_education_embed_url,
                    'total_formats': len(formats)
                }
                
                logging.info(f"✅ 全画質取得完了: {[f['quality'] for f in formats]} (計{len(formats)}種類)")
            else:
                # フォールバック：YouTube Education埋め込み
                stream_data = {
                    'success': True,
                    'embed_url': f'https://www.youtube-nocookie.com/embed/{video_id}',
                    'youtube_education_url': youtube_education_embed_url,
                    'quality': 'embed',
                    'type': 'embed',
                    'formats': []
                }
        else:
            logging.warning(f"マルチAPIからデータを取得できませんでした")
            # 最小限の動画情報を作成
            video_info = {
                'videoId': video_id,
                'title': f'Video {video_id}',
                'author': 'Unknown',
                'authorId': '',
                'lengthSeconds': 0,
                'viewCount': 0,
                'publishedText': '',
                'description': '',
                'videoThumbnails': [
                    {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'}
                ]
            }
            # 最小限のstream_dataも作成
            stream_data = {
                'success': False,
                'embed_url': f'https://www.youtube-nocookie.com/embed/{video_id}',
                'quality': 'embed',
                'type': 'fallback',
                'formats': [],
                'error': 'データを取得できませんでした'
            }
        
        # コメントは遅延読み込みのため、初期表示では空にする
        comments_data = {'comments': [], 'continuation': None}
        
        # 視聴履歴を記録
        if video_info:
            user_prefs.record_watch(video_info)
        
        return render_template('watch.html', 
                             video_info=video_info,
                             stream_data=stream_data,
                             comments_data=comments_data)
    except Exception as e:
        logging.error(f"動画取得エラー: {e}")
        # エラー時でも最小限のvideo_infoを提供
        video_id = request.args.get('v', '')
        fallback_video_info = {
            'videoId': video_id,
            'title': f'動画 {video_id}',
            'author': 'Unknown',
            'authorId': '',
            'lengthSeconds': 0,
            'viewCount': 0,
            'publishedText': '',
            'description': 'れんれんtubeで動画を視聴中',
            'videoThumbnails': [
                {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'}
            ]
        }
        return render_template('watch.html', 
                             video_info=fallback_video_info,
                             stream_data=None,
                             comments_data={'comments': [], 'continuation': None},
                             error="動画の読み込み中にエラーが発生しました。")

@app.route('/watch/<video_id>')
def watch_video_id(video_id):
    """動画視聴ページ - /watch/<video_id> 形式対応"""
    if not video_id:
        return redirect(url_for('index'))
    
    # /watch?v=<video_id> 形式でリダイレクト
    return redirect(url_for('watch', v=video_id))

@app.route('/api/related-videos/<video_id>')
def api_related_videos(video_id):
    """関連動画API - 各動画ごとに異なる関連動画を提供"""
    try:
        # リクエスト開始時にキャッシュをクリア（パフォーマンス向上）
        multi_stream_service.clear_request_cache()
        
        query = request.args.get('q', '')
        all_related_videos = []
        
        # 1. 動画タイトルに基づいて関連動画を検索（最優先）
        if query:
            # 日本語文字を含むキーワードを抽出（より関連性の高い検索のため）
            import re
            japanese_words = re.findall(r'[ひらがなカタカナ漢字]+', query)
            english_words = re.findall(r'[a-zA-Z]+', query)
            
            # 最も関連性の高いキーワードを選択
            priority_keywords = japanese_words[:2] + english_words[:2]
            if not priority_keywords:
                priority_keywords = query.split()[:3]
            
            # 各キーワードで個別に検索
            for i, keyword in enumerate(priority_keywords):
                try:
                    # ページを変えて異なる結果を取得
                    page = (i % 3) + 1
                    search_results = invidious.search_videos(keyword, page=page)
                    if search_results:
                        filtered_videos = [v for v in search_results if v.get('videoId') != video_id]
                        all_related_videos.extend(filtered_videos[:30])
                        logging.info(f"キーワード '{keyword}' で {len(filtered_videos[:30])} 件取得 (ページ{page})")
                except Exception as e:
                    logging.warning(f"関連動画検索失敗（キーワード: {keyword}）: {e}")
            
            # 2. タイトル全体での検索（異なるページから取得）
            try:
                # 動画IDをハッシュ化してページ番号を決定（動画ごとに異なるページ）
                import hashlib
                hash_obj = hashlib.md5(video_id.encode())
                page_num = (int(hash_obj.hexdigest(), 16) % 5) + 1  # 1-5ページ
                
                broad_search = invidious.search_videos(query[:25], page=page_num)
                if broad_search:
                    filtered_videos = [v for v in broad_search if v.get('videoId') != video_id]
                    all_related_videos.extend(filtered_videos[:40])
                    logging.info(f"タイトル全体検索で {len(filtered_videos[:40])} 件取得 (ページ{page_num})")
            except Exception as e:
                logging.warning(f"広域検索失敗: {e}")
        
        # 3. 動画IDに基づいてトレンドの異なる部分を取得
        try:
            # 動画IDに基づいてカテゴリを選択
            categories = ['', 'Music', 'Gaming']
            category_index = sum(ord(c) for c in video_id) % len(categories)
            category = categories[category_index]
            
            trending_videos = invidious.get_trending_videos(region='JP', category=category if category else None)
            if trending_videos:
                # 動画IDに基づいて開始位置を決定
                start_index = (sum(ord(c) for c in video_id) % 20)
                filtered_trending = [v for v in trending_videos[start_index:start_index+30] if v.get('videoId') != video_id]
                all_related_videos.extend(filtered_trending)
                logging.info(f"トレンド動画({category or 'general'})から {len(filtered_trending)} 件取得")
        except Exception as e:
            logging.warning(f"Invidiousトレンド取得失敗: {e}")
        
        # 4. siawaseok APIから異なるカテゴリを取得
        try:
            response = requests.get("https://siawaseok.duckdns.org/api/trend", timeout=10)
            if response.status_code == 200:
                trend_data = response.json()
                if isinstance(trend_data, dict):
                    # 動画IDに基づいてカテゴリを選択
                    available_categories = ['trending', 'music', 'gaming']
                    selected_category = available_categories[(sum(ord(c) for c in video_id) % len(available_categories))]
                    
                    if selected_category in trend_data:
                        category_videos = trend_data[selected_category]
                        # 動画IDに基づいて開始位置を決定
                        start_pos = (sum(ord(c) for c in video_id) % max(1, len(category_videos) - 10))
                        selected_videos = category_videos[start_pos:start_pos+20]
                        filtered_category = [v for v in selected_videos if v.get('videoId') != video_id]
                        all_related_videos.extend(filtered_category)
                        logging.info(f"siawaseok {selected_category}から {len(filtered_category)} 件取得")
        except Exception as e:
            logging.warning(f"siawaseokトレンド取得失敗: {e}")
        
        # 5. 🆕 Kahoot APIで関連動画の詳細情報を取得・補完
        enhanced_videos = []
        seen_ids = set()
        
        # 動画IDに基づいて結果をシャッフル（同じ動画では同じ順序）
        import random
        random.seed(hash(video_id))  # 動画IDに基づいた固定シード
        shuffled_videos = all_related_videos.copy()
        random.shuffle(shuffled_videos)
        
        # 重複を除去して候補動画IDを収集
        candidate_video_ids = []
        for video in shuffled_videos:
            video_id_check = video.get('videoId')
            if video_id_check and video_id_check not in seen_ids and video_id_check != video_id:
                seen_ids.add(video_id_check)
                candidate_video_ids.append(video_id_check)
                if len(candidate_video_ids) >= 25:  # 最大25本の候補（パフォーマンス向上）
                    break
        
        # Kahoot APIで関連動画の詳細情報を一括取得
        if candidate_video_ids:
            logging.info(f"Kahoot APIで関連動画の詳細情報を取得中: {len(candidate_video_ids)} 件")
            kahoot_related_videos = multi_stream_service.get_related_videos_from_kahoot(video_id, candidate_video_ids)
            
            if kahoot_related_videos:
                # Kahoot APIから取得した高品質な情報を優先
                enhanced_videos = kahoot_related_videos[:20]  # 最大20本（パフォーマンス向上）
                logging.info(f"✅ Kahoot APIから関連動画詳細情報取得: {len(enhanced_videos)} 件")
            else:
                # Kahoot API失敗時のフォールバック: 既存の動画情報を使用
                for video in shuffled_videos:
                    video_id_check = video.get('videoId')
                    if video_id_check and video_id_check not in seen_ids and video_id_check != video_id:
                        seen_ids.add(video_id_check)
                        enhanced_videos.append(video)
                        if len(enhanced_videos) >= 20:
                            break
                logging.info(f"🔄 フォールバック: 既存の関連動画情報を使用: {len(enhanced_videos)} 件")
        else:
            logging.warning("関連動画の候補が見つかりませんでした")
        
        logging.info(f"動画 {video_id} の関連動画を {len(enhanced_videos)} 本取得")
        
        return jsonify({
            'success': True,
            'videos': enhanced_videos,
            'total': len(enhanced_videos),
            'video_id': video_id  # デバッグ用
        })
        
    except Exception as e:
        logging.error(f"関連動画取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'videos': []
        })

@app.route('/api/comments/<video_id>')
def api_comments(video_id):
    """コメントAPI - CustomApiServiceを最優先使用"""
    try:
        # 1. CustomApiService（siawaseok.duckdns.org）を最優先で使用
        try:
            logging.info(f"CustomApiService (siawaseok.duckdns.org) でコメント取得開始: {video_id}")
            custom_comments_data = custom_api_service.get_video_comments(video_id)
            
            if custom_comments_data:
                custom_comments = custom_api_service.format_comments(custom_comments_data)
                if custom_comments:
                    logging.info(f"✅ CustomApiService から {len(custom_comments)} 件のコメントを取得")
                    return jsonify({
                        'success': True,
                        'comments': custom_comments,
                        'commentCount': len(custom_comments),
                        'source': 'CustomApiService',
                        'continuation': custom_comments_data.get('continuation')
                    })
        except Exception as e:
            logging.warning(f"CustomApiService コメント取得エラー: {e}")
        
        # 2. フォールバック: Invidiousを使用
        logging.info(f"フォールバック: Invidiousでコメント取得: {video_id}")
        comments_data = invidious.get_video_comments(video_id)
        
        if comments_data and comments_data.get('comments'):
            return jsonify({
                'success': True,
                'comments': comments_data['comments'],
                'commentCount': comments_data.get('commentCount', len(comments_data['comments'])),
                'source': 'Invidious',
                'continuation': comments_data.get('continuation')
            })
        else:
            return jsonify({
                'success': False,
                'comments': [],
                'commentCount': 0,
                'error': 'コメントが見つかりません'
            })
            
    except Exception as e:
        logging.error(f"コメント取得エラー: {e}")
        return jsonify({
            'success': False,
            'comments': [],
            'commentCount': 0,
            'error': str(e)
        })

@app.route('/api/omada-audio/<video_id>')
def get_omada_audio(video_id):
    """omada APIから音声のみを取得"""
    try:
        logging.info(f"omada音声取得リクエスト: {video_id}")
        
        # OmadaVideoServiceを使用して動画情報を取得
        omada_service = OmadaVideoService()
        video_data = omada_service.get_video_streams(video_id)
        
        if not video_data:
            return jsonify({
                'success': False,
                'error': 'omada APIから動画データを取得できませんでした'
            })
        
        # 音声ストリームを検索
        audio_url = None
        best_audio = None
        
        # best_audioが存在する場合
        if 'best_audio' in video_data and video_data['best_audio']:
            best_audio = video_data['best_audio']
            audio_url = best_audio.get('url')
            logging.info(f"omada best_audio URL取得: {audio_url}")
        
        # audio_streamsから最高品質を選択
        elif 'audio_streams' in video_data and video_data['audio_streams']:
            audio_streams = video_data['audio_streams']
            # ビットレート順にソートして最高品質を選択
            sorted_streams = sorted(audio_streams, key=lambda x: x.get('bitrate', 0), reverse=True)
            best_audio = sorted_streams[0]
            audio_url = best_audio.get('url')
            logging.info(f"omada audio_streams URL取得: {audio_url} (bitrate: {best_audio.get('bitrate', 0)})")
        
        # formatted_dataを確認
        elif 'formatted_data' in video_data and video_data['formatted_data']:
            formatted = video_data['formatted_data']
            if 'best_audio' in formatted and formatted['best_audio']:
                best_audio = formatted['best_audio']
                audio_url = best_audio.get('url')
                logging.info(f"omada formatted best_audio URL取得: {audio_url}")
            elif 'audio_streams' in formatted and formatted['audio_streams']:
                audio_streams = formatted['audio_streams']
                sorted_streams = sorted(audio_streams, key=lambda x: x.get('bitrate', 0), reverse=True)
                best_audio = sorted_streams[0]
                audio_url = best_audio.get('url')
                logging.info(f"omada formatted audio_streams URL取得: {audio_url}")
        
        if audio_url:
            logging.info(f"✅ omada音声URL取得成功: {video_id} - {audio_url}")
            return jsonify({
                'success': True,
                'audio_url': audio_url,
                'audio_info': {
                    'bitrate': best_audio.get('bitrate', 0) if best_audio else 0,
                    'container': best_audio.get('container', 'unknown') if best_audio else 'unknown',
                    'codecs': best_audio.get('codecs', 'unknown') if best_audio else 'unknown'
                }
            })
        else:
            logging.warning(f"omada音声ストリームが見つかりません: {video_id}")
            return jsonify({
                'success': False,
                'error': '音声ストリームが見つかりませんでした'
            })
            
    except Exception as e:
        logging.error(f"omada音声取得エラー: {video_id} - {e}")
        return jsonify({
            'success': False,
            'error': f'音声取得エラー: {str(e)}'
        })

@app.route('/channel/<channel_id>/<path:slug>')
def channel_with_slug(channel_id, slug):
    """チャンネルURL正規化：チャンネル名付きURLを正規URLにリダイレクト"""
    return redirect(url_for('channel', channel_id=channel_id), code=301)

@app.route('/channel/<channel_id>')
def channel(channel_id):
    """チャンネルページ - siawaseok API対応"""
    try:
        # ページ番号、チャンネル名、ソート順を取得
        page = int(request.args.get('page', 1))
        channel_name = request.args.get('name', '')
        sort = request.args.get('sort', 'newest')
        
        # siawaseok APIからチャンネル情報を取得
        channel_info = None
        api_data = None
        if channel_id:
            try:
                logging.info(f"マルチエンドポイントでチャンネル情報を取得中: {channel_id}")
                api_data = multi_stream_service.get_channel_info(channel_id)
                
                if api_data:
                    logging.info(f"マルチAPIチャンネルデータ受信成功")
                    
                    # siawaseok APIの実際の構造に合わせて調整
                    # チャンネル登録者数の正しい取得
                    sub_count = 0
                    total_views = 0
                    video_count = 0
                    
                    # siawaseok APIの実際の構造に合わせて調整
                    if 'subCount' in api_data:
                        try:
                            sub_count = int(api_data['subCount']) if api_data['subCount'] else 0
                        except (ValueError, TypeError):
                            sub_count = 0
                    
                    # 総視聴回数を正しく取得
                    if 'totalViews' in api_data:
                        try:
                            total_views = int(api_data['totalViews']) if api_data['totalViews'] else 0
                        except (ValueError, TypeError):
                            total_views = 0
                    
                    # 動画数を正しく計算
                    if 'playlists' in api_data:
                        for playlist in api_data['playlists']:
                            if isinstance(playlist, dict) and 'items' in playlist:
                                video_count += len(playlist['items'])
                    
                    # チャンネル画像の取得
                    avatar_url = api_data.get('avatar', f'https://yt3.ggpht.com/a/default-user=s176-c-k-c0x00ffffff-no-rj')
                    banner_url = api_data.get('banner', '')
                    
                    channel_info = {
                        'author': api_data.get('title', channel_name or f'チャンネル ({channel_id})'),
                        'authorId': channel_id,
                        'description': api_data.get('description', ''),
                        'subCount': sub_count,
                        'totalViews': total_views,
                        'videoCount': video_count,
                        'joined': api_data.get('joined', 0),
                        'authorThumbnails': [
                            {'url': avatar_url}
                        ],
                        'authorBanners': [
                            {'url': banner_url}
                        ] if banner_url else [],
                        'autoGenerated': False
                    }
                else:
                    logging.warning(f"マルチAPIチャンネル情報取得失敗")
            except Exception as e:
                logging.error(f"siawaseok channel API error: {e}")
        
        # フォールバック: チャンネル名で基本情報作成
        if not channel_info and channel_name:
            channel_info = {
                'author': channel_name,
                'authorId': channel_id,
                'description': f'{channel_name}のチャンネル',
                'subCount': 0,
                'totalViews': 0,
                'videoCount': 0,
                'joined': 0,
                'authorThumbnails': [
                    {'url': f'https://yt3.ggpht.com/a/default-user=s176-c-k-c0x00ffffff-no-rj'}
                ],
                'authorBanners': [],
                'autoGenerated': False
            }
        
        # siawaseok APIからチャンネル動画を取得（プレイリスト分け対応）
        videos = []
        playlists = []
        if channel_info and api_data and 'playlists' in api_data:
            # siawaseok APIの構造に基づいてプレイリストごとに整理
            all_videos = []
            
            # 各プレイリストを名前分けして処理
            for playlist in api_data.get('playlists', []):
                if isinstance(playlist, dict) and 'items' in playlist:
                    # プレイリスト情報を取得
                    playlist_name = playlist.get('name', playlist.get('title', 'その他の動画'))
                    playlist_videos = []
                    
                    # プレイリスト内の動画を処理
                    seen_ids_in_playlist = set()
                    for video_data in playlist.get('items', []):
                        if isinstance(video_data, dict) and video_data.get('videoId'):
                            video_id = video_data.get('videoId')
                            if video_id and video_id not in seen_ids_in_playlist:
                                seen_ids_in_playlist.add(video_id)
                                
                                # duration値を安全に変換
                                duration_raw = video_data.get('duration', '0:00')
                                try:
                                    if isinstance(duration_raw, str) and ':' in duration_raw:
                                        parts = duration_raw.split(':')
                                        if len(parts) == 2:
                                            duration_seconds = int(parts[0]) * 60 + int(parts[1])
                                        elif len(parts) == 3:
                                            duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                        else:
                                            duration_seconds = 0
                                    else:
                                        duration_seconds = int(duration_raw) if duration_raw else 0
                                except (ValueError, TypeError):
                                    duration_seconds = 0
                                
                                # viewCount値を安全に変換
                                view_count_raw = video_data.get('viewCount', '0')
                                try:
                                    # "1,234 回視聴" のような文字列から数値を抽出
                                    if isinstance(view_count_raw, str):
                                        import re
                                        view_count_str = re.sub(r'[^\d]', '', view_count_raw)
                                        view_count = int(view_count_str) if view_count_str else 0
                                    else:
                                        view_count = int(view_count_raw) if view_count_raw else 0
                                except (ValueError, TypeError):
                                    view_count = 0
                                
                                video = {
                                    'videoId': video_id,
                                    'title': video_data.get('title', f'Video {video_id}'),
                                    'author': api_data.get('title', channel_name) if api_data else channel_name,
                                    'authorId': channel_id,
                                    'lengthSeconds': duration_seconds,
                                    'viewCount': view_count,
                                    'publishedText': video_data.get('published', ''),
                                    'videoThumbnails': [
                                        {'url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'},
                                        {'url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'}
                                    ]
                                }
                                playlist_videos.append(video)
                                all_videos.append(video)  # 全体リスト用
                    
                    # プレイリスト情報を保存（動画がある場合のみ）
                    if playlist_videos:
                        playlists.append({
                            'name': playlist_name,
                            'videos': playlist_videos,
                            'video_count': len(playlist_videos)
                        })
            
            # 従来の全体動画リスト用（後方互換性のため）
            seen_ids = set()
            for video_data in all_videos:
                if isinstance(video_data, dict) and video_data.get('videoId'):
                    video_id = video_data.get('videoId')
                    if video_id and video_id not in seen_ids:
                        seen_ids.add(video_id)
                        videos.append(video_data)  # 既に処理済みの動画データを使用
            
            # ソート処理
            if sort == 'oldest':
                videos.reverse()
            elif sort == 'popular':
                videos.sort(key=lambda x: x.get('viewCount', 0), reverse=True)
        
        # ページネーション設定（簡易版）
        videos = videos or []
        total_pages = max(1, page + (1 if len(videos) >= 20 else 0))
        
        # チャンネル情報が無い場合の最終フォールバック
        if not channel_info:
            channel_info = {
                'author': videos[0].get('author', channel_name) if videos else (channel_name or f'チャンネル ({channel_id})'),
                'authorId': channel_id,
                'description': 'チャンネル動画一覧',
                'subCount': 0,
                'totalViews': 0,
                'videoCount': len(videos) if videos else 0,
                'joined': 0,
                'authorThumbnails': videos[0].get('authorThumbnails', []) if videos else [
                    {'url': f'https://yt3.ggpht.com/a/default-user=s176-c-k-c0x00ffffff-no-rj'}
                ],
                'authorBanners': [],
                'autoGenerated': False
            }
        
        return render_template('channel.html',
                             channel_info=channel_info,
                             videos=videos,
                             playlists=playlists,
                             current_page=page,
                             total_pages=total_pages,
                             sort=sort)
        
    except Exception as e:
        logging.error(f"Channel page error: {e}")
        channel_name = request.args.get('name', '')
        
        # エラー時も基本的なページを表示
        channel_info = {
            'author': channel_name if channel_name else f'チャンネル ({channel_id})',
            'authorId': channel_id,
            'description': 'チャンネル情報の読み込み中にエラーが発生しました。',
            'subCount': 0,
            'totalViews': 0,
            'videoCount': 0,
            'joined': 0,
            'authorThumbnails': [],
            'authorBanners': [],
            'autoGenerated': False
        }
        
        return render_template('channel.html',
                             channel_info=channel_info,
                             videos=[],
                             playlists=[],
                             current_page=1,
                             total_pages=1,
                             sort='newest',
                             error="チャンネル情報の読み込み中にエラーが発生しました")

@app.route('/shorts')
def shorts():
    """ショート動画メインページ（最初の動画にリダイレクト）"""
    try:
        # 最初のショート動画を取得
        response = api_shorts_list()
        if hasattr(response, 'get_json'):
            response_data = response.get_json()
        else:
            response_data = response
            
        if response_data.get('success') and response_data.get('videos'):
            first_video_id = response_data['videos'][0]['videoId']
            return redirect(url_for('shorts_video', video_id=first_video_id))
        else:
            return render_template('shorts.html', error="ショート動画が見つかりません")
    except Exception as e:
        logging.error(f"ショート動画リダイレクトエラー: {e}")
        return render_template('shorts.html', error="エラーが発生しました")

@app.route('/shorts/<video_id>')
def shorts_video(video_id):
    """個別ショート動画ページ"""
    try:
        # 動画情報を取得
        video_info = invidious.get_video_info(video_id)
        if not video_info:
            return redirect(url_for('shorts'))
        
        # 視聴履歴を記録
        user_prefs.record_watch(video_info)
        
        # コメントを取得
        comments_data = {'comments': [], 'continuation': None}
        try:
            comments_data = invidious.get_video_comments(video_id)
        except Exception as e:
            logging.warning(f"Comments error: {e}")
        
        return render_template('shorts.html', 
                             current_video=video_info,
                             current_video_id=video_id,
                             comments_data=comments_data)
    except Exception as e:
        logging.error(f"ショート動画取得エラー: {e}")
        return redirect(url_for('shorts'))

@app.route('/api/shorts-list')
def api_shorts_list():
    """個人化された日本のショート動画リストAPI - 大幅改善版"""
    try:
        shorts_videos = []
        
        # ユーザーの好みに基づいた推奨キーワードを取得
        recommended_keywords = user_prefs.get_recommendation_keywords()
        logging.info(f"推奨キーワード: {recommended_keywords[:5]}")
        
        # より多くのソースから動画を収集
        search_queries = []
        
        # 好みのチャンネルからの動画を優先検索
        preferred_channels = user_prefs.get_preferred_channels()
        for channel_name, count in preferred_channels[:5]:  # 上位5チャンネル
            search_queries.append(f"channel:{channel_name}")
        
        # 推奨キーワード追加
        search_queries.extend(recommended_keywords[:15])
        
        # 日本の人気ジャンル追加
        popular_genres = [
            "面白い", "おもしろ", "爆笑", "ネタ", "コメディ",
            "料理", "レシピ", "簡単", "DIY", "手作り",
            "ダンス", "踊り", "TikTok", "バズった",
            "猫", "犬", "ペット", "動物", "可愛い",
            "ゲーム", "実況", "攻略", "プレイ",
            "メイク", "ファッション", "コーデ", "美容",
            "スポーツ", "サッカー", "野球", "バスケ",
            "歌ってみた", "弾いてみた", "演奏", "カバー",
            "vlog", "日常", "ルーティン", "モーニング"
        ]
        search_queries.extend(popular_genres)
        
        # 検索実行
        for query in search_queries[:25]:  # 最大25クエリ
            try:
                search_results = invidious.search_videos(query, page=1)
                if search_results and isinstance(search_results, list):
                    videos_list = search_results[:6]  # 各クエリから6件
                elif search_results and hasattr(search_results, 'get') and search_results.get('success'):
                    videos_list = search_results.get('videos', [])[:6]
                else:
                    videos_list = []
                
                for video in videos_list:
                        duration = video.get('lengthSeconds', 0)
                        if 10 <= duration <= 300:  # 10秒～5分に拡大
                            video_id = video.get('videoId')
                            if video_id not in [v.get('videoId') for v in shorts_videos]:
                                if user_prefs.should_recommend_video(video):
                                    shorts_videos.append(video)
                                    if len(shorts_videos) >= 80:  # 80件まで収集
                                        break
                
                if len(shorts_videos) >= 80:
                    break
                    
            except Exception as e:
                logging.warning(f"検索エラー ({query}): {e}")
                continue
        
        # トレンド動画からも大量追加
        trending_types = ['', 'Music', 'Gaming']
        for trend_type in trending_types:
            if len(shorts_videos) >= 80:
                break
                
            try:
                if trend_type:
                    trending_videos = invidious.get_trending_videos(region='JP')
                else:
                    trending_videos = invidious.get_trending_videos(region='JP')
                
                if trending_videos:
                    videos_list = trending_videos if isinstance(trending_videos, list) else trending_videos.get('videos', [])
                    for video in videos_list[:15]:  # トレンドから15件
                        duration = video.get('lengthSeconds', 0)
                        if 10 <= duration <= 300:  # 範囲拡大
                            video_id = video.get('videoId')
                            if video_id not in [v.get('videoId') for v in shorts_videos]:
                                if user_prefs.should_recommend_video(video):
                                    shorts_videos.append(video)
                                    if len(shorts_videos) >= 80:
                                        break
            except Exception as e:
                logging.warning(f"トレンド動画取得エラー: {e}")
        
        # 多様性を保つため、ランダムに並び替え
        import random
        random.shuffle(shorts_videos)
        
        # 短い動画を優先しつつ、多様性も保つ
        shorts_videos.sort(key=lambda x: (x.get('lengthSeconds', 0), random.random()))
        
        logging.info(f"ショート動画 {len(shorts_videos)} 件を取得")
        
        return jsonify({
            'success': True,
            'videos': shorts_videos,  # 全件返す
            'has_more': True,  # 常に追加読み込み可能
            'total': len(shorts_videos)
        })
    except Exception as e:
        logging.error(f"ショート動画リスト取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'videos': []
        })

@app.route('/api/shorts-next/<current_video_id>')
def api_shorts_next(current_video_id):
    """次のショート動画を取得"""
    try:
        # 現在の動画リストを取得
        response = api_shorts_list()
        if hasattr(response, 'get_json'):
            response_data = response.get_json()
        else:
            response_data = response
            
        if not response_data or not response_data.get('success'):
            return jsonify({'success': False, 'error': 'No videos available'})
        
        videos = response_data.get('videos', [])
        current_index = -1
        
        # 現在の動画のインデックスを探す
        for i, video in enumerate(videos):
            if video.get('videoId') == current_video_id:
                current_index = i
                break
        
        # 次の動画を取得
        next_index = current_index + 1
        if next_index < len(videos):
            return jsonify({
                'success': True,
                'video': videos[next_index],
                'has_next': next_index + 1 < len(videos)
            })
        else:
            # 新しい動画を生成して追加
            import random
            additional_keywords = ["エンタメ", "動物", "グルメ", "スポーツ", "技術"]
            for keyword in additional_keywords:
                try:
                    search_results = invidious.search_videos(keyword, page=random.randint(1, 3))
                    for video in search_results[:2]:
                        duration = video.get('lengthSeconds', 0)
                        if 15 <= duration <= 180:
                            if user_prefs.should_recommend_video(video):
                                return jsonify({
                                    'success': True,
                                    'video': video,
                                    'has_next': True
                                })
                except:
                    continue
            
            return jsonify({'success': False, 'error': 'No more videos'})
            
    except Exception as e:
        logging.error(f"次の動画取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/shorts-prev/<current_video_id>')
def api_shorts_prev(current_video_id):
    """前のショート動画を取得"""
    try:
        response = api_shorts_list()
        if hasattr(response, 'get_json'):
            response_data = response.get_json()
        else:
            response_data = response
            
        if not response_data or not response_data.get('success'):
            return jsonify({'success': False, 'error': 'No videos available'})
        
        videos = response_data.get('videos', [])
        current_index = -1
        
        for i, video in enumerate(videos):
            if video.get('videoId') == current_video_id:
                current_index = i
                break
        
        prev_index = current_index - 1
        if prev_index >= 0:
            return jsonify({
                'success': True,
                'video': videos[prev_index],
                'has_prev': prev_index > 0
            })
        else:
            return jsonify({'success': False, 'error': 'No previous videos'})
            
    except Exception as e:
        logging.error(f"前の動画取得エラー: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/stream/<video_id>')
def api_stream(video_id):
    """APIエンドポイント：動画ストリーム取得 - 240p程度の低画質"""
    try:
        # siawaseok APIから低画質ストリームを取得
        external_url = f"https://siawaseok.duckdns.org/api/stream/{video_id}/"
        logging.info(f"Requesting siawaseok API: {external_url}")
        
        response = requests.get(external_url, timeout=15)
        logging.info(f"siawaseok API response status: {response.status_code}")
        
        if response.status_code == 200:
            external_data = response.json()
            logging.info(f"siawaseok API data structure: {list(external_data.keys()) if isinstance(external_data, dict) else 'not dict'}")
            
            # siawaseok APIの構造に基づいて低画質ストリームを選択
            if isinstance(external_data, dict):
                # 360p（音声付き）を優先
                if 'muxed360p' in external_data and external_data['muxed360p']:
                    return jsonify({
                        "success": True,
                        "stream_url": external_data['muxed360p'],
                        "audio_url": "",
                        "has_audio": True,  # muxedは音声付き
                        "title": external_data.get('title', ''),
                        "duration": external_data.get('duration', 0),
                        "quality": "360p",
                        "source": "siawaseok"
                    })
                
                # 音声のみの場合
                elif 'audio' in external_data and external_data['audio']:
                    return jsonify({
                        "success": True,
                        "stream_url": external_data['audio'],
                        "audio_url": external_data['audio'],
                        "has_audio": True,
                        "title": external_data.get('title', ''),
                        "duration": external_data.get('duration', 0),
                        "quality": "audio_only",
                        "source": "siawaseok"
                    })
        
        # API失敗時
        return jsonify({
            "success": False,
            "error": "動画を取得できませんでした。",
            "status_code": 0
        }), 404
            
    except Exception as e:
        logging.error(f"ストリームAPI エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stream/<video_id>/type2')
def api_stream_type2(video_id):
    """APIエンドポイント：type2ストリーム取得（低画質対応）"""
    try:
        # siawaseok.duckdns.orgのtype2エンドポイントから取得
        external_url = f"https://siawaseok.duckdns.org/api/stream/{video_id}/type2"
        logging.info(f"Type2 API request: {external_url}")
        
        response = requests.get(external_url, timeout=15)
        logging.info(f"Type2 API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"Type2 API data structure: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
            
            # type2 APIの構造に基づいて低画質ストリームを選択
            if isinstance(data, dict):
                # URLが直接含まれている場合（YouTube Education用）
                if 'url' in data:
                    return jsonify({
                        "success": True,
                        "stream_url": data['url'],
                        "quality": "embedded",
                        "source": "siawaseok_type2"
                    })
                
                # 360pを優先（低画質）
                elif 'muxed360p' in data and data['muxed360p']:
                    return jsonify({
                        "success": True,
                        "stream_url": data['muxed360p'],
                        "audio_url": data.get('audio', ''),
                        "has_audio": True,
                        "quality": "360p",
                        "source": "siawaseok_type2"
                    })
                
                # 直接返す（既存形式との互換性）
                else:
                    return jsonify(data)
        else:
            logging.error(f"Type2 API error: {response.status_code} - {response.text[:200]}")
            return jsonify({
                "success": False,
                "error": f"動画を取得できませんでした。",
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        logging.error(f"Type2ストリームAPI エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




@app.route('/suggest')
def suggest_api():
    """検索予測変換API エンドポイント"""
    keyword = request.args.get('q', '').strip()
    
    if not keyword:
        return jsonify([])
    
    suggestions = suggest(keyword)
    return jsonify(suggestions)

# プレイリスト・高度動画機能 (@distube/ytpl, @distube/ytdl-core)
@app.route('/api/playlist')
def api_playlist_info():
    """プレイリスト情報取得API（@distube/ytpl使用）"""
    playlist_url = request.args.get('url', '').strip()
    
    if not playlist_url:
        return jsonify({
            'success': False,
            'error': 'プレイリストURLを指定してください'
        }), 400
    
    try:
        logging.info(f"プレイリスト情報取得リクエスト: {playlist_url}")
        result = turbo_service.get_playlist_info(playlist_url)
        
        if result.get('success'):
            logging.info(f"プレイリスト取得成功: {result.get('title', 'Unknown')} ({result.get('totalItems', 0)}件)")
            return jsonify(result)
        else:
            logging.error(f"プレイリスト取得失敗: {result.get('error', 'Unknown error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logging.error(f"プレイリストAPI例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/advanced-video/<video_id>')
def api_advanced_video_info(video_id):
    """高度な動画情報取得API（@distube/ytdl-core使用）"""
    try:
        logging.info(f"高度な動画情報取得リクエスト: {video_id}")
        result = turbo_service.get_advanced_video_info(video_id)
        
        if result.get('success'):
            logging.info(f"高度な動画情報取得成功: {result.get('title', 'Unknown')}")
            return jsonify(result)
        else:
            logging.error(f"高度な動画情報取得失敗: {result.get('error', 'Unknown error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logging.error(f"高度な動画情報API例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/batch-playlists', methods=['POST'])
def api_batch_playlists():
    """複数プレイリスト一括取得API"""
    try:
        data = request.get_json()
        if not data or 'playlist_urls' not in data:
            return jsonify({
                'success': False,
                'error': 'playlist_urls配列を指定してください'
            }), 400
        
        playlist_urls = data['playlist_urls']
        if not isinstance(playlist_urls, list) or len(playlist_urls) == 0:
            return jsonify({
                'success': False,
                'error': '有効なプレイリストURL配列を指定してください'
            }), 400
        
        if len(playlist_urls) > 50:  # 上限設定
            return jsonify({
                'success': False,
                'error': 'プレイリストは最大50件まで指定可能です'
            }), 400
        
        logging.info(f"プレイリスト一括取得リクエスト: {len(playlist_urls)}件")
        result = turbo_service.batch_get_playlists(playlist_urls)
        
        logging.info(f"プレイリスト一括取得結果: {result.get('successful', 0)}/{result.get('totalRequested', 0)}")
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"プレイリスト一括取得API例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/channel-playlists')
def api_channel_playlists():
    """チャンネルプレイリスト取得API"""
    channel_url = request.args.get('url', '').strip()
    
    if not channel_url:
        return jsonify({
            'success': False,
            'error': 'チャンネルURLを指定してください'
        }), 400
    
    try:
        logging.info(f"チャンネルプレイリスト取得リクエスト: {channel_url}")
        result = turbo_service.get_channel_playlists(channel_url)
        
        if result.get('success'):
            logging.info(f"チャンネルプレイリスト取得成功: {result.get('channelName', 'Unknown')} ({len(result.get('playlists', []))}件)")
            return jsonify(result)
        else:
            logging.error(f"チャンネルプレイリスト取得失敗: {result.get('error', 'Unknown error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logging.error(f"チャンネルプレイリストAPI例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stream-fallback/<video_id>')
def api_stream_fallback(video_id):
    """フォールバック機能付きストリーム取得API"""
    try:
        # マルチストリームサービスを使用（フォールバック機能付き）
        result = multi_stream_service.get_video_stream_info(video_id)
        
        if result:
            # siawaseok互換フォーマットに変換
            response_data = {
                "success": True,
                "video_id": video_id,
                "title": result.get('title', ''),
                "duration": result.get('duration', 0),
                "author": result.get('author', ''),
                "thumbnail": result.get('thumbnail', ''),
                "view_count": result.get('view_count', 0),
                "description": result.get('description', ''),
                "1080p": result.get('1080p', ''),
                "720p": result.get('720p', ''),
                "360p": result.get('360p', ''),
                "muxed360p": result.get('muxed360p', ''),
                "audio": result.get('audio', ''),
                "source": result.get('source', 'fallback')
            }
            
            logging.info(f"フォールバックストリーム取得成功: {video_id} - ソース: {result.get('source', 'unknown')}")
            return jsonify(response_data)
        else:
            logging.error(f"フォールバックストリーム取得失敗: {video_id}")
            return jsonify({
                "success": False,
                "error": "すべてのストリーム取得方法が失敗しました"
            }), 404
            
    except Exception as e:
        logging.error(f"フォールバックストリームAPI例外 ({video_id}): {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/fallback-status')
def api_fallback_status():
    """フォールバック機能の状態確認API"""
    try:
        status = multi_stream_service.get_fallback_status()
        endpoint_status = multi_stream_service.get_endpoint_status()
        
        return jsonify({
            "success": True,
            "fallback": status,
            "endpoints": endpoint_status,
            "features": {
                "external_api_endpoints": len(multi_stream_service.api_endpoints),
                "fallback_methods": status['available_methods'],
                "cache_enabled": True
            }
        })
        
    except Exception as e:
        logging.error(f"フォールバック状態API例外: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/fallback-toggle', methods=['POST'])
def api_fallback_toggle():
    """フォールバック機能のON/OFF切り替えAPI"""
    try:
        data = request.get_json() or {}
        enable = data.get('enable')  # True, False, またはNone（トグル）
        
        new_status = multi_stream_service.toggle_fallback(enable)
        
        return jsonify({
            "success": True,
            "fallback_enabled": new_status,
            "message": f"フォールバック機能を{'有効' if new_status else '無効'}にしました"
        })
        
    except Exception as e:
        logging.error(f"フォールバック切り替えAPI例外: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/processing-mode-toggle', methods=['POST'])
def api_processing_mode_toggle():
    """処理優先順位切り替えAPI（直接生成優先 ↔ 外部API優先）"""
    try:
        data = request.get_json() or {}
        direct_first = data.get('direct_first')  # True, False, またはNone（トグル）
        
        new_mode = multi_stream_service.toggle_processing_mode(direct_first)
        status = multi_stream_service.get_fallback_status()
        
        mode_text = '高速直接生成優先' if status['direct_generation_first'] else '外部API優先'
        
        return jsonify({
            "success": True,
            "processing_mode": new_mode,
            "direct_generation_first": status['direct_generation_first'],
            "message": f"処理モードを{mode_text}に変更しました"
        })
        
    except Exception as e:
        logging.error(f"処理モード切り替えAPI例外: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/<video_id>')
def api_youtube_education_url(video_id):
    """YouTube Education埋め込みURL取得API（完全なパラメータ付き）"""
    try:
        if not video_id or len(video_id) != 11:
            return jsonify({
                "success": False,
                "error": "無効な動画IDです"
            }), 400
        
        # マルチストリームサービスから完全なYouTube Education URLを生成
        youtube_education_url = multi_stream_service.get_direct_youtube_embed_url(video_id, "education")
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "youtube_education_url": youtube_education_url,
            "embed_type": "youtube_education"
        })
        
    except Exception as e:
        logging.error(f"YouTube Education URL取得API例外 ({video_id}): {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/<video_id>/2')
def api_stream_urls(video_id):
    """ストリームURL取得API"""
    try:
        if not video_id or len(video_id) != 11:
            return jsonify({
                "success": False,
                "error": "無効な動画IDです"
            }), 400
        
        # マルチストリームサービスでストリーム情報取得
        stream_data = multi_stream_service.get_video_stream_info(video_id)
        
        if not stream_data:
            return jsonify({
                "success": False,
                "error": "ストリーム情報の取得に失敗しました"
            }), 404
        
        # ストリームURL情報を整理
        streams = {}
        if 'muxed360p' in stream_data:
            streams['360p'] = stream_data['muxed360p']
        if '720p' in stream_data:
            streams['720p'] = stream_data['720p']
        if '1080p' in stream_data:
            streams['1080p'] = stream_data['1080p']
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "streams": streams,
            "available_qualities": list(streams.keys())
        })
        
    except Exception as e:
        logging.error(f"ストリームURL取得API例外 ({video_id}): {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/music')
def music():
    """音楽ストリーミングページ - siawaseok API音楽データ表示"""
    trending_music = []
    
    try:
        # siawaseok APIからトレンド動画を取得
        logging.info("siawaseok APIから音楽トレンドデータを取得中...")
        trend_data = multi_stream_service.get_trending_videos()
        
        if trend_data and isinstance(trend_data, dict):
            # 'music'キーを優先的に使用
            music_videos = []
            if 'music' in trend_data and isinstance(trend_data['music'], list):
                music_videos = trend_data['music']
                logging.info(f"siawaseok music APIから {len(music_videos)} 件の音楽を取得")
            elif 'trending' in trend_data and isinstance(trend_data['trending'], list):
                # フォールバック: トレンドから音楽をフィルタリング
                all_videos = trend_data['trending']
                music_videos = [v for v in all_videos if is_music_content(v)]
                logging.info(f"トレンドから {len(music_videos)} 件の音楽をフィルタリング")
            
            # 音楽データを統一形式に変換
            seen_ids = set()
            for video_data in music_videos[:50]:  # 最大50件
                if isinstance(video_data, dict):
                    video_id = video_data.get('videoId') or video_data.get('id')
                    
                    if video_id and video_id not in seen_ids:
                        seen_ids.add(video_id)
                        
                        # duration値を安全に変換
                        duration_raw = video_data.get('lengthSeconds') or video_data.get('duration', 0)
                        try:
                            duration_seconds = int(duration_raw) if duration_raw else 0
                        except (ValueError, TypeError):
                            duration_seconds = 0
                        
                        # viewCount値を安全に変換
                        view_count_raw = video_data.get('viewCount') or video_data.get('view_count', 0)
                        try:
                            view_count = int(view_count_raw) if view_count_raw else 0
                        except (ValueError, TypeError):
                            view_count = 0
                        
                        # アーティスト名を取得
                        artist_name = (video_data.get('author') or 
                                     video_data.get('uploader') or 
                                     video_data.get('uploaderName') or
                                     video_data.get('channelName') or 
                                     'Unknown Artist')
                        
                        # 音楽トラック形式に変換
                        music_track = {
                            'id': video_id,
                            'videoId': video_id,
                            'title': video_data.get('title', f'Track {video_id}'),
                            'artist': artist_name,
                            'duration': duration_seconds,
                            'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                            'artwork_url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                            'playback_count': view_count,
                            'genre': 'Music',
                            'permalink_url': f'https://youtube.com/watch?v={video_id}'
                        }
                        trending_music.append(music_track)
        
        logging.info(f"音楽ページ用に {len(trending_music)} 件の音楽トラックを準備")
        
    except Exception as e:
        logging.error(f"音楽トレンド取得エラー: {e}")
        # フォールバック: Invidiousから音楽を取得
        try:
            trending_videos = invidious.get_trending_videos()
            if trending_videos:
                for video in trending_videos[:30]:
                    if is_music_content(video):
                        music_track = {
                            'id': video.get('videoId'),
                            'videoId': video.get('videoId'),
                            'title': video.get('title', ''),
                            'artist': video.get('author', 'Unknown Artist'),
                            'duration': video.get('lengthSeconds', 0),
                            'thumbnail': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                            'artwork_url': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                            'playback_count': video.get('viewCount', 0),
                            'genre': 'Music'
                        }
                        trending_music.append(music_track)
            logging.info(f"フォールバックで {len(trending_music)} 件の音楽を取得")
        except Exception as e2:
            logging.error(f"音楽フォールバックも失敗: {e2}")
    
    return render_template('music.html', trending_music=trending_music)

def is_music_content(video_data):
    """動画が音楽コンテンツかどうかを判定"""
    if not video_data:
        return False
    
    title = str(video_data.get('title', '')).lower()
    duration = video_data.get('lengthSeconds', 0)
    
    # 音楽関連キーワードと適切な長さをチェック
    music_keywords = ['music', 'song', 'mv', 'official', 'audio', '歌', '音楽', 'ミュージック', 
                     'cover', 'live', 'concert', 'album', 'single', 'remix', 'acoustic']
    
    has_music_keyword = any(keyword in title for keyword in music_keywords)
    is_appropriate_length = 30 <= duration <= 1800  # 30秒〜30分
    
    return has_music_keyword and is_appropriate_length

@app.route('/music/api/stream/<video_id>')
def music_api_stream(video_id):
    """音楽ストリーミング用API - 音声のみのストリームURL取得"""
    try:
        if not video_id or len(video_id) != 11:
            return jsonify({
                "success": False,
                "error": "無効な動画IDです"
            }), 400
        
        # ytdl_serviceから音声ストリームを取得
        audio_url = ytdl._get_audio_stream(video_id)
        
        if audio_url:
            return jsonify({
                "success": True,
                "video_id": video_id,
                "audio_url": audio_url,
                "format": "audio_only"
            })
        else:
            # フォールバック1: マルチストリームサービスから取得
            stream_data = multi_stream_service.get_video_stream_info(video_id)
            if stream_data and 'audio' in stream_data:
                return jsonify({
                    "success": True,
                    "video_id": video_id,
                    "audio_url": stream_data['audio'],
                    "format": "audio_fallback"
                })
            
            # フォールバック2: YouTube Education統合（プロキシ経由）
            try:
                logging.info(f"YouTube Education音声プロキシ試行: {video_id}")
                # 専用プロキシエンドポイントを使用
                proxy_url = f"/music/api/education_stream/{video_id}"
                return jsonify({
                    "success": True,
                    "video_id": video_id,
                    "audio_url": proxy_url,
                    "format": "youtube_education_proxy",
                    "note": "YouTube Education音声プロキシ"
                })
            except Exception as e:
                logging.error(f"YouTube Education プロキシ設定エラー: {e}")
            
            return jsonify({
                "success": False,
                "error": "音声ストリームの取得に失敗しました"
            }), 404
        
    except Exception as e:
        logging.error(f"音楽ストリーミングAPI例外 ({video_id}): {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/music/api/search')
def music_api_search():
    """音楽検索API - 音楽のみの検索結果"""
    query = request.args.get('q')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    
    if not query:
        return jsonify({'error': '検索クエリが必要です', 'tracks': [], 'total': 0}), 400
    
    music_tracks = []
    
    try:
        # 音楽専用検索クエリに変換
        music_query = f"{query} music song audio official"
        
        # siawaseok APIで検索
        search_data = multi_stream_service.search_videos(music_query, page)
        
        if search_data:
            videos_list = []
            if isinstance(search_data, dict) and 'results' in search_data:
                videos_list = search_data['results']
            elif isinstance(search_data, list):
                videos_list = search_data
            
            # 音楽コンテンツのみフィルタリング
            for video_data in videos_list[:limit]:
                if isinstance(video_data, dict) and is_music_content(video_data):
                    video_id = video_data.get('videoId') or video_data.get('id')
                    if video_id:
                        music_track = {
                            'id': video_id,
                            'videoId': video_id,
                            'title': video_data.get('title', ''),
                            'artist': video_data.get('author') or video_data.get('uploader', 'Unknown Artist'),
                            'duration': video_data.get('lengthSeconds', 0),
                            'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                            'playback_count': video_data.get('viewCount', 0),
                            'genre': 'Music'
                        }
                        music_tracks.append(music_track)
        
        # フォールバック: Invidious API
        if len(music_tracks) < 5:
            try:
                search_results = invidious.search_videos(music_query, page)
                if search_results:
                    for video in search_results[:limit-len(music_tracks)]:
                        if is_music_content(video):
                            music_track = {
                                'id': video.get('videoId'),
                                'videoId': video.get('videoId'),
                                'title': video.get('title', ''),
                                'artist': video.get('author', 'Unknown Artist'),
                                'duration': video.get('lengthSeconds', 0),
                                'thumbnail': f"https://img.youtube.com/vi/{video.get('videoId')}/hqdefault.jpg",
                                'playback_count': video.get('viewCount', 0),
                                'genre': 'Music'
                            }
                            music_tracks.append(music_track)
            except Exception as e:
                logging.warning(f"Invidious検索フォールバック失敗: {e}")
        
        return jsonify({
            'success': True,
            'tracks': music_tracks, 
            'total': len(music_tracks), 
            'query': query,
            'page': page
        })
        
    except Exception as e:
        logging.error(f"音楽検索API例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tracks': [],
            'total': 0
        }), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html', error="ページが見つかりません。"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html', error="内部サーバーエラーが発生しました。"), 500

@app.route('/music/api/education_stream/<video_id>')
def music_education_stream_proxy(video_id):
    """YouTube Education音声ストリーミングプロキシ"""
    try:
        if not video_id or len(video_id) != 11:
            return jsonify({
                "success": False,
                "error": "無効な動画IDです"
            }), 400
        
        logging.info(f"YouTube Education音声プロキシ開始: {video_id}")
        
        # YouTube Education埋め込みURLを取得
        education_url = multi_stream_service.get_direct_youtube_embed_url(video_id, embed_type="education")
        if not education_url:
            logging.error(f"YouTube Education URL生成失敗: {video_id}")
            return jsonify({
                "success": False,
                "error": "YouTube Education URLの生成に失敗しました"
            }), 404
        
        logging.info(f"✅ YouTube Education URL生成成功: {education_url[:100]}...")
        
        # Education URLから音声ストリーム情報を抽出
        try:
            # ytdl-coreを使ってEducation URLから音声情報を抽出
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'noplaylist': True,
                'extract_flat': False
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 生成されたYouTube Education URLから音声を抽出
                info = ydl.extract_info(education_url, download=False)
                
                if info and 'url' in info:
                    # 直接音声URLをリダイレクト
                    logging.info(f"✅ YouTube Education音声ストリーム抽出成功")
                    return redirect(info['url'])
                else:
                    logging.error(f"YouTube Education音声URL抽出失敗: {video_id}")
                    
        except Exception as extract_error:
            logging.error(f"YouTube Education音声抽出エラー: {extract_error}")
        
        return jsonify({
            "success": False,
            "error": "YouTube Education音声ストリームの抽出に失敗しました"
        }), 404
        
    except Exception as e:
        logging.error(f"YouTube Education音声プロキシ例外 ({video_id}): {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/siawaseok-comments/<video_id>')
def siawaseok_comments_proxy(video_id):
    """siawaseok.duckdns.org/api/comments/ プロキシエンドポイント"""
    try:
        if not video_id:
            return jsonify({
                'success': False,
                'error': '動画IDが必要です'
            }), 400
        
        # siawaseok APIからコメントを取得
        siawaseok_url = f"https://siawaseok.duckdns.org/api/comments/{video_id}"
        logging.info(f"siawaseokコメント取得: {siawaseok_url}")
        
        response = requests.get(siawaseok_url, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logging.info(f"siawaseokコメント取得成功: {video_id}")
                
                # データ形式を統一
                formatted_comments = []
                comments_data = data.get('comments', []) if isinstance(data, dict) else data
                
                if isinstance(comments_data, list):
                    for comment in comments_data:
                        formatted_comment = {
                            'id': comment.get('id', f"siawaseok_{hash(str(comment))}"),
                            'author': comment.get('author', comment.get('user', {}).get('name', 'Unknown User')),
                            'authorThumbnails': comment.get('authorThumbnails', []),
                            'content': comment.get('content', comment.get('text', '')),
                            'publishedText': comment.get('publishedText', comment.get('created_at', '')),
                            'likeCount': comment.get('likeCount', comment.get('likes', 0)),
                            'replies': comment.get('replies', 0),
                            'source': 'siawaseok'
                        }
                        formatted_comments.append(formatted_comment)
                
                return jsonify({
                    'success': True,
                    'comments': formatted_comments,
                    'total': len(formatted_comments),
                    'source': 'siawaseok'
                })
                
            except json.JSONDecodeError as e:
                logging.warning(f"siawaseokコメントJSON解析エラー: {e}")
                return jsonify({
                    'success': False,
                    'error': 'コメントデータの解析に失敗しました'
                }), 500
        else:
            logging.warning(f"siawaseokコメント取得失敗: {response.status_code}")
            return jsonify({
                'success': False,
                'error': f'コメント取得失敗: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.Timeout:
        logging.warning(f"siawaseokコメント取得タイムアウト: {video_id}")
        return jsonify({
            'success': False,
            'error': 'コメント取得がタイムアウトしました'
        }), 504
        
    except requests.exceptions.RequestException as e:
        logging.error(f"siawaseokコメント取得リクエストエラー: {e}")
        return jsonify({
            'success': False,
            'error': 'コメント取得でネットワークエラーが発生しました'
        }), 503
        
    except Exception as e:
        logging.error(f"siawaseokコメント取得例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/omada-comments/<video_id>')
def omada_comments_proxy(video_id):
    """yt.omada.cafe/api/v1/comments/ プロキシエンドポイント"""
    try:
        if not video_id:
            return jsonify({
                'success': False,
                'error': '動画IDが必要です'
            }), 400
        
        # yt.omada.cafe APIからコメントを取得
        omada_url = f"https://yt.omada.cafe/api/v1/comments/{video_id}"
        logging.info(f"yt.omada.cafeコメント取得: {omada_url}")
        
        response = requests.get(omada_url, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logging.info(f"yt.omada.cafeコメント取得成功: {video_id}")
                
                # データ形式を統一
                formatted_comments = []
                comments_data = data.get('comments', []) if isinstance(data, dict) else data
                
                if isinstance(comments_data, list):
                    for comment in comments_data:
                        formatted_comment = {
                            'id': comment.get('commentId', f"omada_{hash(str(comment))}"),
                            'author': comment.get('author', comment.get('authorText', 'Unknown User')),
                            'authorThumbnails': comment.get('authorThumbnails', []),
                            'content': comment.get('content', comment.get('contentHtml', '')),
                            'publishedText': comment.get('publishedText', comment.get('published', '')),
                            'likeCount': comment.get('likeCount', 0),
                            'replies': comment.get('replies', 0),
                            'source': 'omada'
                        }
                        formatted_comments.append(formatted_comment)
                
                return jsonify({
                    'success': True,
                    'comments': formatted_comments,
                    'total': len(formatted_comments),
                    'source': 'omada'
                })
                
            except json.JSONDecodeError as e:
                logging.warning(f"yt.omada.cafeコメントJSON解析エラー: {e}")
                return jsonify({
                    'success': False,
                    'error': 'コメントデータの解析に失敗しました'
                }), 500
        else:
            logging.warning(f"yt.omada.cafeコメント取得失敗: {response.status_code}")
            return jsonify({
                'success': False,
                'error': f'コメント取得失敗: {response.status_code}'
            }), response.status_code
            
    except requests.exceptions.Timeout:
        logging.warning(f"yt.omada.cafeコメント取得タイムアウト: {video_id}")
        return jsonify({
            'success': False,
            'error': 'コメント取得がタイムアウトしました'
        }), 504
        
    except requests.exceptions.RequestException as e:
        logging.error(f"yt.omada.cafeコメント取得リクエストエラー: {e}")
        return jsonify({
            'success': False,
            'error': 'コメント取得でネットワークエラーが発生しました'
        }), 503
        
    except Exception as e:
        logging.error(f"yt.omada.cafeコメント取得例外: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/priority-comments/<video_id>')
def get_priority_comments(video_id):
    """🎯 最優先でomada.cafeからコメント取得、フォールバック付き統合エンドポイント"""
    try:
        logging.info(f"🎯 最優先コメント取得開始: {video_id}")
        
        # CustomApiServiceの優先度付きコメント取得を使用
        comments_data = custom_api_service.get_video_comments_with_priority(video_id)
        
        if comments_data:
            # コメントをフォーマット
            formatted_comments = custom_api_service.format_comments(comments_data)
            if formatted_comments:
                logging.info(f"✅ 優先度付きコメント取得成功: {len(formatted_comments)} 件")
                return jsonify({
                    'success': True,
                    'comments': formatted_comments,
                    'commentCount': len(formatted_comments),
                    'source': 'priority_omada_first',
                    'continuation': comments_data.get('continuation')
                })
        
        # 最終フォールバック: Invidious API
        logging.info(f"最終フォールバック: Invidious APIからコメント取得試行")
        try:
            invidious_comments = invidious.get_video_comments(video_id)
            if invidious_comments and invidious_comments.get('comments'):
                logging.info(f"✅ Invidious フォールバック成功: {len(invidious_comments['comments'])} 件")
                return jsonify({
                    'success': True,
                    'comments': invidious_comments['comments'],
                    'commentCount': invidious_comments.get('commentCount', len(invidious_comments['comments'])),
                    'source': 'invidious_fallback',
                    'continuation': invidious_comments.get('continuation')
                })
        except Exception as e:
            logging.warning(f"Invidious フォールバックエラー: {e}")
        
        # すべて失敗した場合
        logging.warning(f"全てのコメント取得エンドポイントが失敗: {video_id}")
        return jsonify({
            'success': True,
            'comments': [],
            'commentCount': 0,
            'source': 'none',
            'message': 'コメントが見つかりませんでした'
        })
        
    except Exception as e:
        logging.error(f"優先度付きコメント取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/<video_id>')
def api_video_info(video_id):
    """動画情報API - YouTube Education URL生成対応"""
    try:
        logging.info(f"🚀 /api/<video_id> エンドポイント実行開始: {video_id}")
        
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
                'error': '動画情報を取得できませんでした'
            }), 404
        
        # Kahoot API keyを使ってYouTube Education URL生成
        try:
            logging.info(f"🔑 Kahoot API keyでYouTube Education URL生成開始: {video_id}")
            youtube_education_url = multi_stream_service.get_direct_youtube_embed_url(video_id, "education")
            if youtube_education_url and "youtubeeducation.com" in youtube_education_url:
                logging.info(f"✅ Kahoot API keyでYouTube Education URL生成成功: {youtube_education_url[:100]}...")
            else:
                # フォールバック
                youtube_education_url = f"https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&controls=1&rel=0"
                logging.warning(f"⚠️ Kahoot方式失敗、フォールバック使用")
        except Exception as e:
            logging.warning(f"⚠️ Kahoot API keyでのYouTube Education URL生成失敗、フォールバック使用: {e}")
            youtube_education_url = f"https://www.youtubeeducation.com/embed/{video_id}?autoplay=1&controls=1&rel=0"
        
        # 利用可能な品質をフィルタリング
        available_qualities = {}
        for quality in target_qualities:
            quality_data = result['quality_streams'].get(quality, {})
            if quality_data.get('video_url') or quality_data.get('combined_url'):
                available_qualities[quality] = quality_data
                logging.info(f"✅ 品質 {quality} 追加済み")
        
        # APIレスポンス
        response = {
            'success': True,
            'video_id': video_id,
            'videoId': result.get('videoId'),
            'title': result.get('title'),
            'thumbnail': result.get('thumbnail'),
            'description': result.get('description'),
            'author': result.get('author'),
            'authorId': result.get('authorId'),
            'authorUrl': result.get('authorUrl'),
            'authorThumbnails': result.get('authorThumbnails', []),
            'viewCount': result.get('viewCount'),
            'lengthSeconds': result.get('lengthSeconds'),
            'publishedText': result.get('publishedText'),
            'embed_type': 'youtube_education',
            'youtube_education_url': youtube_education_url,
            'multi_quality': True,
            'quality_streams': available_qualities,
            'best_audio': result.get('best_audio'),
            'available_qualities': list(available_qualities.keys()),
            'source': 'yt.omada.cafe'
        }
        
        logging.info(f"✅ /api/<video_id> エンドポイント成功: {video_id}")
        logging.info(f"   利用可能品質: {list(available_qualities.keys())}")
        logging.info(f"   チャンネル: {result.get('author', 'Unknown')}")
        logging.info(f"   YouTube Education URL: {youtube_education_url[:100]}...")
        
        return jsonify(response)
        
    except Exception as e:
        logging.error(f"/api/<video_id> エンドポイントエラー: {e}")
        return jsonify({
            'success': False,
            'error': f'動画情報取得エラー: {str(e)}'
        }), 500
