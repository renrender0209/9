const express = require('express');
const axios = require('axios');
const ytdl = require('ytdl-core');
const { storage } = require('./storage');
const { watchHistorySchema, userPreferencesSchema } = require('../shared/schema');

const router = express.Router();

// Enhanced parameter validation middleware
const validateVideoId = (req, res, next) => {
  const { videoId } = req.params;
  if (!videoId || typeof videoId !== 'string' || videoId.length < 1) {
    return res.status(400).json({ error: 'Invalid video ID parameter' });
  }
  next();
};

// Invidious instances for fallback
const INVIDIOUS_INSTANCES = [
  'https://invidious.nerdvpn.de',
  'https://invidious.projectsegfau.lt',
  'https://invidious.private.coffee',
  'https://yewtu.be',
  'https://invidious.f5.si',
  'https://inv.nadeko.net',
  'https://siawaseok-wakame-server2.glitch.me'
];

let currentInstanceIndex = 0;

// Helper function to get working Invidious instance
async function getWorkingInstance() {
  for (let i = 0; i < INVIDIOUS_INSTANCES.length; i++) {
    const instance = INVIDIOUS_INSTANCES[currentInstanceIndex];
    try {
      await axios.get(`${instance}/api/v1/stats`, { timeout: 3000 });
      return instance;
    } catch (error) {
      console.log(`Instance ${instance} not working, trying next...`);
      currentInstanceIndex = (currentInstanceIndex + 1) % INVIDIOUS_INSTANCES.length;
    }
  }
  throw new Error('No working Invidious instances available');
}

// Search videos
router.get('/api/search', async (req, res) => {
  try {
    const { q, page = 1, sort = 'relevance', type = 'video' } = req.query;
    
    if (!q) {
      return res.status(400).json({ error: 'Search query is required' });
    }

    const instance = await getWorkingInstance();
    const response = await axios.get(`${instance}/api/v1/search`, {
      params: {
        q,
        page,
        sort,
        type,
        region: 'JP'
      },
      timeout: 10000
    });

    // Filter only video results
    const videos = response.data.filter(item => item.type === 'video');
    res.json(videos);
  } catch (error) {
    console.error('Search error:', error.message);
    res.status(500).json({ error: 'Failed to search videos' });
  }
});

// Get trending videos (Japan)
router.get('/api/trending', async (req, res) => {
  try {
    const { type = 'default' } = req.query;
    
    const instance = await getWorkingInstance();
    const response = await axios.get(`${instance}/api/v1/trending`, {
      params: {
        type,
        region: 'JP'
      },
      timeout: 10000
    });

    res.json(response.data);
  } catch (error) {
    console.error('Trending error:', error.message);
    res.status(500).json({ error: 'Failed to get trending videos' });
  }
});

// Get video details
router.get('/api/video/:videoId([a-zA-Z0-9_-]+)', validateVideoId, async (req, res) => {
  try {
    const { videoId } = req.params;
    
    const instance = await getWorkingInstance();
    const response = await axios.get(`${instance}/api/v1/videos/${videoId}`, {
      params: { region: 'JP' },
      timeout: 10000
    });

    const videoData = response.data;
    
    // Add multiple streaming options
    videoData.streamingOptions = {
      embed: `https://siawaseok.duckdns.org/api/stream/${videoId}`,
      video: `https://siawaseok.duckdns.org/api/stream/${videoId}/type2`,
      audio: `https://siawaseok.duckdns.org/api/stream/${videoId}/type2`, // Audio from same endpoint
      invidious: videoData.formatStreams || [],
      adaptive: videoData.adaptiveFormats || [],
      invidiousAudio: videoData.adaptiveFormats?.filter(format => {
        const isAudio = format.type?.includes('audio') || 
                       format.audioQuality || 
                       (format.type?.includes('mp4') && !format.qualityLabel) ||
                       format.encoding?.includes('opus') ||
                       format.encoding?.includes('aac');
        return isAudio;
      }).sort((a, b) => {
        // Sort by audio quality (higher bitrate first)
        const aBitrate = parseInt(a.bitrate) || 0;
        const bBitrate = parseInt(b.bitrate) || 0;
        return bBitrate - aBitrate;
      }) || []
    };
    
    res.json(videoData);
  } catch (error) {
    console.error('Video details error:', error.message);
    res.status(500).json({ error: 'Failed to get video details' });
  }
});

// Get YouTube Education embed URL
router.get('/api/embed/:videoId([a-zA-Z0-9_-]+)', validateVideoId, async (req, res) => {
  try {
    const { videoId } = req.params;
    
    // Get the embed URL from the custom endpoint
    const embedResponse = await axios.get(`https://siawaseok.duckdns.org/api/stream/${videoId}`, {
      timeout: 10000
    });
    
    // Also get the type2 endpoint for audio/video streams
    let audioVideoData = null;
    try {
      const type2Response = await axios.get(`https://siawaseok.duckdns.org/api/stream/${videoId}/type2`, {
        timeout: 10000
      });
      audioVideoData = type2Response.data;
    } catch (type2Error) {
      console.log('Type2 endpoint not available:', type2Error.message);
    }
    
    // Return the YouTube Education embed URL and stream data
    res.json({
      embedUrl: embedResponse.data.url || embedResponse.data,
      videoId: videoId,
      streamData: audioVideoData
    });
  } catch (error) {
    console.error('Embed URL error:', error.message);
    res.status(500).json({ error: 'Failed to get embed URL' });
  }
});

// Get YouTube streaming URLs using ytdl-core (fallback option)
router.get('/api/ytdl/:videoId([a-zA-Z0-9_-]+)', validateVideoId, async (req, res) => {
  try {
    const { videoId } = req.params;
    const { quality = 'highest' } = req.query;
    
    if (!ytdl.validateID(videoId)) {
      return res.status(400).json({ error: 'Invalid video ID' });
    }

    const info = await ytdl.getInfo(videoId);
    const formats = ytdl.filterFormats(info.formats, 'videoandaudio');
    
    if (formats.length === 0) {
      return res.status(404).json({ error: 'No suitable formats found' });
    }

    // Get the best quality format
    const format = quality === 'highest' ? formats[0] : formats[formats.length - 1];
    
    res.json({
      title: info.videoDetails.title,
      description: info.videoDetails.description,
      length: info.videoDetails.lengthSeconds,
      viewCount: info.videoDetails.viewCount,
      author: info.videoDetails.author.name,
      streamUrl: format.url,
      quality: format.qualityLabel,
      formats: formats.map(f => ({
        quality: f.qualityLabel,
        url: f.url,
        hasAudio: f.hasAudio,
        hasVideo: f.hasVideo,
        container: f.container,
        bitrate: f.bitrate
      }))
    });
  } catch (error) {
    console.error('YTDL error:', error.message);
    res.status(500).json({ error: 'Failed to get YouTube streaming data' });
  }
});

// Proxy stream endpoint for CORS issues
router.get('/api/stream/:videoId([a-zA-Z0-9_-]+)', validateVideoId, async (req, res) => {
  try {
    const { videoId } = req.params;
    const { quality = 'highest' } = req.query;
    
    // Try custom endpoint first
    try {
      const customUrl = `https://siawaseok.duckdns.org/api/stream/${videoId}/type2`;
      const response = await axios.get(customUrl, { 
        responseType: 'stream',
        timeout: 5000 
      });
      
      // Set appropriate headers
      res.set({
        'Content-Type': response.headers['content-type'] || 'video/mp4',
        'Content-Length': response.headers['content-length'],
        'Accept-Ranges': 'bytes',
        'Access-Control-Allow-Origin': '*'
      });
      
      response.data.pipe(res);
      return;
    } catch (customError) {
      console.log('Custom endpoint failed, trying ytdl-core...');
    }
    
    // Fallback to ytdl-core
    if (!ytdl.validateID(videoId)) {
      return res.status(400).json({ error: 'Invalid video ID' });
    }

    const info = await ytdl.getInfo(videoId);
    const format = ytdl.chooseFormat(info.formats, { quality: quality === 'highest' ? 'highestvideo' : 'lowestvideo' });
    
    if (!format) {
      return res.status(404).json({ error: 'No suitable format found' });
    }

    // Stream the video
    const videoStream = ytdl(videoId, { format: format });
    
    res.set({
      'Content-Type': 'video/mp4',
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*'
    });
    
    videoStream.pipe(res);
    
  } catch (error) {
    console.error('Stream proxy error:', error.message);
    res.status(500).json({ error: 'Failed to stream video' });
  }
});

// Get search suggestions
router.get('/api/suggestions', async (req, res) => {
  try {
    const { q } = req.query;
    
    if (!q) {
      return res.json({ suggestions: [] });
    }

    const instance = await getWorkingInstance();
    const response = await axios.get(`${instance}/api/v1/search/suggestions`, {
      params: { q },
      timeout: 5000
    });

    res.json(response.data);
  } catch (error) {
    console.error('Suggestions error:', error.message);
    res.json({ suggestions: [] });
  }
});

// Watch history endpoints
router.get('/api/history', async (req, res) => {
  try {
    const { userId = 'default' } = req.query;
    const history = await storage.getWatchHistory(userId);
    res.json(history);
  } catch (error) {
    console.error('Get history error:', error.message);
    res.status(500).json({ error: 'Failed to get watch history' });
  }
});

router.post('/api/history', async (req, res) => {
  try {
    const { userId = 'default' } = req.query;
    
    // Validate request body
    const validatedEntry = watchHistorySchema.omit({ id: true, watchedAt: true }).parse(req.body);
    
    const entry = await storage.addToWatchHistory(userId, validatedEntry);
    res.json(entry);
  } catch (error) {
    console.error('Add to history error:', error.message);
    res.status(400).json({ error: 'Invalid watch history entry' });
  }
});

router.delete('/api/history/:entryId([a-zA-Z0-9_-]+)', async (req, res) => {
  try {
    const { entryId } = req.params;
    const { userId = 'default' } = req.query;
    
    await storage.removeFromWatchHistory(userId, entryId);
    res.json({ success: true });
  } catch (error) {
    console.error('Remove from history error:', error.message);
    res.status(500).json({ error: 'Failed to remove from history' });
  }
});

router.delete('/api/history', async (req, res) => {
  try {
    const { userId = 'default' } = req.query;
    await storage.clearWatchHistory(userId);
    res.json({ success: true });
  } catch (error) {
    console.error('Clear history error:', error.message);
    res.status(500).json({ error: 'Failed to clear history' });
  }
});

// User preferences endpoints
router.get('/api/preferences', async (req, res) => {
  try {
    const { userId = 'default' } = req.query;
    const preferences = await storage.getUserPreferences(userId);
    res.json(preferences);
  } catch (error) {
    console.error('Get preferences error:', error.message);
    res.status(500).json({ error: 'Failed to get preferences' });
  }
});

router.put('/api/preferences', async (req, res) => {
  try {
    const { userId = 'default' } = req.query;
    
    // Validate request body
    const validatedPrefs = userPreferencesSchema.omit({ id: true }).partial().parse(req.body);
    
    const preferences = await storage.updateUserPreferences(userId, validatedPrefs);
    res.json(preferences);
  } catch (error) {
    console.error('Update preferences error:', error.message);
    res.status(400).json({ error: 'Invalid preferences data' });
  }
});

module.exports = router;