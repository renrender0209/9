"""
ユーザーの視聴履歴と推奨システム
"""
import json
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class UserPreferences:
    def __init__(self):
        self.data_file = "user_data.json"
        self.load_data()
    
    def load_data(self):
        """ユーザーデータを読み込み"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.watch_history = data.get('watch_history', [])
                    self.search_history = data.get('search_history', [])
                    self.liked_videos = data.get('liked_videos', [])
                    self.preferred_channels = data.get('preferred_channels', {})
                    self.preferred_keywords = data.get('preferred_keywords', {})
            else:
                self.watch_history = []
                self.search_history = []
                self.liked_videos = []
                self.preferred_channels = {}
                self.preferred_keywords = {}
        except Exception as e:
            logging.error(f"ユーザーデータ読み込みエラー: {e}")
            self.watch_history = []
            self.search_history = []
            self.liked_videos = []
            self.preferred_channels = {}
            self.preferred_keywords = {}
    
    def save_data(self):
        """ユーザーデータを保存"""
        try:
            data = {
                'watch_history': self.watch_history,
                'search_history': self.search_history,
                'liked_videos': self.liked_videos,
                'preferred_channels': self.preferred_channels,
                'preferred_keywords': self.preferred_keywords
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"ユーザーデータ保存エラー: {e}")
    
    def record_watch(self, video_info):
        """動画視聴を記録"""
        try:
            watch_record = {
                'video_id': video_info.get('videoId'),
                'title': video_info.get('title'),
                'author': video_info.get('author'),
                'author_id': video_info.get('authorId'),
                'duration': video_info.get('lengthSeconds', 0),
                'keywords': video_info.get('keywords', []),
                'genre': video_info.get('genre'),
                'timestamp': datetime.now().isoformat()
            }
            
            self.watch_history.append(watch_record)
            
            # 履歴が100件を超えたら古いものを削除
            if len(self.watch_history) > 100:
                self.watch_history = self.watch_history[-100:]
            
            # チャンネル好みを更新
            author = video_info.get('author')
            if author:
                self.preferred_channels[author] = self.preferred_channels.get(author, 0) + 1
            
            # キーワード好みを更新
            keywords = video_info.get('keywords', [])
            for keyword in keywords[:5]:  # 最初の5個のキーワードのみ
                self.preferred_keywords[keyword] = self.preferred_keywords.get(keyword, 0) + 1
            
            self.save_data()
        except Exception as e:
            logging.error(f"視聴記録エラー: {e}")
    
    def record_search(self, query):
        """検索クエリを記録"""
        try:
            search_record = {
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
            
            self.search_history.append(search_record)
            
            # 検索履歴が50件を超えたら古いものを削除
            if len(self.search_history) > 50:
                self.search_history = self.search_history[-50:]
            
            self.save_data()
        except Exception as e:
            logging.error(f"検索記録エラー: {e}")
    
    def record_like(self, video_id):
        """いいねを記録"""
        try:
            if video_id not in self.liked_videos:
                self.liked_videos.append(video_id)
                self.save_data()
        except Exception as e:
            logging.error(f"いいね記録エラー: {e}")
    
    def get_recommendation_keywords(self):
        """推奨キーワードを取得"""
        try:
            # 最近の視聴履歴（7日以内）を重視
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_keywords = []
            
            for record in self.watch_history:
                try:
                    timestamp = datetime.fromisoformat(record['timestamp'])
                    if timestamp > recent_cutoff:
                        recent_keywords.extend(record.get('keywords', []))
                except:
                    continue
            
            # 頻度の高いキーワードを抽出
            keyword_counts = Counter(recent_keywords)
            top_keywords = [keyword for keyword, count in keyword_counts.most_common(10)]
            
            # 好みのチャンネルからキーワードを追加
            top_channels = sorted(self.preferred_channels.items(), 
                                key=lambda x: x[1], reverse=True)[:5]
            
            # 検索履歴からもキーワードを抽出
            recent_searches = []
            for search in self.search_history[-10:]:  # 最新10件の検索
                recent_searches.append(search['query'])
            
            # 日本のコンテンツ向けベースキーワード
            base_keywords = [
                "日本", "アニメ", "ゲーム", "音楽", "料理", "旅行", 
                "ペット", "猫", "犬", "可愛い", "面白い", "ダンス"
            ]
            
            # 推奨キーワードを組み合わせ
            recommendation_keywords = top_keywords + recent_searches + base_keywords
            
            # 重複を除去し、最初の15個を返す
            seen = set()
            unique_keywords = []
            for keyword in recommendation_keywords:
                if keyword and keyword not in seen and len(keyword) > 1:
                    seen.add(keyword)
                    unique_keywords.append(keyword)
                    if len(unique_keywords) >= 15:
                        break
            
            return unique_keywords if unique_keywords else base_keywords
            
        except Exception as e:
            logging.error(f"推奨キーワード取得エラー: {e}")
            return ["日本", "アニメ", "ゲーム", "音楽", "料理"]
    
    def get_preferred_channels(self):
        """好みのチャンネルを取得"""
        try:
            return sorted(self.preferred_channels.items(), 
                         key=lambda x: x[1], reverse=True)[:10]
        except Exception as e:
            logging.error(f"好みチャンネル取得エラー: {e}")
            return []
    
    def should_recommend_video(self, video_info):
        """動画を推奨すべきかを判断"""
        try:
            # 既に視聴した動画は除外
            video_id = video_info.get('videoId')
            for record in self.watch_history:
                if record.get('video_id') == video_id:
                    return False
            
            # 好みのチャンネルの動画は優先
            author = video_info.get('author')
            if author in self.preferred_channels:
                return True
            
            # キーワードマッチングで判断
            video_keywords = video_info.get('keywords', [])
            video_title = video_info.get('title', '').lower()
            
            preferred_keywords = list(self.preferred_keywords.keys())
            
            for keyword in preferred_keywords:
                if keyword.lower() in video_title or keyword in video_keywords:
                    return True
            
            return True  # デフォルトでは推奨
            
        except Exception as e:
            logging.error(f"推奨判断エラー: {e}")
            return True

# グローバルインスタンス
user_prefs = UserPreferences()