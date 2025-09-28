const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 3001;

// Dynamic import for node-fetch
let fetch;
(async () => {
    const nodeFetch = await import('node-fetch');
    fetch = nodeFetch.default;
})();

// ミドルウェア
app.use(cors());
app.use(express.json());

// SoundCloud Client ID
const SOUNDCLOUD_CLIENT_ID = process.env.SOUNDCLOUD_CLIENT_ID;

if (!SOUNDCLOUD_CLIENT_ID) {
    console.error('SOUNDCLOUD_CLIENT_ID environment variable is required');
    process.exit(1);
}

console.log('SoundCloud service starting with Client ID:', SOUNDCLOUD_CLIENT_ID.substring(0, 8) + '...');

// SoundCloudサービスクラス
class SoundCloudService {
    constructor() {
        this.clientId = SOUNDCLOUD_CLIENT_ID;
        this.baseUrl = 'https://api.soundcloud.com';
    }

    async searchTracks(query, limit = 20) {
        try {
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
            throw error;
        }
    }

    async getTrackInfo(trackId) {
        try {
            const response = await fetch(`${this.baseUrl}/tracks/${trackId}?client_id=${this.clientId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const track = await response.json();
            
            return {
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
            };
        } catch (error) {
            console.error('SoundCloud track info error:', error);
            throw error;
        }
    }

    async getTrendingTracks(genre = '', limit = 20) {
        try {
            let url = `${this.baseUrl}/tracks?client_id=${this.clientId}&limit=${limit}&order=hotness`;
            if (genre) {
                url += `&genres=${encodeURIComponent(genre)}`;
            }
            
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data || !Array.isArray(data)) {
                return { tracks: [], total: 0 };
            }

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
            throw error;
        }
    }

    getEmbedUrl(trackId) {
        return `https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/${trackId}&color=%23ff5500&auto_play=true&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=true`;
    }
}

const soundcloudService = new SoundCloudService();

// API エンドポイント
app.get('/api/search', async (req, res) => {
    try {
        const { q, limit = 20 } = req.query;
        if (!q) {
            return res.status(400).json({ error: 'Query parameter is required' });
        }
        
        const result = await soundcloudService.searchTracks(q, parseInt(limit));
        res.json(result);
    } catch (error) {
        console.error('Search API error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/track/:trackId', async (req, res) => {
    try {
        const { trackId } = req.params;
        const result = await soundcloudService.getTrackInfo(trackId);
        res.json(result);
    } catch (error) {
        console.error('Track info API error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/trending', async (req, res) => {
    try {
        const { genre = '', limit = 20 } = req.query;
        const result = await soundcloudService.getTrendingTracks(genre, parseInt(limit));
        res.json(result);
    } catch (error) {
        console.error('Trending API error:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/embed/:trackId', (req, res) => {
    try {
        const { trackId } = req.params;
        const embedUrl = soundcloudService.getEmbedUrl(trackId);
        res.json({ embedUrl });
    } catch (error) {
        console.error('Embed API error:', error);
        res.status(500).json({ error: error.message });
    }
});

// ヘルスチェック
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// サーバー起動
app.listen(PORT, '0.0.0.0', () => {
    console.log(`SoundCloud service running on http://0.0.0.0:${PORT}`);
});

// エラーハンドリング
process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});