# れんれんtube - 日本語動画ストリーミングアプリケーション

## プロジェクト概要
YouTubeの動画を視聴するための「れんれんtube」Webアプリケーション。siawaseok.duckdns.org APIを使用した高画質ストリーミング機能と、YouTube Education埋め込み機能を提供。

## 主要機能
- 日本のトレンド動画表示
- 動画検索機能
- 高画質サムネイル表示（maxresdefault.jpg）
- siawaseok.duckdns.org APIからのストリームURL取得
- YouTube Education埋め込み（type2エンドポイント）
- YouTube-nocookie.com埋め込み
- 視聴履歴とお気に入り機能

## 技術スタック
- Backend: Python Flask
- API統合: siawaseok.duckdns.org、Invidious、yt-dlp
- Frontend: HTML5, JavaScript, Bootstrap

## API設定
### siawaseok.duckdns.org API
- 通常ストリーム: `https://siawaseok.duckdns.org/api/stream/{video_id}/`
- Type2ストリーム: `https://siawaseok.duckdns.org/api/stream/{video_id}/type2`
- トレンド動画: `https://siawaseok.duckdns.org/api/trend`
- 検索機能: `https://siawaseok.duckdns.org/api/search?q={query}`
- チャンネル情報: `https://siawaseok.duckdns.org/api/channel/{channel_id}`

## 最近の変更
- 2025-08-13: siawaseok.duckdns.org API完全移行
- トレンド機能をsiawaseok.duckdns.org/api/trendに変更
- watch関数をsiawaseok API専用に修正
- stream取得をsiawaseok APIのみに変更（720p, muxed360p, audio対応）
- YouTube Education埋め込み機能完成
  - 通常の埋め込み再生を削除
  - YouTube Education埋め込みのみに整理
  - siawaseok通常APIエンドポイント（/api/stream/{video_id}/）から取得したURLをiframeで直接表示
  - 埋め込み表示テキストを「youtubeeducationで再生中」に変更
  - 動画説明欄：siawaseok APIから直接取得（スピード向上）
  - チャンネル情報：siawaseok.duckdns.org/api/channel/{channel_id}から取得
  - 検索機能：siawaseok.duckdns.org/api/search?q={query}に完全移行
  - コンソールログとUI上でURLの確認が可能
  - siawaseok type2 APIから直接ストリーム取得
  - HTML5ビデオプレーヤーで720p/480p/360p対応
  - 分離音声・動画の同期再生機能
- 高画質サムネイル実装
- 詳細ログ機能追加

## ユーザー設定
- 言語: 日本語
- 画質: 高画質優先（1080p）
- **処理優先順位: 外部API優先 → 直接生成フォールバック** (ユーザーフィードバック反映)
- API優先順位: siawaseok.duckdns.org > Invidious > yt-dlp

## 最新の変更 (2025-09-05)
**マルチエンドポイント・フォールバック機能統合**
- 追加APIエンドポイント統合: siawaseok.duckdns.org, 3.net219117116.t-com.ne.jp, 219.117.116.3
- マルチエンドポイント並列処理でスピード・信頼性向上
- **自前ストリームURL生成フォールバック機能**:
  - 外部API失敗時に yt-dlp + ytdl-core で自動フォールバック
  - ハイブリッド方式: 外部API優先 → 自前生成でカバー
  - キャッシュ機能付きで高速化（10分間キャッシュ）
  - フォールバックON/OFF切り替え可能
- **🆕 高速直接生成優先モード実装**:
  - **処理優先順位**: 高速直接生成 → 外部API (従来は逆順)
  - **パフォーマンス**: ytdl-core直接生成(2.4秒) < 外部API(3.7秒)
  - **設定切り替え可能**: 直接生成優先 ⇄ 外部API優先
  - 新API: /api/processing-mode-toggle - 処理優先順位の切り替え
- 直接YouTube Education URL生成（API呼び出し不要）
- @distube/ytpl プレイリスト機能統合
- @distube/ytdl-core 高度動画解析機能統合
- 新API追加:
  - /api/playlist - プレイリスト情報取得
  - /api/advanced-video/<video_id> - 高度動画情報
  - /api/batch-playlists - 複数プレイリスト一括処理
  - /api/channel-playlists - チャンネルプレイリスト一覧
  - /api/stream-fallback/<video_id> - フォールバック機能付きストリーム取得
  - /api/fallback-status - フォールバック機能の状態確認
  - /api/fallback-toggle - フォールバック機能のON/OFF切り替え
  - **🆕 /api/processing-mode-toggle - 処理優先順位切り替え**

## 最新の変更 (2025-09-03)
- サイト名を「siawaseok 動画ストリーミング」から「れんれんtube」に変更
- カスタムロゴ・アイコン・アイキャッチ画像を設定
- 検索結果でチャンネル情報も表示する機能を有効化（Invidious API search_all使用）
- ライブ動画の時間表示に赤い「ライブ」バッジを追加（lengthSeconds=0の場合）
- トレンド動画表示件数を50件から100件に増加
- ホームボタンのロゴ表示は「YouTube」のまま維持