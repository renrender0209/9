class MusicPlayer {
    constructor() {
        this.audio = document.getElementById('audioPlayer');
        this.playerBar = document.getElementById('musicPlayer');
        this.currentTrack = null;
        this.isPlaying = false;
        this.currentTime = 0;
        this.duration = 0;
        this.volume = 0.7;
        this.isMuted = false;
        this.isShuffled = false;
        this.repeatMode = 'off'; // 'off', 'one', 'all'
        this.playlist = [];
        this.currentIndex = 0;
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupAudioEvents();
    }

    initializeElements() {
        // プレイヤー要素を取得
        this.playPauseBtn = document.getElementById('playPauseBtn');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.shuffleBtn = document.getElementById('shuffleBtn');
        this.repeatBtn = document.getElementById('repeatBtn');
        this.muteBtn = document.getElementById('muteBtn');
        
        this.progressBar = document.getElementById('progressBar');
        this.progress = document.getElementById('progress');
        this.currentTimeSpan = document.getElementById('currentTime');
        this.totalTimeSpan = document.getElementById('totalTime');
        
        this.trackImage = document.getElementById('currentTrackImage');
        this.trackTitle = document.getElementById('currentTrackTitle');
        this.trackArtist = document.getElementById('currentTrackArtist');
        
        // 初期音量設定
        this.audio.volume = this.volume;
    }

    setupEventListeners() {
        // 再生/一時停止
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        
        // 前の曲/次の曲
        this.prevBtn.addEventListener('click', () => this.previousTrack());
        this.nextBtn.addEventListener('click', () => this.nextTrack());
        
        // シャッフル
        this.shuffleBtn.addEventListener('click', () => this.toggleShuffle());
        
        // リピート
        this.repeatBtn.addEventListener('click', () => this.toggleRepeat());
        
        // ミュート
        this.muteBtn.addEventListener('click', () => this.toggleMute());
        
        // プログレスバークリック
        this.progressBar.addEventListener('click', (e) => this.seekTo(e));
        
        // キーボードショートカット
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    setupAudioEvents() {
        this.audio.addEventListener('loadstart', () => {
            console.log('音声読み込み開始');
        });

        this.audio.addEventListener('loadedmetadata', () => {
            this.duration = this.audio.duration;
            this.updateTimeDisplay();
            console.log('音声メタデータ読み込み完了:', this.duration);
        });

        this.audio.addEventListener('canplay', () => {
            console.log('音声再生準備完了');
        });

        this.audio.addEventListener('play', () => {
            this.isPlaying = true;
            this.updatePlayPauseButton();
        });

        this.audio.addEventListener('pause', () => {
            this.isPlaying = false;
            this.updatePlayPauseButton();
        });

        this.audio.addEventListener('timeupdate', () => {
            this.currentTime = this.audio.currentTime;
            this.updateProgress();
            this.updateTimeDisplay();
        });

        this.audio.addEventListener('ended', () => {
            this.handleTrackEnd();
        });

        this.audio.addEventListener('error', (e) => {
            console.error('音声再生エラー:', e);
            this.showError('音楽の再生に失敗しました');
        });
    }

    async loadTrack(track) {
        try {
            console.log('トラック読み込み開始:', track.title);
            
            // プレイヤーバーを表示
            this.playerBar.style.display = 'flex';
            
            // トラック情報を更新
            this.currentTrack = track;
            this.updateTrackInfo();
            
            // 音声ストリームを取得
            const response = await fetch(`/music/api/stream/${track.videoId}`);
            const streamData = await response.json();
            
            if (streamData.success && streamData.audio_url) {
                this.audio.src = streamData.audio_url;
                this.audio.load();
                
                // 自動再生
                try {
                    await this.audio.play();
                    console.log('トラック再生開始:', track.title);
                } catch (playError) {
                    console.log('自動再生がブロックされました:', playError);
                    this.showNotification('再生ボタンをクリックして音楽を開始してください');
                }
            } else {
                throw new Error(streamData.error || '音声ストリームを取得できませんでした');
            }
            
        } catch (error) {
            console.error('トラック読み込みエラー:', error);
            this.showError('音楽の読み込みに失敗しました: ' + error.message);
        }
    }

    togglePlayPause() {
        if (!this.audio.src) return;
        
        if (this.isPlaying) {
            this.audio.pause();
        } else {
            this.audio.play().catch(e => {
                console.error('再生エラー:', e);
                this.showError('音楽の再生に失敗しました');
            });
        }
    }

    previousTrack() {
        if (this.playlist.length === 0) return;
        
        this.currentIndex = this.currentIndex > 0 ? this.currentIndex - 1 : this.playlist.length - 1;
        this.loadTrack(this.playlist[this.currentIndex]);
    }

    nextTrack() {
        if (this.playlist.length === 0) return;
        
        if (this.isShuffled) {
            this.currentIndex = Math.floor(Math.random() * this.playlist.length);
        } else {
            this.currentIndex = this.currentIndex < this.playlist.length - 1 ? this.currentIndex + 1 : 0;
        }
        
        this.loadTrack(this.playlist[this.currentIndex]);
    }

    toggleShuffle() {
        this.isShuffled = !this.isShuffled;
        this.shuffleBtn.style.color = this.isShuffled ? '#1db954' : '#b3b3b3';
        this.showNotification(this.isShuffled ? 'シャッフル: オン' : 'シャッフル: オフ');
    }

    toggleRepeat() {
        const modes = ['off', 'all', 'one'];
        const currentModeIndex = modes.indexOf(this.repeatMode);
        this.repeatMode = modes[(currentModeIndex + 1) % modes.length];
        
        const icon = this.repeatBtn.querySelector('i');
        switch (this.repeatMode) {
            case 'off':
                icon.className = 'fas fa-redo';
                this.repeatBtn.style.color = '#b3b3b3';
                this.showNotification('リピート: オフ');
                break;
            case 'all':
                icon.className = 'fas fa-redo';
                this.repeatBtn.style.color = '#1db954';
                this.showNotification('リピート: 全て');
                break;
            case 'one':
                icon.className = 'fas fa-redo-alt';
                this.repeatBtn.style.color = '#1db954';
                this.showNotification('リピート: 1曲');
                break;
        }
    }

    toggleMute() {
        this.isMuted = !this.isMuted;
        this.audio.muted = this.isMuted;
        
        const icon = this.muteBtn.querySelector('i');
        icon.className = this.isMuted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
    }

    seekTo(event) {
        if (!this.duration) return;
        
        const rect = this.progressBar.getBoundingClientRect();
        const percent = (event.clientX - rect.left) / rect.width;
        const newTime = percent * this.duration;
        
        this.audio.currentTime = newTime;
    }

    updateProgress() {
        if (!this.duration) return;
        
        const percent = (this.currentTime / this.duration) * 100;
        this.progress.style.width = `${percent}%`;
    }

    updateTimeDisplay() {
        this.currentTimeSpan.textContent = this.formatTime(this.currentTime);
        this.totalTimeSpan.textContent = this.formatTime(this.duration);
    }

    updatePlayPauseButton() {
        const icon = this.playPauseBtn.querySelector('i');
        icon.className = this.isPlaying ? 'fas fa-pause' : 'fas fa-play';
    }

    updateTrackInfo() {
        if (!this.currentTrack) return;
        
        this.trackTitle.textContent = this.currentTrack.title;
        this.trackArtist.textContent = this.currentTrack.artist;
        this.trackImage.src = this.currentTrack.thumbnail || 'https://via.placeholder.com/56x56/333/fff?text=Music';
        
        // ページタイトルを更新
        document.title = `${this.currentTrack.title} - ${this.currentTrack.artist} | Music Stream`;
    }

    handleTrackEnd() {
        switch (this.repeatMode) {
            case 'one':
                this.audio.currentTime = 0;
                this.audio.play();
                break;
            case 'all':
            case 'off':
                if (this.playlist.length > 0) {
                    this.nextTrack();
                }
                break;
        }
    }

    handleKeyboard(event) {
        // 入力要素にフォーカスがある場合はスキップ
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }

        switch (event.code) {
            case 'Space':
                event.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                this.audio.currentTime = Math.max(0, this.audio.currentTime - 10);
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.audio.currentTime = Math.min(this.duration, this.audio.currentTime + 10);
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.changeVolume(0.1);
                break;
            case 'ArrowDown':
                event.preventDefault();
                this.changeVolume(-0.1);
                break;
            case 'KeyM':
                event.preventDefault();
                this.toggleMute();
                break;
        }
    }

    changeVolume(delta) {
        this.volume = Math.max(0, Math.min(1, this.volume + delta));
        this.audio.volume = this.volume;
    }

    formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    showNotification(message) {
        // 簡単な通知表示
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1db954;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => notification.style.opacity = '1', 100);
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 2000);
    }

    showError(message) {
        console.error(message);
        this.showNotification(message);
    }
}

// グローバルに音楽プレイヤーを利用可能にする
window.MusicPlayer = MusicPlayer;

// グローバル関数として playTrack を定義
window.playTrack = function(videoId, title, artist, thumbnail) {
    if (window.musicPlayer) {
        window.musicPlayer.loadTrack({
            videoId: videoId,
            title: title,
            artist: artist,
            thumbnail: thumbnail
        });
    } else {
        console.error('Music player not initialized');
    }
};

// 重複した初期化コードを削除