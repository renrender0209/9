const { z } = require("zod");

// Video data from Invidious API
const videoSchema = z.object({
  videoId: z.string(),
  title: z.string(),
  author: z.string(),
  authorId: z.string(),
  authorUrl: z.string(),
  lengthSeconds: z.number(),
  viewCount: z.number(),
  published: z.number(),
  publishedText: z.string(),
  description: z.string(),
  videoThumbnails: z.array(z.object({
    quality: z.string(),
    url: z.string(),
    width: z.number(),
    height: z.number()
  })),
  adaptiveFormats: z.array(z.object({
    url: z.string(),
    itag: z.string(),
    type: z.string(),
    qualityLabel: z.string().optional(),
    resolution: z.string().optional(),
    fps: z.number().optional(),
    audioQuality: z.string().optional(),
    audioSampleRate: z.string().optional(),
    audioChannels: z.string().optional()
  })).optional(),
  formatStreams: z.array(z.object({
    url: z.string(),
    itag: z.string(),
    type: z.string(),
    quality: z.string(),
    qualityLabel: z.string(),
    resolution: z.string(),
    container: z.string()
  })).optional(),
  recommendedVideos: z.array(z.object({
    videoId: z.string(),
    title: z.string(),
    author: z.string(),
    lengthSeconds: z.number(),
    viewCount: z.number(),
    videoThumbnails: z.array(z.object({
      quality: z.string(),
      url: z.string(),
      width: z.number(),
      height: z.number()
    }))
  })).optional()
});

// Search result item
const searchResultSchema = z.object({
  type: z.literal("video"),
  videoId: z.string(),
  title: z.string(),
  author: z.string(),
  authorId: z.string(),
  authorUrl: z.string(),
  lengthSeconds: z.number(),
  viewCount: z.number(),
  published: z.number(),
  publishedText: z.string(),
  description: z.string(),
  videoThumbnails: z.array(z.object({
    quality: z.string(),
    url: z.string(),
    width: z.number(),
    height: z.number()
  }))
});

// Watch history entry
const watchHistorySchema = z.object({
  id: z.string(),
  videoId: z.string(),
  title: z.string(),
  author: z.string(),
  thumbnail: z.string(),
  watchedAt: z.number(),
  progress: z.number().min(0).max(100), // percentage watched
});

// User preferences
const userPreferencesSchema = z.object({
  id: z.string(),
  preferredQuality: z.enum(["auto", "144p", "240p", "360p", "480p", "720p", "1080p"]).default("auto"),
  autoplay: z.boolean().default(false),
  volume: z.number().min(0).max(100).default(50),
  language: z.string().default("ja"),
  region: z.string().default("JP")
});

module.exports = {
  videoSchema,
  searchResultSchema,
  watchHistorySchema,
  userPreferencesSchema
};