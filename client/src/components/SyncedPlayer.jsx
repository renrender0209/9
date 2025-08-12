import { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, RotateCcw } from 'lucide-react';

function SyncedPlayer({ videoUrl, audioUrl, onTimeUpdate, onDurationChange }) {
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const [syncOffset, setSyncOffset] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    const video = videoRef.current;
    const audio = audioRef.current;

    if (video) {
      video.volume = volume;
      video.muted = isMuted;
    }
    if (audio) {
      audio.volume = volume;
      audio.muted = isMuted;
    }
  }, [volume, isMuted]);

  const syncAudioWithVideo = () => {
    const video = videoRef.current;
    const audio = audioRef.current;
    
    if (video && audio) {
      const timeDiff = Math.abs(video.currentTime - audio.currentTime);
      if (timeDiff > 0.2) { // Only sync if difference is more than 200ms
        audio.currentTime = video.currentTime + syncOffset;
      }
    }
  };

  const togglePlayPause = async () => {
    const video = videoRef.current;
    const audio = audioRef.current;
    
    try {
      if (isPlaying) {
        video?.pause();
        audio?.pause();
      } else {
        // Sync before playing
        if (video && audio) {
          audio.currentTime = video.currentTime + syncOffset;
        }
        
        // Start both simultaneously
        const promises = [];
        if (video) promises.push(video.play());
        if (audio) promises.push(audio.play());
        
        await Promise.all(promises);
      }
      setIsPlaying(!isPlaying);
    } catch (err) {
      console.error('Playback error:', err);
      setError('再生に失敗しました');
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
  };

  const handleTimeUpdate = (e) => {
    const newTime = e.target.currentTime;
    setCurrentTime(newTime);
    
    // Sync audio periodically
    syncAudioWithVideo();
    
    if (onTimeUpdate) {
      onTimeUpdate(e);
    }
  };

  const handleLoadedMetadata = (e) => {
    const newDuration = e.target.duration;
    setDuration(newDuration);
    
    if (onDurationChange) {
      onDurationChange(e);
    }
  };

  const handleSeek = (e) => {
    const video = videoRef.current;
    const audio = audioRef.current;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newTime = (clickX / rect.width) * duration;
    
    if (video) video.currentTime = newTime;
    if (audio) audio.currentTime = newTime + syncOffset;
    setCurrentTime(newTime);
  };

  const handleFullscreen = () => {
    const video = videoRef.current;
    if (video) {
      if (video.requestFullscreen) {
        video.requestFullscreen();
      } else if (video.webkitRequestFullscreen) {
        video.webkitRequestFullscreen();
      } else if (video.mozRequestFullScreen) {
        video.mozRequestFullScreen();
      }
    }
  };

  const formatTime = (time) => {
    const hours = Math.floor(time / 3600);
    const minutes = Math.floor((time % 3600) / 60);
    const seconds = Math.floor(time % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const adjustSync = (offset) => {
    setSyncOffset(prev => prev + offset);
    const audio = audioRef.current;
    const video = videoRef.current;
    if (audio && video) {
      audio.currentTime = video.currentTime + syncOffset + offset;
    }
  };

  if (error) {
    return (
      <div className="w-full aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
        <div className="text-center text-white">
          <p className="mb-4">{error}</p>
          <button
            onClick={() => {setError(null); window.location.reload();}}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            再読み込み
          </button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="relative w-full aspect-video bg-black rounded-lg overflow-hidden group"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Main video */}
      <video
        ref={videoRef}
        className="w-full h-full object-contain"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onError={() => setError('動画の読み込みに失敗しました')}
        preload="metadata"
      >
        <source src={videoUrl} type="video/mp4" />
      </video>

      {/* Separate audio track */}
      {audioUrl && audioUrl !== videoUrl && (
        <audio
          ref={audioRef}
          preload="metadata"
          onError={() => console.log('Audio track failed to load')}
        >
          <source src={audioUrl} type="audio/mp4" />
        </audio>
      )}

      {/* Custom controls */}
      <div className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 transition-opacity duration-300 ${showControls ? 'opacity-100' : 'opacity-0'}`}>
        {/* Progress bar */}
        <div className="mb-4">
          <div 
            className="w-full h-2 bg-gray-600 rounded cursor-pointer hover:h-3 transition-all"
            onClick={handleSeek}
          >
            <div 
              className="h-full bg-red-600 rounded transition-all"
              style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button 
              onClick={togglePlayPause} 
              className="text-white hover:text-gray-300 transition-colors"
            >
              {isPlaying ? <Pause size={24} /> : <Play size={24} />}
            </button>
            
            <div className="flex items-center space-x-2">
              <button 
                onClick={toggleMute} 
                className="text-white hover:text-gray-300 transition-colors"
              >
                {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={handleVolumeChange}
                className="w-20 accent-red-600"
              />
            </div>
            
            <span className="text-white text-sm font-mono">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>

            {/* Audio sync controls */}
            {audioUrl && audioUrl !== videoUrl && (
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => adjustSync(-0.1)}
                  className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded text-white"
                  title="音声を0.1秒早める"
                >
                  A-
                </button>
                <span className="text-xs text-gray-300" title="音声同期オフセット">
                  {syncOffset.toFixed(1)}s
                </span>
                <button
                  onClick={() => adjustSync(0.1)}
                  className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded text-white"
                  title="音声を0.1秒遅らせる"
                >
                  A+
                </button>
                <button
                  onClick={() => setSyncOffset(0)}
                  className="text-white hover:text-gray-300 ml-2"
                  title="同期リセット"
                >
                  <RotateCcw size={16} />
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <div className="text-xs text-gray-300 bg-black/50 px-2 py-1 rounded">
              カスタム高画質
            </div>
            
            <button 
              onClick={handleFullscreen}
              className="text-white hover:text-gray-300 transition-colors"
            >
              <Maximize size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Loading indicator */}
      {!videoUrl && (
        <div className="absolute inset-0 flex items-center justify-center bg-black">
          <div className="text-white">動画を読み込み中...</div>
        </div>
      )}
    </div>
  );
}

export default SyncedPlayer;