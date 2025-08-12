import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import VideoCard from '@components/VideoCard';
import EmbedPlayer from '@components/EmbedPlayer';
import { updateMetaTags, resetMetaTags, generateVideoStructuredData } from '@utils/meta';
import { ThumbsUp, ThumbsDown, Share, Download, MoreHorizontal, Link } from 'lucide-react';
import { apiRequest } from '@lib/queryClient';

function VideoPage({ params }) {
  const { videoId } = params;
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const queryClient = useQueryClient();

  const { data: videoData, isLoading, error } = useQuery({
    queryKey: ['/api/video', videoId],
  });

  const addToHistoryMutation = useMutation({
    mutationFn: (data) => apiRequest('/api/history', { method: 'POST', data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/history'] });
    }
  });

  useEffect(() => {
    if (videoData) {
      // Update meta tags for social sharing
      updateMetaTags(videoData);
      generateVideoStructuredData(videoData);
      
      // Add to watch history
      addToHistoryMutation.mutate({
        videoId: videoData.videoId,
        title: videoData.title,
        author: videoData.author,
        thumbnail: videoData.videoThumbnails?.[0]?.url || '',
        progress: 0
      });
    }
    
    // Cleanup when component unmounts
    return () => {
      resetMetaTags();
    };
  }, [videoData]);

  const handleTimeUpdate = (e) => {
    if (e?.target?.currentTime) {
      setCurrentTime(e.target.currentTime);
    }
  };

  const handleDurationChange = (e) => {
    if (e?.target?.duration) {
      setDuration(e.target.duration);
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

  const formatViewCount = (count) => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M回視聴`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K回視聴`;
    }
    return `${count}回視聴`;
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/watch/${videoId}`;
    
    try {
      if (navigator.share) {
        // Use native share API if available
        await navigator.share({
          title: videoData.title,
          text: `${videoData.title} - ${videoData.author}`,
          url: url
        });
      } else {
        // Fallback to clipboard
        await navigator.clipboard.writeText(url);
        // You could add a toast notification here
        alert('リンクがクリップボードにコピーされました！');
      }
    } catch (error) {
      // Manual fallback
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      alert('リンクがクリップボードにコピーされました！');
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-white">動画を読み込み中...</div>
      </div>
    );
  }

  if (error || !videoData) {
    return (
      <div className="p-6 text-center text-red-400">
        <p>動画の読み込みに失敗しました</p>
        <button 
          onClick={() => window.location.reload()} 
          className="mt-2 text-blue-400 hover:text-blue-300"
        >
          再試行
        </button>
      </div>
    );
  }



  return (
    <div className="p-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main video section */}
        <div className="lg:col-span-3">
          {/* Video player */}
          <EmbedPlayer 
            videoId={videoId}
            onTimeUpdate={handleTimeUpdate}
            onDurationChange={handleDurationChange}
          />

          {/* Video info */}
          <div className="mt-4">
            <h1 className="text-xl font-bold text-white mb-2">{videoData.title}</h1>
            
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                    {videoData.author?.charAt(0) || 'U'}
                  </div>
                  <div>
                    <p className="text-white font-medium">{videoData.author}</p>
                    <p className="text-gray-400 text-sm">{videoData.subCountText}</p>
                  </div>
                </div>
                <button className="bg-white text-black px-4 py-2 rounded-full font-medium hover:bg-gray-200">
                  登録
                </button>
              </div>
              
              <div className="flex items-center space-x-2">
                <div className="flex bg-gray-800 rounded-full">
                  <button className="flex items-center space-x-2 px-4 py-2 text-white hover:bg-gray-700 rounded-l-full">
                    <ThumbsUp size={20} />
                    <span>{videoData.likeCount?.toLocaleString()}</span>
                  </button>
                  <button className="flex items-center space-x-2 px-4 py-2 text-white hover:bg-gray-700 rounded-r-full border-l border-gray-600">
                    <ThumbsDown size={20} />
                  </button>
                </div>
                
                <button 
                  onClick={handleShare}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-800 text-white rounded-full hover:bg-gray-700"
                >
                  <Share size={20} />
                  <span>共有</span>
                </button>
                
                <button className="flex items-center space-x-2 px-4 py-2 bg-gray-800 text-white rounded-full hover:bg-gray-700">
                  <Download size={20} />
                  <span>保存</span>
                </button>
                
                <button className="p-2 bg-gray-800 text-white rounded-full hover:bg-gray-700">
                  <MoreHorizontal size={20} />
                </button>
              </div>
            </div>

            {/* Video stats */}
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="flex items-center space-x-4 text-sm text-gray-300 mb-2">
                <span>{formatViewCount(videoData.viewCount)}</span>
                <span>{videoData.publishedText}</span>
              </div>
              
              <div className="text-white text-sm">
                <p className="line-clamp-3">{videoData.description}</p>
                <button className="text-gray-400 hover:text-white mt-2">
                  もっと見る
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Recommended videos sidebar */}
        <div className="lg:col-span-1">
          <h2 className="text-white font-bold mb-4">関連動画</h2>
          <div className="space-y-4">
            {videoData.recommendedVideos?.slice(0, 10).map((video) => (
              <div key={video.videoId} className="flex space-x-2">
                <div className="flex-shrink-0 w-40">
                  <VideoCard video={video} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default VideoPage;