import { Router, Route, Switch } from 'wouter';
import Header from '@components/Header';
import Sidebar from '@components/Sidebar';
import HomePage from '@pages/HomePage';
import SearchPage from '@pages/SearchPage';
import VideoPage from '@pages/VideoPage';
import HistoryPage from '@pages/HistoryPage';

function App() {
  return (
    <div className="min-h-screen bg-youtube-dark-bg text-white">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 ml-60">
          <Router>
            <Switch>
              <Route path="/" component={HomePage} />
              <Route path="/search" component={SearchPage} />
              <Route path="/watch/:videoId" component={VideoPage} />
              <Route path="/history" component={HistoryPage} />
              <Route>
                <div className="p-8 text-center">
                  <h1 className="text-2xl font-bold mb-4">ページが見つかりません</h1>
                  <p className="text-gray-400">お探しのページは存在しません。</p>
                </div>
              </Route>
            </Switch>
          </Router>
        </main>
      </div>
    </div>
  );
}

export default App;