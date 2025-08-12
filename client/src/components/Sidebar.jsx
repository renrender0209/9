import { Link, useLocation } from 'wouter';
import { Home, TrendingUp, History, Clock, ThumbsUp, PlaySquare, Settings } from 'lucide-react';

function Sidebar() {
  const [location] = useLocation();

  const menuItems = [
    { icon: Home, label: 'ホーム', path: '/' },
    { icon: TrendingUp, label: 'トレンド', path: '/trending' },
    { icon: History, label: '履歴', path: '/history' },
    { icon: Clock, label: '後で見る', path: '/watch-later' },
    { icon: ThumbsUp, label: '高評価', path: '/liked' },
    { icon: PlaySquare, label: 'あなたの動画', path: '/my-videos' },
  ];

  const bottomItems = [
    { icon: Settings, label: '設定', path: '/settings' },
  ];

  const isActive = (path) => location === path;

  return (
    <aside className="fixed left-0 top-14 w-60 h-[calc(100vh-3.5rem)] bg-youtube-dark-bg border-r border-gray-800 overflow-y-auto z-40">
      <div className="py-2">
        {/* Main menu */}
        <div className="px-3 space-y-1">
          {menuItems.map((item) => (
            <Link key={item.path} href={item.path}>
              <div className={`flex items-center space-x-6 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                isActive(item.path) 
                  ? 'bg-gray-800 text-white' 
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}>
                <item.icon size={20} />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
            </Link>
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-800 my-4"></div>

        {/* Subscriptions section */}
        <div className="px-3">
          <h3 className="text-gray-400 text-sm font-medium mb-2 px-3">登録チャンネル</h3>
          <div className="space-y-1">
            {/* Placeholder for subscriptions */}
            <div className="text-gray-500 text-sm px-3 py-2">
              ログインして登録チャンネルを表示
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-800 my-4"></div>

        {/* YouTube Premium section */}
        <div className="px-3">
          <h3 className="text-gray-400 text-sm font-medium mb-2 px-3">YouTubeからのその他の機能</h3>
          <div className="space-y-1">
            <div className="text-gray-500 text-sm px-3 py-2">
              YouTube Premium
            </div>
            <div className="text-gray-500 text-sm px-3 py-2">
              YouTube Music
            </div>
            <div className="text-gray-500 text-sm px-3 py-2">
              YouTube Kids
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-gray-800 my-4"></div>

        {/* Bottom menu */}
        <div className="px-3 space-y-1">
          {bottomItems.map((item) => (
            <Link key={item.path} href={item.path}>
              <div className={`flex items-center space-x-6 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                isActive(item.path) 
                  ? 'bg-gray-800 text-white' 
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`}>
                <item.icon size={20} />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 text-xs text-gray-500">
          <div className="space-y-1">
            <div>© 2025 YouTube Clone</div>
            <div>Powered by Invidious API</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;