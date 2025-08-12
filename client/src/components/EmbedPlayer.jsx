import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import SyncedPlayer from './SyncedPlayer';

function EmbedPlayer({ videoId, onTimeUpdate, onDurationChange }) {
  const [embedUrl, setEmbedUrl] = useState('');
  const [streamData, setStreamData] = useState(null);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  const { data: embedData, isLoading, error: fetchError, refetch } = useQuery({
    queryKey: ['/api/embed', videoId],
    retry: 3,
    retryDelay: 1000,
  });

  useEffect(() => {
    if (embedData) {
      if (typeof embedData === 'string') {
        setEmbedUrl(embedData);
      } else if (embedData.embedUrl) {
        setEmbedUrl(embedData.embedUrl);
      } else if (embedData.url) {
        setEmbedUrl(embedData.url);
      }
      
      // Set stream data for audio extraction
      if (embedData.streamData) {
        setStreamData(embedData.streamData);
      }
      
      setError(null);
    } else if (fetchError) {
      setError('埋め込みURLの取得に失敗しました');
    }
  }, [embedData, fetchError]);

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    setError(null);
    refetch();
  };

  const handleIframeLoad = () => {
    console.log('Embed player loaded successfully');
  };

  const handleIframeError = () => {
    setError('動画の読み込みに失敗しました');
  };

  if (isLoading) {
    return (
      <div className="w-full aspect-video bg-black rounded-lg flex items-center justify-center">
        <div className="text-center text-white">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p>動画を読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !embedUrl) {
    return (
      <div className="w-full aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
        <div className="text-center text-white">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-400" />
          <p className="mb-4">{error || '動画URLが見つかりません'}</p>
          <button
            onClick={handleRetry}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 mx-auto"
          >
            <RefreshCw size={16} />
            <span>再試行</span>
          </button>
          <p className="text-sm text-gray-400 mt-2">試行回数: {retryCount}</p>
        </div>
      </div>
    );
  }

  // Check if the URL is a YouTube Education embed URL
  const isYouTubeEducationUrl = embedUrl.includes('youtube.com') || embedUrl.includes('youtu.be');
  
  if (isYouTubeEducationUrl) {
    // For YouTube Education URLs, create an iframe
    const iframeSrc = embedUrl.includes('/embed/') ? embedUrl : `https://www.youtube-nocookie.com/embed/${videoId}`;
    
    return (
      <div className="w-full aspect-video bg-black rounded-lg overflow-hidden">
        <iframe
          src={iframeSrc}
          title="YouTube video player"
          className="w-full h-full"
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
          onLoad={handleIframeLoad}
          onError={handleIframeError}
        />
      </div>
    );
  } else {
    // For direct video URLs, try to get Invidious streams first
    return <InvidiousPlayer videoId={videoId} embedUrl={embedUrl} streamData={streamData} />;
  }
}

// Component for handling Invidious streams with audio/video sync
function InvidiousPlayer({ videoId, embedUrl, streamData }) {
  const { data: videoDetails, isLoading } = useQuery({
    queryKey: ['/api/video', videoId],
  });

  if (isLoading) {
    return (
      <div className="w-full aspect-video bg-black rounded-lg flex items-center justify-center">
        <div className="text-center text-white">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
          <p>ストリーム情報を取得中...</p>
        </div>
      </div>
    );
  }

  // Try to get best quality video and audio from different sources
  const getVideoUrl = () => {
    // Priority: Custom endpoint > Invidious video formats > fallback
    if (embedUrl) return embedUrl;
    
    const videoFormats = videoDetails?.streamingOptions?.invidious?.filter(f => 
      f.type?.includes('video') && !f.type?.includes('audio')
    ) || [];
    
    const bestVideo = videoFormats.find(f => f.qualityLabel?.includes('720p')) || 
                     videoFormats.find(f => f.qualityLabel?.includes('480p')) ||
                     videoFormats[0];
    
    return bestVideo?.url || `https://siawaseok.duckdns.org/api/stream/${videoId}/type2`;
  };

  const getAudioUrl = () => {
    // Priority: Invidious audio > Custom audio endpoint
    const audioFormats = videoDetails?.streamingOptions?.invidiousAudio || [];
    
    const bestAudio = audioFormats.find(f => f.audioQuality === 'AUDIO_QUALITY_MEDIUM') ||
                     audioFormats.find(f => f.audioQuality === 'AUDIO_QUALITY_LOW') ||
                     audioFormats[0];
    
    return bestAudio?.url || `https://siawaseok.duckdns.org/api/stream/${videoId}/type2`;
  };

  const videoUrl = getVideoUrl();
  const audioUrl = getAudioUrl();

  // Use synced player for better audio/video synchronization
  return (
    <SyncedPlayer
      videoUrl={videoUrl}
      audioUrl={audioUrl !== videoUrl ? audioUrl : null}
    />
  );
}

export default EmbedPlayer;