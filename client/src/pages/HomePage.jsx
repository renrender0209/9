import { useQuery } from '@tanstack/react-query';
import VideoCard from '@components/VideoCard';
import { Loader2 } from 'lucide-react';

function HomePage() {
  const { data: trendingVideos, isLoading, error } = useQuery({
    queryKey: ['/api/trending'],
    queryFn: async () => {
      const response = await fetch('/api/trending');
      if (!response.ok) {
        throw new Error('Failed to fetch trending videos');
      }
      return response.json();
    },
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-white" />
          <span className="ml-2 text-white">トレンド動画を読み込み中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center text-red-400">
          <p>トレンド動画の読み込みに失敗しました</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-2 text-blue-400 hover:text-blue-300"
          >
            再試行
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">日本のトレンド</h1>
        <p className="text-gray-400">今日本で人気の動画をチェックしよう</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {trendingVideos?.map((video) => (
          <VideoCard key={video.videoId} video={video} />
        ))}
      </div>

      {trendingVideos?.length === 0 && (
        <div className="text-center text-gray-400 mt-8">
          <p>トレンド動画が見つかりません</p>
        </div>
      )}
    </div>
  );
}

export default HomePage;