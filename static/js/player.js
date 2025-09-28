// 動画プレーヤー関連の機能
class VideoPlayer {
    constructor() {
        this.player = null;
        this.currentQuality = 'auto';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupMobileSupport();
    }

    setupMobileSupport() {
        const video = document.getElementById('videoPlayer');
        if (video) {
            // Safari/iOS対応を強化
            video.setAttribute('playsinline', '');
            video.setAttribute('webkit-playsinline', '');
            video.setAttribute('x-webkit-airplay', 'allow');
            
            // Safari特有の問題に対応
            if (this.isSafari()) {
                video.setAttribute('controls', 'controls');
                video.setAttribute('preload', 'none');
                
                // Safariでのビデオ読み込み問題に対応
                video.addEventListener('loadstart', () => {
                    console.log('Safari: Video loading started');
                });
                
                video.addEventListener('canplay', () => {
                    console.log('Safari: Video can start playing');
                });
                
                // Safariでのエラー時のフォールバック
                video.addEventListener('error', (e) => {
                    console.error('Safari video error:', e);
                    this.handleSafariVideoError(e);
                });
            }
            
            // タッチデバイスでのコントロール表示
            if ('ontouchstart' in window) {
                video.setAttribute('controls', 'controls');
                
                // iOSでの自動再生制限に対応
                video.addEventListener('loadedmetadata', () => {
                    console.log('Video metadata loaded, ready for iOS playback');
                });
                
                // エラーハンドリング
                video.addEventListener('error', (e) => {
                    console.error('Video error:', e);
                    this.handleVideoError(e);
                });
            }
        }
    }

    setupEventListeners() {
        // 品質変更（多品質・音声分離対応）
        const qualitySelect = document.getElementById('qualitySelect');
        if (qualitySelect) {
            qualitySelect.addEventListener('change', (e) => {
                const selectedOption = e.target.options[e.target.selectedIndex];
                const quality = selectedOption.getAttribute('data-quality');
                const isMultiQuality = selectedOption.getAttribute('data-multi-quality') === 'true';
                
                if (isMultiQuality) {
                    // 🚀 新しい多品質形式での処理
                    const videoUrl = selectedOption.getAttribute('data-video-url');
                    const audioUrl = selectedOption.getAttribute('data-audio-url');
                    const combinedUrl = selectedOption.getAttribute('data-combined-url');
                    const hasAudio = selectedOption.getAttribute('data-has-audio') === 'true';
                    
                    console.log('Multi-Quality change:', {quality, videoUrl, audioUrl, combinedUrl, hasAudio});
                    
                    if (hasAudio && combinedUrl) {
                        // 360p: 音声付き結合ストリーム
                        this.changeQuality(combinedUrl, null, true);
                    } else if (videoUrl && audioUrl) {
                        // 480p以上: 映像・音声分離再生
                        this.changeQuality(videoUrl, audioUrl, false);
                    } else {
                        // フォールバック
                        this.changeQuality(selectedOption.value, null, hasAudio);
                    }
                } else {
                    // 従来の形式での処理（後方互換性）
                    const videoUrl = selectedOption.value;
                    const audioUrl = selectedOption.getAttribute('data-audio-url');
                    const hasAudio = selectedOption.getAttribute('data-has-audio') === 'true';
                    
                    console.log('Legacy Quality change:', {quality, videoUrl, audioUrl, hasAudio});
                    
                    // 音声分離が必要かどうかを判断
                    const needsSeparateAudio = audioUrl && audioUrl.length > 0 && !hasAudio;
                    
                    if (needsSeparateAudio) {
                        // 分離音声を使用
                        this.changeQuality(videoUrl, audioUrl, false);
                    } else {
                        // 統合音声または音声なし
                        this.changeQuality(videoUrl, null, hasAudio);
                    }
                }
            });
        }

        // フルスクリーンボタン
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                this.toggleFullscreen();
            });
        }

        // 再生速度変更
        const speedSelect = document.getElementById('speedSelect');
        if (speedSelect) {
            speedSelect.addEventListener('change', (e) => {
                this.changePlaybackRate(parseFloat(e.target.value));
            });
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            const video = document.querySelector('video');
            if (!video) return;

            // 入力要素にフォーカスがある場合はスキップ
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch (e.key) {
                case ' ':
                case 'k':
                    e.preventDefault();
                    this.togglePlayPause();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.seek(-10);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.seek(10);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.changeVolume(0.1);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.changeVolume(-0.1);
                    break;
                case 'f':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
                case 'm':
                    e.preventDefault();
                    this.toggleMute();
                    break;
                case '0':
                case '1':
                case '2':
                case '3':
                case '4':
                case '5':
                case '6':
                case '7':
                case '8':
                case '9':
                    e.preventDefault();
                    const percent = parseInt(e.key) * 10;
                    this.seekToPercent(percent);
                    break;
            }
        });
    }

    togglePlayPause() {
        const video = document.querySelector('video');
        const audio = document.getElementById('audioPlayer');
        
        if (video) {
            if (video.paused) {
                console.log('📺 動画再生開始...');
                video.play().then(() => {
                    console.log('✅ 動画再生成功');
                    // 分離音声がある場合は同時に再生
                    if (audio && audio.src && video.muted) {
                        console.log('🎵 分離音声再生開始...');
                        audio.play().then(() => {
                            console.log('✅ 分離音声再生成功');
                        }).catch(e => {
                            console.error('❌ 分離音声再生失敗:', e);
                            // 再試行
                            setTimeout(() => {
                                audio.play().then(() => {
                                    console.log('✅ 分離音声再生再試行成功');
                                }).catch(e2 => {
                                    console.error('❌ 分離音声再生再試行失敗:', e2);
                                });
                            }, 200);
                        });
                    }
                }).catch(e => {
                    console.error('❌ 動画再生失敗:', e);
                });
            } else {
                console.log('⏸️ 動画一時停止...');
                video.pause();
                // 分離音声がある場合は同時に停止
                if (audio && !audio.paused) {
                    audio.pause();
                    console.log('⏸️ 分離音声一時停止');
                }
            }
        }
    }

    seek(seconds) {
        const video = document.querySelector('video');
        const audio = document.getElementById('audioPlayer');
        
        if (video) {
            const newTime = Math.max(0, Math.min(video.duration, video.currentTime + seconds));
            video.currentTime = newTime;
            
            // 分離音声がある場合は同期
            if (audio && audio.src && video.muted) {
                audio.currentTime = newTime;
            }
        }
    }

    seekToPercent(percent) {
        const video = document.querySelector('video');
        const audio = document.getElementById('audioPlayer');
        
        if (video && video.duration) {
            const newTime = (video.duration * percent) / 100;
            video.currentTime = newTime;
            
            // 分離音声がある場合は同期
            if (audio && audio.src && video.muted) {
                audio.currentTime = newTime;
            }
        }
    }

    changeVolume(delta) {
        const video = document.querySelector('video');
        const audio = document.getElementById('audioPlayer');
        
        if (video) {
            const newVolume = Math.max(0, Math.min(1, video.volume + delta));
            video.volume = newVolume;
            
            // 分離音声がある場合は音量を同期
            if (audio && audio.src && video.muted) {
                audio.volume = newVolume;
            }
        }
    }

    toggleMute() {
        const video = document.querySelector('video');
        const audio = document.getElementById('audioPlayer');
        
        if (video) {
            // 分離音声使用時は音声要素のミュートを切り替え
            if (audio && audio.src && video.muted) {
                audio.muted = !audio.muted;
            } else {
                video.muted = !video.muted;
            }
        }
    }

    toggleFullscreen() {
        const video = document.querySelector('video');
        if (video) {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                video.requestFullscreen();
            }
        }
    }

    changeQuality(url, audioUrl = null, hasAudio = true) {
        const video = document.querySelector('video');
        let audio = document.getElementById('audioPlayer');
        
        // 音声プレーヤーが存在しない場合は作成
        if (!audio) {
            audio = document.createElement('audio');
            audio.id = 'audioPlayer';
            audio.preload = 'metadata';
            audio.style.display = 'none';
            document.body.appendChild(audio);
        }
        
        if (video && url) {
            const currentTime = video.currentTime;
            const wasPlaying = !video.paused;
            
            // ローディング状態を表示
            showLoadingState();
            
            // 既存の音声を停止
            if (audio) {
                audio.pause();
                audio.src = '';
            }
            
            // 音声設定の強制適用
            if (!hasAudio && audioUrl) {
                // 分離音声使用時：動画はミュート、音声要素で再生
                video.muted = true;
                console.log('🎵 分離音声モード：動画をミュートし、音声要素を使用します');
            } else {
                // 組み合わせストリーム（動画+音声）の場合
                video.muted = false;
                video.volume = 0.7; // 初期音量を70%に設定
                console.log('🔊 音声を有効化しました - ボリューム:', video.volume);
            }
            
            // iOS向けの処理
            if (this.isiOS()) {
                // iOSではsourceを変更する方法を使用
                const sources = video.querySelectorAll('source');
                sources.forEach(source => source.remove());
                
                const newSource = document.createElement('source');
                newSource.src = url;
                newSource.type = 'video/mp4';
                video.appendChild(newSource);
                
                video.load();
            } else {
                // プリロード設定を最適化
                video.preload = 'metadata';
                video.src = url;
            }
            
            // 音声が分離されている場合の処理
            if (!hasAudio && audioUrl && audio) {
                console.log('🎵 分離音声設定開始:', audioUrl);
                audio.preload = 'metadata';
                audio.src = audioUrl;
                audio.volume = 0.7; // 音声要素の音量設定
                audio.muted = false; // 音声要素のミュートを確実に解除
                
                // 動画と音声の同期
                this.syncVideoAudio(video, audio);
                console.log('🎵 分離音声設定完了 - 音量:', audio.volume);
            }
            
            // より迅速な読み込みのためのイベント処理
            const handleLoadSuccess = () => {
                video.currentTime = currentTime;
                if (audio && audioUrl && !hasAudio) {
                    audio.currentTime = currentTime;
                    console.log('🎵 分離音声の時間を同期:', currentTime);
                }
                hideLoadingState();
                if (wasPlaying) {
                    const playPromise = video.play();
                    if (playPromise) {
                        playPromise.then(() => {
                            console.log('📺 動画再生開始成功');
                            if (audio && audioUrl && !hasAudio) {
                                console.log('🎵 分離音声再生開始...');
                                // より確実な音声再生のために少し遅延
                                setTimeout(() => {
                                    audio.play().then(() => {
                                        console.log('✅ 分離音声再生成功');
                                    }).catch(e => {
                                        console.error('❌ 音声再生失敗:', e);
                                        // 音声再生に失敗した場合の再試行
                                        setTimeout(() => {
                                            audio.play().catch(e2 => {
                                                console.error('❌ 音声再生再試行も失敗:', e2);
                                            });
                                        }, 500);
                                    });
                                }, 100);
                            }
                        }).catch(e => {
                            console.log('Auto-play prevented:', e);
                            hideLoadingState();
                        });
                    }
                }
                cleanup();
            };
            
            const handleError = () => {
                hideLoadingState();
                showToast('動画の読み込みに失敗しました', 'danger');
                cleanup();
            };
            
            const cleanup = () => {
                video.removeEventListener('loadedmetadata', handleLoadSuccess);
                video.removeEventListener('canplay', handleLoadSuccess);
                video.removeEventListener('error', handleError);
                clearTimeout(timeoutId);
            };
            
            // 複数のイベントで読み込み完了を検知
            video.addEventListener('loadedmetadata', handleLoadSuccess, { once: true });
            video.addEventListener('canplay', handleLoadSuccess, { once: true });
            video.addEventListener('error', handleError, { once: true });
            
            // タイムアウト処理（5秒に短縮）
            const timeoutId = setTimeout(() => {
                if (video.readyState < 2) {
                    hideLoadingState();
                    showToast('動画の読み込みに時間がかかっています', 'warning');
                    cleanup();
                }
            }, 5000);
            
            video.load();
            if (audio && audioUrl && !hasAudio) {
                audio.load();
            }
        }
    }

    syncVideoAudio(video, audio) {
        // 既存のイベントリスナーを削除
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }
        
        // 動画と音声の同期制御
        const syncAudio = () => {
            const timeDiff = Math.abs(video.currentTime - audio.currentTime);
            if (timeDiff > 0.2) { // 0.2秒以上のずれがある場合
                audio.currentTime = video.currentTime;
            }
        };
        
        // 再生/一時停止の同期
        const playHandler = () => {
            if (audio.paused) {
                audio.play().catch(e => console.log('Audio sync play failed:', e));
            }
        };
        
        const pauseHandler = () => {
            if (!audio.paused) audio.pause();
        };
        
        const seekedHandler = () => {
            audio.currentTime = video.currentTime;
        };
        
        const endedHandler = () => {
            audio.pause();
            audio.currentTime = 0;
            if (this.syncInterval) {
                clearInterval(this.syncInterval);
            }
        };
        
        // イベントリスナーを追加
        video.addEventListener('play', playHandler);
        video.addEventListener('pause', pauseHandler);
        video.addEventListener('seeked', seekedHandler);
        video.addEventListener('ended', endedHandler);
        
        // 定期的な同期チェック
        this.syncInterval = setInterval(() => {
            if (!video.paused && !audio.paused) {
                syncAudio();
            }
        }, 500); // より頻繁にチェック
        
        // 音声の音量を動画と同期
        const volumeHandler = () => {
            if (!video.muted) {
                audio.volume = video.volume;
            }
        };
        
        video.addEventListener('volumechange', volumeHandler);
        
        // 初期音量設定
        audio.volume = video.volume;
    }

    changePlaybackRate(rate) {
        const video = document.querySelector('video');
        const audio = document.getElementById('audioPlayer');
        
        if (video) {
            video.playbackRate = rate;
            
            // 分離音声がある場合は再生速度を同期
            if (audio && audio.src && video.muted) {
                audio.playbackRate = rate;
            }
        }
    }

    isiOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }

    isSafari() {
        return /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    }

    handleSafariVideoError(error) {
        console.error('Safari video error details:', error);
        const video = document.getElementById('videoPlayer');
        
        if (video && video.error) {
            console.error('Safari video error code:', video.error.code);
            
            // Safari特有のエラーに対する対処
            if (video.error.code === 4) { // MEDIA_ELEMENT_ERROR: Format error
                showToast('Safariで動画形式がサポートされていません。別の画質をお試しください。', 'warning');
                
                // 代替フォーマットを試行
                const qualitySelect = document.getElementById('qualitySelect');
                if (qualitySelect && qualitySelect.options.length > 1) {
                    // 次の画質オプションを試行
                    const currentIndex = qualitySelect.selectedIndex;
                    const nextIndex = currentIndex + 1;
                    if (nextIndex < qualitySelect.options.length) {
                        qualitySelect.selectedIndex = nextIndex;
                        qualitySelect.dispatchEvent(new Event('change'));
                        showToast('別の画質で再試行しています...', 'info');
                    }
                }
            } else if (video.error.code === 3) { // MEDIA_ELEMENT_ERROR: Decode error
                showToast('Safariで動画のデコードに失敗しました。ページを更新してください。', 'danger');
            } else {
                showToast('Safariで動画再生エラーが発生しました。', 'danger');
            }
        }
    }

    handleVideoError(error) {
        console.error('Video playback error:', error);
        const video = document.querySelector('video');
        
        if (video && video.error) {
            let errorMessage = '動画の再生中にエラーが発生しました。';
            
            switch (video.error.code) {
                case 1:
                    errorMessage = '動画の読み込みが中断されました。著作権制限により再生できない可能性があります。';
                    break;
                case 2:
                    errorMessage = 'ネットワークエラーが発生しました。著作権により地域制限されている可能性があります。';
                    break;
                case 3:
                    errorMessage = '動画のデコードでエラーが発生しました。著作権保護により再生が制限されています。';
                    break;
                case 4:
                    errorMessage = 'この動画形式はサポートされていません。または著作権により再生が制限されています。';
                    break;
            }
            
            showToast(errorMessage, 'error');
            
            // 著作権制限の場合のガイダンス
            if (video.error.code === 2 || video.error.code === 4) {
                setTimeout(() => {
                    showToast('著作権により制限された楽曲の場合、公式のストリーミングサービスでお楽しみください。', 'info');
                }, 3000);
            }
            
            // iOS向けの追加のエラーハンドリング
            if (this.isiOS()) {
                showToast('iOSでの再生には、動画を直接タップして開始してください。', 'info');
            }
        }
    }

    // 時間フォーマット
    formatTime(seconds) {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hrs > 0) {
            return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }
    }

    // プログレスバーの更新
    updateProgress() {
        const video = document.querySelector('video');
        const progressBar = document.getElementById('progressBar');
        const currentTimeSpan = document.getElementById('currentTime');
        const durationSpan = document.getElementById('duration');

        if (video && progressBar) {
            // 動画の長さが取得できない場合は0:00ではなく適切に処理
            const duration = video.duration || 0;
            const currentTime = video.currentTime || 0;
            
            // NaNやInfinityの場合の処理
            if (isNaN(duration) || !isFinite(duration)) {
                if (durationSpan) {
                    durationSpan.textContent = '--:--';
                }
                if (progressBar) {
                    progressBar.style.width = '0%';
                }
            } else {
                const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
                progressBar.style.width = `${progress}%`;
                
                if (durationSpan) {
                    durationSpan.textContent = this.formatTime(duration);
                }
            }

            if (currentTimeSpan) {
                currentTimeSpan.textContent = this.formatTime(currentTime);
            }
        }
    }
}

// プレーヤーを初期化
document.addEventListener('DOMContentLoaded', () => {
    const videoPlayer = new VideoPlayer();
    
    // プログレスバーの更新
    const video = document.querySelector('video');
    if (video) {
        video.addEventListener('timeupdate', () => {
            videoPlayer.updateProgress();
        });

        video.addEventListener('loadedmetadata', () => {
            console.log('Video metadata loaded, duration:', video.duration);
            videoPlayer.updateProgress();
        });

        // 追加：動画データの読み込み完了時にも更新
        video.addEventListener('loadeddata', () => {
            console.log('Video data loaded, duration:', video.duration);
            videoPlayer.updateProgress();
        });

        // 追加：再生可能状態になった時にも更新
        video.addEventListener('canplay', () => {
            console.log('Video can play, duration:', video.duration);
            videoPlayer.updateProgress();
        });

        // 追加：動画の長さが変更された時の処理
        video.addEventListener('durationchange', () => {
            console.log('Duration changed to:', video.duration);
            videoPlayer.updateProgress();
        });
    }
});

// ユーティリティ関数
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    const container = document.querySelector('.toast-container') || document.body;
    container.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// エラーハンドリング
function handleVideoError(error) {
    console.error('Video error:', error);
    showToast('動画の再生中にエラーが発生しました。', 'danger');
}

// 動画の読み込み状態を表示
function showLoadingState() {
    const playerWrapper = document.querySelector('.video-player-wrapper');
    if (playerWrapper) {
        const loading = document.createElement('div');
        loading.className = 'loading-overlay d-flex align-items-center justify-content-center';
        loading.innerHTML = `
            <div class="text-center text-white">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">読み込み中...</span>
                </div>
                <div class="mt-2">動画を読み込んでいます...</div>
            </div>
        `;
        loading.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 10;
        `;
        playerWrapper.appendChild(loading);
    }
}

function hideLoadingState() {
    const loading = document.querySelector('.loading-overlay');
    if (loading) {
        loading.remove();
    }
}
