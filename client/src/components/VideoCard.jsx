import { Link } from 'wouter';
import { formatDistanceToNow } from '@/utils/dateFormat';

function VideoCard({ video }) {
  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViewCount = (count) => {
    if (count >= 1000000) {
      return `${(count / 1000000).toFixed(1)}M回視聴`;
    } else if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K回視聴`;
    }
    return `${count}回視聴`;
  };

  const getPublishedTime = (timestamp) => {
    try {
      const date = new Date(timestamp * 1000);
      return formatDistanceToNow(date);
    } catch {
      return video.publishedText || '';
    }
  };

  const thumbnail = video.videoThumbnails?.find(t => t.quality === 'medium' || t.quality === 'high')?.url || 
                   video.videoThumbnails?.[0]?.url || '';

  return (
    <Link href={`/watch/${video.videoId}`}>
      <div className="cursor-pointer group">
        <div className="relative">
          <img
            src={thumbnail}
            alt={video.title}
            className="w-full aspect-video object-cover rounded-lg bg-gray-800"
            loading="lazy"
          />
          <div className="absolute bottom-2 right-2 bg-black bg-opacity-80 text-white text-xs px-1 py-0.5 rounded">
            {formatDuration(video.lengthSeconds)}
          </div>
        </div>
        
        <div className="mt-3 flex space-x-3">
          <div className="flex-shrink-0">
            <div className="w-9 h-9 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
              {video.author?.charAt(0) || 'U'}
            </div>
          </div>
          
          <div className="min-w-0 flex-1">
            <h3 className="text-white text-sm font-medium line-clamp-2 group-hover:text-gray-300">
              {video.title}
            </h3>
            <p className="text-gray-400 text-xs mt-1 hover:text-gray-300">
              {video.author}
            </p>
            <p className="text-gray-400 text-xs mt-1">
              {formatViewCount(video.viewCount)} • {getPublishedTime(video.published)}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}

export default VideoCard;