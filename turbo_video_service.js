const ytdl = require('@distube/ytdl-core');
const ytpl = require('@distube/ytpl');
const YouTubeSearchAPI = require('youtube-search-api');
const https = require('https');
const http = require('http');

class TurboVideoService {
    constructor() {
        this.cache = new Map();
        this.maxCacheSize = 1000;
        this.requestQueue = [];
        this.processing = false;
        
        // 複数のAPIエンドポイント（優先順位順）
        this.apiEndpoints = [
            'https://siawaseok.duckdns.org',
            'https://3.net219117116.t-com.ne.jp',
            'https://219.117.116.3'
        ];
        
        this.endpointHealthStatus = new Map();
        this.failedEndpoints = new Map();
        this.endpointTimeout = 8000; // 8秒タイムアウト
    }

    async getVideoStream(videoId, quality = '720p') {
        try {
            // キャッシュチェック
            const cacheKey = `${videoId}_${quality}`;
            if (this.cache.has(cacheKey)) {
                const cached = this.cache.get(cacheKey);
                if (Date.now() - cached.timestamp < 300000) { // 5分間キャッシュ
                    return cached.data;
                }
            }

            // 高速取得開始
            const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
            
            // 並列でフォーマット情報を取得
            const [info, formats] = await Promise.all([
                ytdl.getBasicInfo(videoUrl),
                ytdl.getInfo(videoUrl).then(info => info.formats)
            ]);

            // 720p音声付きフォーマットを優先選択
            const videoFormats = formats.filter(f => f.hasVideo && f.hasAudio);
            const audioOnlyFormats = formats.filter(f => !f.hasVideo && f.hasAudio);
            const videoOnlyFormats = formats.filter(f => f.hasVideo && !f.hasAudio);

            // 720p音声付きを探す
            let bestFormat = videoFormats.find(f => 
                f.qualityLabel === '720p' || 
                (f.height === 720 && f.hasAudio)
            );

            // フォールバック: 最高品質の音声付き動画
            if (!bestFormat) {
                bestFormat = videoFormats
                    .filter(f => f.hasAudio && f.height >= 480)
                    .sort((a, b) => b.height - a.height)[0];
            }

            // 分離音声・動画対応
            let audioFormat = null;
            let videoFormat = null;

            if (!bestFormat && videoOnlyFormats.length > 0) {
                videoFormat = videoOnlyFormats
                    .filter(f => f.height === 720 || f.qualityLabel === '720p')
                    .sort((a, b) => b.height - a.height)[0];
                
                audioFormat = audioOnlyFormats
                    .sort((a, b) => b.audioBitrate - a.audioBitrate)[0];
            }

            const result = {
                success: true,
                videoId: videoId,
                title: info.videoDetails.title,
                duration: parseInt(info.videoDetails.lengthSeconds),
                author: info.videoDetails.author.name,
                thumbnail: info.videoDetails.thumbnails?.[0]?.url,
                formats: {
                    combined: bestFormat ? {
                        url: bestFormat.url,
                        quality: bestFormat.qualityLabel || `${bestFormat.height}p`,
                        hasAudio: true,
                        hasVideo: true,
                        container: bestFormat.container,
                        bitrate: bestFormat.bitrate
                    } : null,
                    video: videoFormat ? {
                        url: videoFormat.url,
                        quality: videoFormat.qualityLabel || `${videoFormat.height}p`,
                        hasAudio: false,
                        hasVideo: true,
                        container: videoFormat.container,
                        bitrate: videoFormat.bitrate
                    } : null,
                    audio: audioFormat ? {
                        url: audioFormat.url,
                        quality: 'audio',
                        hasAudio: true,
                        hasVideo: false,
                        container: audioFormat.container,
                        bitrate: audioFormat.audioBitrate
                    } : null
                },
                allFormats: formats.map(f => ({
                    quality: f.qualityLabel || `${f.height}p`,
                    url: f.url,
                    hasAudio: f.hasAudio,
                    hasVideo: f.hasVideo,
                    container: f.container,
                    bitrate: f.bitrate || f.audioBitrate
                }))
            };

            // キャッシュに保存
            this.cache.set(cacheKey, {
                data: result,
                timestamp: Date.now()
            });

            // キャッシュサイズ制限
            if (this.cache.size > this.maxCacheSize) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }

            return result;

        } catch (error) {
            console.error('Video stream error:', error);
            return {
                success: false,
                error: error.message,
                videoId: videoId
            };
        }
    }

    async batchGetVideos(videoIds, quality = '720p') {
        try {
            // 並列処理で複数動画を高速取得
            const promises = videoIds.map(id => this.getVideoStream(id, quality));
            const results = await Promise.all(promises);
            
            return {
                success: true,
                videos: results.filter(r => r.success),
                errors: results.filter(r => !r.success)
            };

        } catch (error) {
            console.error('Batch video error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    async searchVideos(query, maxResults = 20) {
        try {
            const searchResults = await YouTubeSearchAPI.GetListByKeyword(
                query, 
                false, 
                maxResults,
                [{ type: 'video' }]
            );

            const videos = searchResults.items.map(item => ({
                id: item.id,
                title: item.title,
                author: item.channelTitle,
                duration: this.parseDuration(item.length?.simpleText),
                thumbnail: item.thumbnail?.thumbnails?.[0]?.url,
                views: item.viewCount?.simpleText,
                publishedTime: item.publishedTime
            }));

            return {
                success: true,
                videos: videos
            };

        } catch (error) {
            console.error('Search error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    parseDuration(durationText) {
        if (!durationText) return 0;
        
        const parts = durationText.split(':').reverse();
        let seconds = 0;
        
        for (let i = 0; i < parts.length; i++) {
            seconds += parseInt(parts[i]) * Math.pow(60, i);
        }
        
        return seconds;
    }

    clearCache() {
        this.cache.clear();
    }

    getCacheStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize
        };
    }

    // 複数のAPIエンドポイントを並列で試行して最速レスポンスを取得
    async fastMultiEndpointRequest(path, videoId) {
        const promises = this.apiEndpoints.map(endpoint => 
            this.makeRequest(endpoint, path)
                .then(data => ({ success: true, data, endpoint }))
                .catch(error => ({ success: false, error: error.message, endpoint }))
        );

        try {
            // 最初に成功したレスポンスを使用
            const results = await Promise.allSettled(promises);
            const successfulResult = results.find(result => 
                result.status === 'fulfilled' && result.value.success
            );

            if (successfulResult) {
                console.log(`✅ Fast API response from: ${successfulResult.value.endpoint}`);
                return successfulResult.value.data;
            }

            // すべて失敗した場合
            console.error('❌ All API endpoints failed');
            return null;

        } catch (error) {
            console.error('Multi-endpoint request error:', error);
            return null;
        }
    }

    // HTTPリクエストを実行
    makeRequest(endpoint, path) {
        return new Promise((resolve, reject) => {
            const url = `${endpoint}/${path}`;
            const isHttps = url.startsWith('https:');
            const client = isHttps ? https : http;

            const timeout = setTimeout(() => {
                reject(new Error(`Timeout for ${endpoint}`));
            }, this.endpointTimeout);

            const req = client.get(url, (res) => {
                clearTimeout(timeout);
                
                if (res.statusCode !== 200) {
                    reject(new Error(`HTTP ${res.statusCode} from ${endpoint}`));
                    return;
                }

                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const jsonData = JSON.parse(data);
                        resolve(jsonData);
                    } catch (parseError) {
                        reject(new Error(`JSON parse error from ${endpoint}: ${parseError.message}`));
                    }
                });
            });

            req.on('error', (error) => {
                clearTimeout(timeout);
                reject(error);
            });

            req.setTimeout(this.endpointTimeout, () => {
                req.destroy();
                reject(new Error(`Request timeout for ${endpoint}`));
            });
        });
    }

    // 高速動画情報取得（複数エンドポイント使用）
    async getFastVideoInfo(videoId) {
        const cacheKey = `fast_info_${videoId}`;
        
        // キャッシュチェック
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < 180000) { // 3分間キャッシュ
                console.log(`📦 Cache hit for video info: ${videoId}`);
                return cached.data;
            }
        }

        try {
            // 複数エンドポイントを並列試行
            const apiData = await this.fastMultiEndpointRequest(`api/stream/${videoId}/type2`, videoId);
            
            if (apiData) {
                // レスポンスを正規化
                const videoInfo = {
                    success: true,
                    videoId: videoId,
                    title: apiData.title || `Video ${videoId}`,
                    author: apiData.uploader || apiData.author || 'Unknown',
                    duration: apiData.duration || 0,
                    viewCount: apiData.view_count || apiData.viewCount || 0,
                    description: apiData.description || '',
                    thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
                    directStreamUrls: this.extractStreamUrls(apiData),
                    youtubeEducationUrl: this.generateYouTubeEducationUrl(videoId)
                };

                // キャッシュに保存
                this.cache.set(cacheKey, {
                    data: videoInfo,
                    timestamp: Date.now()
                });

                console.log(`🚀 Fast video info retrieved: ${videoInfo.title}`);
                return videoInfo;
            }

            // フォールバック: ytdl-core使用
            console.log(`📺 Fallback to ytdl-core for: ${videoId}`);
            return await this.getVideoStream(videoId);

        } catch (error) {
            console.error(`❌ Fast video info error for ${videoId}:`, error);
            return { success: false, error: error.message, videoId };
        }
    }

    // ストリームURLを抽出
    extractStreamUrls(apiData) {
        const streamUrls = {};
        
        ['1080p', '720p', '480p', '360p', '240p'].forEach(quality => {
            if (apiData[quality]) {
                if (typeof apiData[quality] === 'string') {
                    streamUrls[quality] = { url: apiData[quality], hasAudio: true };
                } else if (typeof apiData[quality] === 'object') {
                    streamUrls[quality] = {
                        video: apiData[quality].video?.url,
                        audio: apiData[quality].audio?.url,
                        hasAudio: !!apiData[quality].audio
                    };
                }
            }
        });

        return streamUrls;
    }

    // YouTube Education URL生成（提供された形式と同じ）
    generateYouTubeEducationUrl(videoId) {
        try {
            // 固定のembed_config（提供されたものと同じ）
            const embedConfig = JSON.stringify({
                enc: "AXH1ezlDMqRg2sliE-6U84LMtrXE06quNAQW8whxjmPJyEbHIYM8iJqZyL4C1dmz65fkyGT8_CAOBPxZn1TPFdfiT_MxeBVG2kj3MBZvRPd7jtEvqyDT0ozH4dAJtJE286DsFe8aJR6nRjlvfLHzxjka-T7JKf3dXQ==",
                hideTitle: true
            });

            const params = new URLSearchParams({
                autoplay: '1',
                mute: '0',
                controls: '1',
                start: '0',
                origin: 'https://create.kahoot.it',
                playsinline: '1',
                showinfo: '0',
                rel: '0',
                iv_load_policy: '3',
                modestbranding: '1',
                fs: '1',
                embed_config: embedConfig,
                enablejsapi: '1',
                widgetid: '1'
            });

            const url = `https://www.youtubeeducation.com/embed/${videoId}?${params.toString()}`;
            console.log(`✅ 完全なYouTube Education URL生成: ${url.substring(0, 100)}...`);
            return url;

        } catch (error) {
            console.error(`❌ YouTube Education URL生成エラー: ${error.message}`);
            // フォールバック
            return `https://www.youtubeeducation.com/embed/${videoId}?autoplay=1&controls=1&rel=0`;
        }
    }

    // 動的埋め込み設定生成（エラーコード2対策）
    generateDynamicEmbedConfig(videoId) {
        try {
            const crypto = require('crypto');
            
            // 現在時刻とビデオIDを組み合わせてユニークなハッシュを生成
            const currentTime = Math.floor(Date.now() / 1000).toString();
            const videoHash = crypto.createHash('sha256').update(`${videoId}_${currentTime}`).digest('hex');
            
            // より有効性の高いエンコード文字列を生成
            const baseString = `YTE_${videoId}_${currentTime}_${videoHash.substring(0, 32)}`;
            const encodedString = Buffer.from(baseString).toString('base64');
            
            // より確実な埋め込み設定
            const embedConfig = {
                enc: encodedString,
                hideTitle: true,
                autoHideControls: false,
                enableEducationMode: true,
                videoId: videoId,
                timestamp: currentTime
            };
            
            const configJson = JSON.stringify(embedConfig);
            console.log(`✅ 動的embed_config生成完了: ${configJson.length}文字`);
            return configJson;

        } catch (error) {
            console.error(`❌ 動的埋め込み設定生成エラー: ${error.message}`);
            // 最小限の安全な設定
            return JSON.stringify({
                enc: "YTE_default_safe",
                hideTitle: true,
                enableEducationMode: true
            });
        }
    }

    // エンドポイント健康状態チェック
    async checkEndpointHealth() {
        const healthResults = {};
        
        for (const endpoint of this.apiEndpoints) {
            try {
                const startTime = Date.now();
                const testData = await this.makeRequest(endpoint, 'api/trend');
                const responseTime = Date.now() - startTime;
                
                healthResults[endpoint] = {
                    status: 'healthy',
                    responseTime: responseTime,
                    lastCheck: new Date().toISOString()
                };
                
                console.log(`✅ ${endpoint}: ${responseTime}ms`);
                
            } catch (error) {
                healthResults[endpoint] = {
                    status: 'unhealthy',
                    error: error.message,
                    lastCheck: new Date().toISOString()
                };
                
                console.log(`❌ ${endpoint}: ${error.message}`);
            }
        }
        
        return healthResults;
    }

    // プレイリスト機能（@distube/ytpl使用）
    async getPlaylistInfo(playlistUrl) {
        const cacheKey = `playlist_${playlistUrl}`;
        
        // キャッシュチェック
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < 600000) { // 10分間キャッシュ
                console.log(`📦 Playlist cache hit: ${playlistUrl}`);
                return cached.data;
            }
        }

        try {
            console.log(`🎵 プレイリスト情報取得開始: ${playlistUrl}`);
            
            const playlistInfo = await ytpl(playlistUrl, { limit: 100 });
            
            const result = {
                success: true,
                id: playlistInfo.id,
                title: playlistInfo.title,
                description: playlistInfo.description,
                url: playlistInfo.url,
                visibility: playlistInfo.visibility,
                totalItems: playlistInfo.total_items,
                author: {
                    name: playlistInfo.author?.name || 'Unknown',
                    channelID: playlistInfo.author?.channelID || '',
                    url: playlistInfo.author?.url || ''
                },
                thumbnail: playlistInfo.bestThumbnail?.url || '',
                views: playlistInfo.views || 0,
                lastUpdated: playlistInfo.lastUpdated || '',
                items: playlistInfo.items.map(item => ({
                    id: item.id,
                    title: item.title,
                    url: item.url,
                    shortUrl: item.shortUrl,
                    author: {
                        name: item.author?.name || 'Unknown',
                        channelID: item.author?.channelID || '',
                        url: item.author?.url || ''
                    },
                    thumbnail: item.bestThumbnail?.url || '',
                    duration: item.durationSec || 0,
                    durationText: this.formatDuration(item.durationSec),
                    index: item.index
                }))
            };

            // キャッシュに保存
            this.cache.set(cacheKey, {
                data: result,
                timestamp: Date.now()
            });

            console.log(`🎵 プレイリスト取得完了: ${result.title} (${result.totalItems}件)`);
            return result;

        } catch (error) {
            console.error(`❌ プレイリスト取得エラー: ${error.message}`);
            return {
                success: false,
                error: error.message,
                url: playlistUrl
            };
        }
    }

    // 高度な動画情報取得（@distube/ytdl-core使用）
    async getAdvancedVideoInfo(videoId) {
        const cacheKey = `advanced_${videoId}`;
        
        // キャッシュチェック
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < 300000) { // 5分間キャッシュ
                console.log(`📦 Advanced cache hit: ${videoId}`);
                return cached.data;
            }
        }

        try {
            const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
            console.log(`🔍 高度な動画情報取得開始: ${videoId}`);

            // @distube/ytdl-coreの高度な機能を使用
            const info = await ytdl.getInfo(videoUrl, {
                lang: 'ja',
                requestOptions: {
                    headers: {
                        'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8'
                    }
                }
            });

            // フォーマットを詳細に分析
            const formats = info.formats.map(format => ({
                itag: format.itag,
                url: format.url,
                mimeType: format.mimeType,
                quality: format.quality,
                qualityLabel: format.qualityLabel,
                width: format.width,
                height: format.height,
                fps: format.fps,
                hasVideo: format.hasVideo,
                hasAudio: format.hasAudio,
                container: format.container,
                bitrate: format.bitrate,
                audioBitrate: format.audioBitrate,
                audioQuality: format.audioQuality,
                audioSampleRate: format.audioSampleRate,
                approxDurationMs: format.approxDurationMs
            }));

            // 最適フォーマットを選択
            const bestVideoWithAudio = formats.find(f => 
                f.hasVideo && f.hasAudio && f.qualityLabel === '720p'
            ) || formats.find(f => f.hasVideo && f.hasAudio && f.height >= 480);

            const bestVideoOnly = formats.find(f => 
                f.hasVideo && !f.hasAudio && f.qualityLabel === '1080p'
            ) || formats.find(f => f.hasVideo && !f.hasAudio && f.height >= 720);

            const bestAudioOnly = formats.filter(f => 
                !f.hasVideo && f.hasAudio
            ).sort((a, b) => (b.audioBitrate || 0) - (a.audioBitrate || 0))[0];

            const result = {
                success: true,
                videoId: videoId,
                title: info.videoDetails.title,
                description: info.videoDetails.description,
                duration: parseInt(info.videoDetails.lengthSeconds),
                author: {
                    name: info.videoDetails.author.name,
                    channelID: info.videoDetails.author.id,
                    url: info.videoDetails.author.user_url
                },
                views: parseInt(info.videoDetails.viewCount),
                likes: info.videoDetails.likes || 0,
                category: info.videoDetails.category,
                isLive: info.videoDetails.isLiveContent,
                keywords: info.videoDetails.keywords || [],
                thumbnail: info.videoDetails.thumbnails[0]?.url,
                uploadDate: info.videoDetails.uploadDate,
                formats: {
                    all: formats,
                    bestVideoWithAudio: bestVideoWithAudio,
                    bestVideoOnly: bestVideoOnly,
                    bestAudioOnly: bestAudioOnly,
                    availableQualities: [...new Set(formats.filter(f => f.qualityLabel).map(f => f.qualityLabel))]
                },
                related: info.related_videos?.slice(0, 10).map(related => ({
                    id: related.id,
                    title: related.title,
                    author: related.author?.name,
                    length_seconds: related.length_seconds,
                    view_count: related.view_count
                })) || [],
                chapters: info.videoDetails.chapters || [],
                storyboards: info.videoDetails.storyboards || []
            };

            // キャッシュに保存
            this.cache.set(cacheKey, {
                data: result,
                timestamp: Date.now()
            });

            console.log(`🔍 高度な動画情報取得完了: ${result.title}`);
            return result;

        } catch (error) {
            console.error(`❌ 高度な動画情報取得エラー: ${error.message}`);
            return {
                success: false,
                error: error.message,
                videoId: videoId
            };
        }
    }

    // バッチプレイリスト処理
    async batchGetPlaylists(playlistUrls) {
        console.log(`🎵 バッチプレイリスト処理開始: ${playlistUrls.length}件`);
        
        const results = await Promise.allSettled(
            playlistUrls.map(url => this.getPlaylistInfo(url))
        );

        const successfulPlaylists = [];
        const failedPlaylists = [];

        results.forEach((result, index) => {
            if (result.status === 'fulfilled' && result.value.success) {
                successfulPlaylists.push(result.value);
            } else {
                failedPlaylists.push({
                    url: playlistUrls[index],
                    error: result.reason?.message || 'Unknown error'
                });
            }
        });

        return {
            success: true,
            totalRequested: playlistUrls.length,
            successful: successfulPlaylists.length,
            failed: failedPlaylists.length,
            playlists: successfulPlaylists,
            errors: failedPlaylists
        };
    }

    // 持続時間フォーマット関数
    formatDuration(seconds) {
        if (!seconds || seconds === 0) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }

    // チャンネルのプレイリスト一覧取得
    async getChannelPlaylists(channelUrl) {
        try {
            console.log(`📚 チャンネルプレイリスト取得: ${channelUrl}`);
            
            // チャンネルIDまたはURLからプレイリストを取得
            const playlists = await ytpl.getChannelInfo(channelUrl);
            
            return {
                success: true,
                channelName: playlists.name,
                channelId: playlists.id,
                playlists: playlists.items.map(playlist => ({
                    id: playlist.id,
                    title: playlist.title,
                    url: playlist.url,
                    videoCount: playlist.videoCount,
                    thumbnail: playlist.bestThumbnail?.url
                }))
            };

        } catch (error) {
            console.error(`❌ チャンネルプレイリスト取得エラー: ${error.message}`);
            return {
                success: false,
                error: error.message,
                channelUrl: channelUrl
            };
        }
    }
}

// CLI インターフェース
if (require.main === module) {
    const service = new TurboVideoService();
    const [,, command, ...args] = process.argv;

    switch (command) {
        case 'stream':
            service.getVideoStream(args[0], args[1])
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'batch':
            const videoIds = args[0].split(',');
            service.batchGetVideos(videoIds, args[1])
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'search':
            service.searchVideos(args[0], parseInt(args[1]) || 20)
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'fast-info':
            service.getFastVideoInfo(args[0])
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'health-check':
            service.checkEndpointHealth()
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'youtube-education-url':
            const educationUrl = service.generateYouTubeEducationUrl(args[0]);
            console.log(JSON.stringify({ success: true, url: educationUrl }));
            break;

        case 'playlist':
            service.getPlaylistInfo(args[0])
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'advanced-info':
            service.getAdvancedVideoInfo(args[0])
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'batch-playlists':
            const urls = args[0].split(',');
            service.batchGetPlaylists(urls)
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        case 'channel-playlists':
            service.getChannelPlaylists(args[0])
                .then(result => console.log(JSON.stringify(result)))
                .catch(error => {
                    console.error(JSON.stringify({ success: false, error: error.message }));
                    process.exit(1);
                });
            break;

        default:
            console.error('Usage: node turbo_video_service.js [stream|batch|search|fast-info|health-check|youtube-education-url|playlist|advanced-info|batch-playlists|channel-playlists] [args...]');
            process.exit(1);
    }
}

module.exports = TurboVideoService;