import os

# Invidious インスタンスリスト（高速化のため厳選）
INVIDIOUS_INSTANCES = [
    # 最優先：最も安定しているインスタンスのみ使用
    'https://youtube.alt.tyil.nl/',
    'https://invidious.nikkosphere.com/',
    'https://invid-api.poketube.fun/',
    'https://lekker.gay/',
    'https://iv.melmac.space/',
    # フォールバック（最小限）
    'https://yewtu.be/',
    'https://invidious.private.coffee/',
]

# リクエストタイムアウト設定
REQUEST_TIMEOUT = 3  # 大幅に短縮して高速化

# yt-dlp設定
YTDL_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'format': 'best[ext=mp4]/best',
}
