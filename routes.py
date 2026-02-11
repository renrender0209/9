from flask import render_template, request, jsonify, redirect, url_for
from app import app, limiter, cache_get, cache_set
import concurrent.futures
import logging
import hashlib
import requests
import time
from multi_stream_service import MultiStreamService
from custom_api_service import CustomApiService
from vkr_downloader_service import OmadaVideoService
from user_preferences import user_prefs

multi_stream_service = MultiStreamService()
custom_api_service = CustomApiService()
video_service = OmadaVideoService()

executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)

# ==========================================
# ホームページ
# ==========================================

@app.route('/')
def index():
    cache_key = 'trending_home'
    cached = cache_get(cache_key)
    if cached:
        return render_template('index.html', trending_videos=cached)
    
    try:
        def get_trend():
            return multi_stream_service.get_trending_videos()
        
        future = executor.submit(get_trend)
        trend_data = future.result(timeout=5)
        
        videos = []
        if trend_data and isinstance(trend_data, dict):
            videos = trend_data.get('trending', [])[:50]
        
        cache_set(cache_key, videos, 300)
        return render_template('index.html', trending_videos=videos)
        
    except Exception as e:
        logging.error(f"トレンド取得エラー: {e}")
        return render_template('index.html', trending_videos=[])

# ==========================================
# 検索
# ==========================================

@app.route('/search')
@limiter.limit("30 per minute")
def search():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    
    if not query:
        return redirect(url_for('index'))
    
    cache_key = f'search_{hashlib.md5(query.encode()).hexdigest()}_{page}'
    cached = cache_get(cache_key)
    if cached:
        return render_template('search.html', **cached)
    
    try:
        videos = []
        
        def get_kahoot():
            try:
                return multi_stream_service.search_videos_with_kahoot(query, 25, page) or []
            except:
                return []
        
        def get_custom():
            try:
                results = custom_api_service.search_videos(query)
                if results:
                    return custom_api_service.format_search_results(results)[:15]
                return []
            except:
                return []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            future_k = pool.submit(get_kahoot)
            future_c = pool.submit(get_custom)
            
            try:
                videos.extend(future_k.result(timeout=4))
            except:
                pass
            
            try:
                videos.extend(future_c.result(timeout=3))
            except:
                pass
        
        seen = set()
        unique = []
        for v in videos:
            vid = v.get('videoId')
            if vid and vid not in seen:
                seen.add(vid)
                unique.append(v)
        
        result = {
            'results': unique[:30],
            'channels': [],
            'query': query,
            'page': page,
            'total_results': len(unique),
            'has_next': len(unique) >= 30,
            'has_prev': page > 1
        }
        
        cache_set(cache_key, result, 300)
        return render_template('search.html', **result)
        
    except Exception as e:
        logging.error(f"検索エラー: {e}")
        return render_template('search.html', 
            results=[], channels=[], query=query, page=page,
            total_results=0, has_next=False, has_prev=False)

# ==========================================
# 動画視聴
# ==========================================

@app.route('/watch')
def watch():
    video_id = request.args.get('v')
    if not video_id:
        return redirect(url_for('index'))
    
    cache_key = f'video_{video_id}'
    cached = cache_get(cache_key)
    if cached:
        return render_template('watch.html', **cached)
    
    try:
        video_info = None
        stream_data = None
        
        def get_omada():
            try:
                return video_service.get_stream_urls(video_id, ['720p', '480p', '360p'])
            except:
                return None
        
        def get_kahoot():
            try:
                return multi_stream_service.get_video_info_from_kahoot(video_id)
            except:
                return None
        
        def get_custom():
            try:
                data = custom_api_service.get_video_info(video_id)
                if data:
                    return custom_api_service.format_video_info(data)
                return None
            except:
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(get_omada): 'omada',
                pool.submit(get_kahoot): 'kahoot',
                pool.submit(get_custom): 'custom'
            }
            
            for future in concurrent.futures.as_completed(futures, timeout=6):
                source = futures[future]
                try:
                    result = future.result()
                    if result:
                        if source == 'omada' and not stream_data:
                            stream_data = result
                        elif not video_info:
                            video_info = result
                        
                        if stream_data and video_info:
                            break
                except Exception as e:
                    logging.warning(f"{source} 失敗: {e}")
        
        if not video_info:
            video_info = {
                'videoId': video_id,
                'title': f'動画 {video_id}',
                'author': '不明',
                'authorId': '',
                'description': '',
                'lengthSeconds': 0,
                'viewCount': 0,
                'publishedText': ''
            }
        
        render_data = {
            'video_info': video_info,
            'stream_data': stream_data,
            'comments_data': {'comments': [], 'continuation': None}
        }
        
        cache_set(cache_key, render_data, 600)
        
        if video_info and video_info.get('title') != f'動画 {video_id}':
            user_prefs.record_watch(video_info)
        
        return render_template('watch.html', **render_data)
        
    except Exception as e:
        logging.error(f"動画表示エラー: {e}")
        return redirect(url_for('index'))

# ==========================================
# 関連動画API
# ==========================================

@app.route('/api/related-videos/<video_id>')
@limiter.limit("60 per minute")
def api_related_videos(video_id):
    cache_key = f'related_{video_id}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    
    try:
        query = request.args.get('q', '')[:50]
        
        def get_kahoot():
            try:
                return multi_stream_service.search_videos_with_kahoot(query, 12, 1) or []
            except:
                return []
        
        def get_siawaseok():
            try:
                r = requests.get("https://siawaseok.duckdns.org/api/trend", timeout=3)
                if r.status_code == 200:
                    d = r.json()
                    videos = []
                    for cat in ['trending', 'music', 'gaming']:
                        if cat in d:
                            videos.extend(d[cat][:4])
                    return videos
                return []
            except:
                return []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            future_k = pool.submit(get_kahoot)
            future_s = pool.submit(get_siawaseok)
            
            all_videos = []
            
            try:
                all_videos.extend(future_k.result(timeout=4))
            except:
                pass
            
            try:
                all_videos.extend(future_s.result(timeout=3))
            except:
                pass
        
        seen = set()
        unique = []
        for v in all_videos:
            vid = v.get('videoId')
            if vid and vid != video_id and vid not in seen:
                seen.add(vid)
                unique.append(v)
                if len(unique) >= 20:
                    break
        
        result = {
            'success': True,
            'videos': unique,
            'total': len(unique)
        }
        
        cache_set(cache_key, result, 600)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"関連動画エラー: {e}")
        return jsonify({'success': False, 'videos': []})

# ==========================================
# コメントAPI
# ==========================================

@app.route('/api/comments/<video_id>')
@limiter.limit("30 per minute")
def get_comments(video_id):
    cache_key = f'comments_{video_id}'
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)
    
    try:
        response = requests.get(
            f"https://siawaseok.duckdns.org/api/comments/{video_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            result = {
                'success': True,
                'comments': response.json(),
                'source': 'siawaseok'
            }
            cache_set(cache_key, result, 300)
            return jsonify(result)
    except:
        pass
    
    return jsonify({'success': False, 'comments': []})

# ==========================================
# 検索候補API
# ==========================================

@app.route('/api/suggest')
def suggest_api():
    keyword = request.args.get('q', '')
    if not keyword or len(keyword) < 2:
        return jsonify([])
    
    try:
        import urllib.parse
        url = f"http://www.google.com/complete/search?client=youtube&hl=ja&ds=yt&q={urllib.parse.quote(keyword)}"
        response = requests.get(url, timeout=3)
        
        if response.status_code == 200:
            import json
            json_text = response.text[19:-1]
            data = json.loads(json_text)
            suggestions = [item[0] for item in data[1]]
            return jsonify(suggestions[:8])
    except:
        pass
    
    return jsonify([])

# ==========================================
# ヘルスチェック
# ==========================================

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'cache_size': len(cache_store),
        'timestamp': time.time()
    })

# ==========================================
# テンプレートフィルター
# ==========================================

@app.template_filter('format_view_count')
def format_view_count(count):
    if not count or count == 0:
        return 'N/A'
    
    try:
        count = int(count)
        if count >= 100000000:
            return f"{count // 100000000}億{(count % 100000000) // 10000:,}万" if (count % 100000000) // 10000 > 0 else f"{count // 100000000}億"
        elif count >= 10000:
            return f"{count // 10000}万{count % 10000:,}" if count % 10000 > 0 else f"{count // 10000}万"
        else:
            return f"{count:,}"
    except:
        return 'N/A'

@app.template_filter('format_view_count_with_suffix')
def format_view_count_with_suffix(count):
    formatted = format_view_count(count)
    if formatted == 'N/A':
        return '視聴回数不明'
    return f"{formatted}回視聴"

@app.template_filter('format_duration_japanese')
def format_duration_japanese_filter(seconds):
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
    except:
        return ''

@app.template_filter('format_published_japanese')
def format_published_japanese_filter(published_text):
    if not published_text:
        return ''
    
    try:
        if 'T' in published_text and published_text.endswith('Z'):
            from datetime import datetime, timezone
            published_date = datetime.fromisoformat(published_text.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            diff = now - published_date
            
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
            return published_text
            
    except Exception as e:
        logging.warning(f"日付フォーマットエラー: {published_text}")
        return published_text