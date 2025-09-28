const ytdl = require('ytdl-core');
const express = require('express');
const app = express();

app.use(express.json());

// CORS設定
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    next();
});

// 動画情報とストリームURLを取得
app.get('/video/:videoId', async (req, res) => {
    try {
        const videoId = req.params.videoId;
        const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
        
        // 動画情報を取得
        const info = await ytdl.getInfo(videoUrl);
        
        // フォーマットを取得して整理
        const formats = ytdl.filterFormats(info.formats, 'videoandaudio');
        const videoOnlyFormats = ytdl.filterFormats(info.formats, 'videoonly');
        const audioOnlyFormats = ytdl.filterFormats(info.formats, 'audioonly');
        
        // 品質別にフォーマットを整理
        const qualityFormats = {};
        
        // 動画+音声の統合フォーマット
        formats.forEach(format => {
            if (format.height) {
                const quality = getQualityLabel(format.height);
                if (!qualityFormats[quality] || 
                    (qualityFormats[quality].bitrate || 0) < (format.bitrate || 0)) {
                    qualityFormats[quality] = {
                        url: format.url,
                        quality: quality,
                        resolution: `${format.width}x${format.height}`,
                        fps: format.fps,
                        container: format.container,
                        hasAudio: true,
                        audioUrl: null,
                        bitrate: format.bitrate,
                        audioBitrate: format.audioBitrate
                    };
                }
            }
        });
        
        // 最高品質の音声を選択
        const bestAudio = audioOnlyFormats.reduce((best, current) => {
            return (!best || (current.audioBitrate || 0) > (best.audioBitrate || 0)) ? current : best;
        }, null);
        
        // 動画のみのフォーマット（高品質）
        videoOnlyFormats.forEach(format => {
            if (format.height) {
                const quality = getQualityLabel(format.height);
                
                // 1080p以上の場合は動画のみと音声を分離して提供
                if (format.height >= 1080 && bestAudio) {
                    if (!qualityFormats[quality] || 
                        (qualityFormats[quality].bitrate || 0) < (format.bitrate || 0)) {
                        qualityFormats[quality] = {
                            url: format.url,
                            quality: quality,
                            resolution: `${format.width}x${format.height}`,
                            fps: format.fps,
                            container: format.container,
                            hasAudio: false,
                            audioUrl: bestAudio.url,
                            bitrate: format.bitrate,
                            audioBitrate: bestAudio.audioBitrate
                        };
                    }
                }
            }
        });
        
        // フォーマット配列に変換
        const formatsList = Object.values(qualityFormats)
            .sort((a, b) => {
                const qualityOrder = { '2160p': 4, '1440p': 3, '1080p': 2, '720p': 1, '480p': 0, '360p': -1, '240p': -2 };
                return (qualityOrder[b.quality] || -3) - (qualityOrder[a.quality] || -3);
            });
        
        const result = {
            title: info.videoDetails.title,
            duration: parseInt(info.videoDetails.lengthSeconds),
            thumbnail: info.videoDetails.thumbnails[info.videoDetails.thumbnails.length - 1]?.url,
            uploader: info.videoDetails.author.name,
            best_url: formatsList[0]?.url,
            formats: formatsList
        };
        
        res.json(result);
        
    } catch (error) {
        console.error('ytdl-core エラー:', error);
        res.status(500).json({ error: error.message });
    }
});

// 音声のみのURLを取得
app.get('/audio/:videoId', async (req, res) => {
    try {
        const videoId = req.params.videoId;
        const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
        
        const info = await ytdl.getInfo(videoUrl);
        const audioFormats = ytdl.filterFormats(info.formats, 'audioonly');
        
        if (audioFormats.length === 0) {
            return res.status(404).json({ error: '音声フォーマットが見つかりません' });
        }
        
        // 最高品質の音声を選択
        const bestAudio = audioFormats.reduce((best, current) => {
            return (!best || (current.audioBitrate || 0) > (best.audioBitrate || 0)) ? current : best;
        }, null);
        
        res.json({
            url: bestAudio.url,
            container: bestAudio.container,
            audioBitrate: bestAudio.audioBitrate
        });
        
    } catch (error) {
        console.error('音声取得エラー:', error);
        res.status(500).json({ error: error.message });
    }
});

// 品質ラベルを決定する関数
function getQualityLabel(height) {
    if (height >= 2160) return '2160p';
    if (height >= 1440) return '1440p';
    if (height >= 1080) return '1080p';
    if (height >= 720) return '720p';
    if (height >= 480) return '480p';
    if (height >= 360) return '360p';
    return '240p';
}

const PORT = process.env.YTDL_PORT || 3001;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`ytdl-core サービスがポート ${PORT} で開始されました`);
});

module.exports = app;