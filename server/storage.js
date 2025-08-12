const { v4: uuidv4 } = require('uuid');

class MemStorage {
  constructor() {
    this.watchHistory = new Map();
    this.userPreferences = new Map();
    this.defaultPreferences = {
      id: 'default',
      preferredQuality: 'auto',
      autoplay: false,
      volume: 50,
      language: 'ja',
      region: 'JP'
    };
  }

  // Watch History methods
  async getWatchHistory(userId = 'default') {
    const userHistory = this.watchHistory.get(userId) || [];
    return userHistory.sort((a, b) => b.watchedAt - a.watchedAt);
  }

  async addToWatchHistory(userId = 'default', entry) {
    const id = uuidv4();
    const historyEntry = {
      ...entry,
      id,
      watchedAt: Date.now()
    };

    const userHistory = this.watchHistory.get(userId) || [];
    
    // Remove existing entry for same video if exists
    const filteredHistory = userHistory.filter(item => item.videoId !== entry.videoId);
    
    // Add new entry and limit to 100 items
    const updatedHistory = [historyEntry, ...filteredHistory].slice(0, 100);
    
    this.watchHistory.set(userId, updatedHistory);
    return historyEntry;
  }

  async removeFromWatchHistory(userId = 'default', entryId) {
    const userHistory = this.watchHistory.get(userId) || [];
    const filteredHistory = userHistory.filter(item => item.id !== entryId);
    this.watchHistory.set(userId, filteredHistory);
    return true;
  }

  async clearWatchHistory(userId = 'default') {
    this.watchHistory.set(userId, []);
    return true;
  }

  // User Preferences methods
  async getUserPreferences(userId = 'default') {
    return this.userPreferences.get(userId) || this.defaultPreferences;
  }

  async updateUserPreferences(userId = 'default', preferences) {
    const currentPrefs = await this.getUserPreferences(userId);
    const updatedPrefs = {
      ...currentPrefs,
      ...preferences,
      id: userId
    };
    this.userPreferences.set(userId, updatedPrefs);
    return updatedPrefs;
  }
}

const storage = new MemStorage();

module.exports = { storage };