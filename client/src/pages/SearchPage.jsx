import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import VideoCard from '@components/VideoCard';
import { Loader2, Search } from 'lucide-react';

function SearchPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentQuery, setCurrentQuery] = useState('');

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q') || '';
    setSearchQuery(query);
    setCurrentQuery(query);
  }, []);

  const { data: searchResults, isLoading, error } = useQuery({
    queryKey: ['/api/search', { q: currentQuery }],
    enabled: !!currentQuery,
  });

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setCurrentQuery(searchQuery.trim());
      window.history.pushState({}, '', `?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div className="p-6">
      {/* Search form */}
      <div className="mb-6">
        <form onSubmit={handleSearch} className="flex max-w-2xl">
          <div className="flex w-full">
            <input
              type="text"
              placeholder="動画を検索"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 h-10 px-4 bg-black border border-gray-600 text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none rounded-l-full"
            />
            <button
              type="submit"
              className="h-10 px-6 bg-gray-800 border border-l-0 border-gray-600 hover:bg-gray-700 rounded-r-full flex items-center justify-center"
            >
              <Search size={20} />
            </button>
          </div>
        </form>
      </div>

      {/* Search results */}
      {currentQuery && (
        <div className="mb-4">
          <h1 className="text-xl font-semibold text-white">
            「{currentQuery}」の検索結果
          </h1>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-white" />
          <span className="ml-2 text-white">検索中...</span>
        </div>
      )}

      {error && (
        <div className="text-center text-red-400">
          <p>検索に失敗しました</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-2 text-blue-400 hover:text-blue-300"
          >
            再試行
          </button>
        </div>
      )}

      {searchResults && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {searchResults.map((video) => (
            <VideoCard key={video.videoId} video={video} />
          ))}
        </div>
      )}

      {searchResults && searchResults.length === 0 && (
        <div className="text-center text-gray-400 mt-8">
          <p>「{currentQuery}」に一致する動画が見つかりません</p>
          <p className="text-sm mt-2">別のキーワードで検索してみてください</p>
        </div>
      )}

      {!currentQuery && (
        <div className="text-center text-gray-400 mt-8">
          <Search size={48} className="mx-auto mb-4 opacity-50" />
          <p>検索キーワードを入力してください</p>
        </div>
      )}
    </div>
  );
}

export default SearchPage;