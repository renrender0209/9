const scdl = require('soundcloud-downloader').default;

class SoundCloudService {
    constructor() {
        this.clientId = process.env.SOUNDCLOUD_CLIENT_ID;
        this.initialized = false;
        this.baseUrl = 'https://api.soundcloud.com';
    }

    async initialize() {
        if (this.initialized) return true;
        
        try {
            if (!this.clientId) {
                throw new Error('SoundCloud Client ID is required');
            }
            this.initialized = true;
            console.log('SoundCloud service initialized with Client ID');
            return true;
        } catch (error) {
            console.error('SoundCloud service initialization failed:', error);
            return false;
        }
    }

    async searchTracks(query, limit = 20) {
        try {
            await this.initialize();
            
            // SoundCloud公式APIを使用して検索
            const response = await fetch(`${this.baseUrl}/tracks?q=${encodeURIComponent(query)}&client_id=${this.clientId}&limit=${limit}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data || !Array.isArray(data)) {
                return { tracks: [], total: 0 };
            }

            const tracks = data.map(track => ({
                id: track.id,
                title: track.title,
                artist: track.user ? track.user.username : 'Unknown Artist',
                duration: track.duration ? Math.floor(track.duration / 1000) : 0,
                artwork_url: track.artwork_url || (track.user ? track.user.avatar_url : null),
                permalink_url: track.permalink_url,
                stream_url: track.stream_url,
                playback_count: track.playback_count || 0,
                likes_count: track.favoritings_count || 0,
                genre: track.genre || '',
                tag_list: track.tag_list || '',
                created_at: track.created_at,
                description: track.description || ''
            }));

            return {
                tracks: tracks,
                total: tracks.length,
                query: query
            };
        } catch (error) {
            console.error('SoundCloud search error:', error);
            return { tracks: [], total: 0, error: error.message };
        }
    }

    async getTrackInfo(trackId) {
        try {
            await this.initialize();
            
            const response = await fetch(`${this.baseUrl}/tracks/${trackId}?client_id=${this.clientId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const trackInfo = await response.json();
            
            if (!trackInfo) {
                throw new Error('Track not found');
            }

            return {
                id: trackInfo.id,
                title: trackInfo.title,
                artist: trackInfo.user ? trackInfo.user.username : 'Unknown Artist',
                duration: trackInfo.duration ? Math.floor(trackInfo.duration / 1000) : 0,
                artwork_url: trackInfo.artwork_url || (trackInfo.user ? trackInfo.user.avatar_url : null),
                permalink_url: trackInfo.permalink_url,
                stream_url: trackInfo.stream_url,
                playback_count: trackInfo.playback_count || 0,
                likes_count: trackInfo.favoritings_count || 0,
                genre: trackInfo.genre || '',
                tag_list: trackInfo.tag_list || '',
                description: trackInfo.description || '',
                created_at: trackInfo.created_at
            };
        } catch (error) {
            console.error('SoundCloud track info error:', error);
            throw error;
        }
    }

    async getTrendingTracks(genre = '', limit = 20) {
        try {
            await this.initialize();
            
            // トレンド楽曲を取得するためのクエリ
            let query = 'electronic music'; // デフォルトでエレクトロニック音楽
            if (genre) {
                query = `${genre} music`;
            }
            
            const response = await fetch(`${this.baseUrl}/tracks?q=${encodeURIComponent(query)}&client_id=${this.clientId}&limit=${limit}&order=hotness`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (!data || !Array.isArray(data)) {
                return { tracks: [], total: 0 };
            }

            // 再生回数でソート
            const tracks = data
                .map(track => ({
                    id: track.id,
                    title: track.title,
                    artist: track.user ? track.user.username : 'Unknown Artist',
                    duration: track.duration ? Math.floor(track.duration / 1000) : 0,
                    artwork_url: track.artwork_url || (track.user ? track.user.avatar_url : null),
                    permalink_url: track.permalink_url,
                    stream_url: track.stream_url,
                    playback_count: track.playback_count || 0,
                    likes_count: track.favoritings_count || 0,
                    genre: track.genre || '',
                    tag_list: track.tag_list || ''
                }))
                .sort((a, b) => b.playback_count - a.playback_count);

            return {
                tracks: tracks,
                total: tracks.length,
                genre: genre
            };
        } catch (error) {
            console.error('SoundCloud trending error:', error);
            return { tracks: [], total: 0, error: error.message };
        }
    }

    getEmbedUrl(trackId) {
        return `https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/${trackId}&color=%23ff5500&auto_play=true&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=true`;
    }
}

// Express.jsサーバーとして動作
const express = require('express');
const app = express();
const port = 3001;

const soundcloudService = new SoundCloudService();

app.use(express.json());

// CORS対応
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
    
    if (req.method === 'OPTIONS') {
        res.sendStatus(200);
    } else {
        next();
    }
});

// API エンドポイント
app.get('/api/soundcloud/search', async (req, res) => {
    try {
        const { q, limit = 20 } = req.query;
        if (!q) {
            return res.status(400).json({ error: 'Query parameter is required' });
        }
        
        const results = await soundcloudService.searchTracks(q, parseInt(limit));
        res.json(results);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/soundcloud/track/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const trackInfo = await soundcloudService.getTrackInfo(id);
        res.json(trackInfo);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/soundcloud/trending', async (req, res) => {
    try {
        const { genre = '', limit = 20 } = req.query;
        const results = await soundcloudService.getTrendingTracks(genre, parseInt(limit));
        res.json(results);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/soundcloud/embed/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const embedUrl = soundcloudService.getEmbedUrl(id);
        res.json({ embedUrl });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// サーバー起動
if (require.main === module) {
    app.listen(port, '0.0.0.0', () => {
        console.log(`SoundCloud service listening at http://0.0.0.0:${port}`);
    });
}

module.exports = { SoundCloudService, app };