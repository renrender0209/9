import { useState } from 'react';
import { useLocation } from 'wouter';
import { Search, Menu, Mic } from 'lucide-react';
import { SiYoutube } from 'react-icons/si';

function Header() {
  const [, setLocation] = useLocation();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setLocation(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="fixed top-0 w-full bg-youtube-dark-bg border-b border-gray-800 z-50 h-14">
      <div className="flex items-center justify-between px-4 h-full">
        {/* Left section */}
        <div className="flex items-center space-x-4">
          <button className="p-2 hover:bg-gray-800 rounded-full">
            <Menu size={20} />
          </button>
          <div 
            className="flex items-center space-x-1 cursor-pointer"
            onClick={() => setLocation('/')}
          >
            <SiYoutube className="text-youtube-red text-2xl" />
            <span className="text-white text-xl font-bold">YouTube</span>
            <span className="text-gray-400 text-xs ml-1">JP</span>
          </div>
        </div>

        {/* Center section - Search */}
        <div className="flex items-center max-w-2xl w-full mx-4">
          <form onSubmit={handleSearch} className="flex w-full">
            <div className="flex w-full">
              <input
                type="text"
                placeholder="検索"
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
            <button
              type="button"
              className="ml-2 p-2 bg-gray-800 hover:bg-gray-700 rounded-full"
            >
              <Mic size={20} />
            </button>
          </form>
        </div>

        {/* Right section */}
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
            U
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;