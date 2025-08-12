import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'wouter';
import { Trash2, Clock } from 'lucide-react';
import { apiRequest } from '@lib/queryClient';
import { formatDistanceToNow } from '@/utils/dateFormat';

function HistoryPage() {
  const queryClient = useQueryClient();

  const { data: history, isLoading, error } = useQuery({
    queryKey: ['/api/history'],
  });

  const removeFromHistoryMutation = useMutation({
    mutationFn: (entryId) => apiRequest(`/api/history/${entryId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/history'] });
    }
  });

  const clearHistoryMutation = useMutation({
    mutationFn: () => apiRequest('/api/history', { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/history'] });
    }
  });

  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return formatDistanceToNow(date, { addSuffix: true, locale: ja });
    } catch {
      return '';
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-white">履歴を読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-red-400">
        <p>履歴の読み込みに失敗しました</p>
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
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Clock size={24} className="text-white" />
          <h1 className="text-2xl font-bold text-white">視聴履歴</h1>
        </div>
        
        {history && history.length > 0 && (
          <button
            onClick={() => clearHistoryMutation.mutate()}
            className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            disabled={clearHistoryMutation.isPending}
          >
            <Trash2 size={16} />
            <span>すべて削除</span>
          </button>
        )}
      </div>

      {history && history.length === 0 ? (
        <div className="text-center text-gray-400 mt-8">
          <Clock size={48} className="mx-auto mb-4 opacity-50" />
          <p>視聴履歴がありません</p>
          <p className="text-sm mt-2">動画を視聴すると、ここに履歴が表示されます</p>
        </div>
      ) : (
        <div className="space-y-4">
          {history?.map((entry) => (
            <div key={entry.id} className="flex items-start space-x-4 p-4 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
              <Link href={`/watch/${entry.videoId}`} className="flex-shrink-0">
                <img
                  src={entry.thumbnail}
                  alt={entry.title}
                  className="w-48 aspect-video object-cover rounded-lg bg-gray-700"
                />
              </Link>
              
              <div className="flex-1 min-w-0">
                <Link href={`/watch/${entry.videoId}`}>
                  <h3 className="text-white font-medium line-clamp-2 hover:text-gray-300 cursor-pointer">
                    {entry.title}
                  </h3>
                </Link>
                
                <p className="text-gray-400 text-sm mt-1">{entry.author}</p>
                <p className="text-gray-500 text-xs mt-2">
                  視聴日時: {formatTime(entry.watchedAt)}
                </p>
                
                {entry.progress > 0 && (
                  <div className="mt-2">
                    <div className="flex items-center space-x-2 text-xs text-gray-400">
                      <span>進行状況: {Math.round(entry.progress)}%</span>
                    </div>
                    <div className="w-full bg-gray-600 rounded-full h-1 mt-1">
                      <div 
                        className="bg-red-600 h-1 rounded-full" 
                        style={{ width: `${entry.progress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
              
              <button
                onClick={() => removeFromHistoryMutation.mutate(entry.id)}
                className="p-2 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded-lg"
                disabled={removeFromHistoryMutation.isPending}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default HistoryPage;