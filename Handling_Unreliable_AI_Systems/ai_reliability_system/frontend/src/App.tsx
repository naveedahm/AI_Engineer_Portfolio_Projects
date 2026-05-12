import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ChatInterface } from './components/Chat/ChatInterface';
import { Dashboard } from './components/Monitoring/Dashboard';
import { ErrorBoundary } from './components/Common/ErrorBoundary';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 60000,
    },
  },
});

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard'>('chat');

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex">
                  <div className="flex-shrink-0 flex items-center">
                    <h1 className="text-xl font-bold text-gray-900">
                      AI Reliability System
                    </h1>
                  </div>
                  <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                    <button
                      onClick={() => setActiveTab('chat')}
                      className={`${
                        activeTab === 'chat'
                          ? 'border-indigo-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                    >
                      Chat
                    </button>
                    <button
                      onClick={() => setActiveTab('dashboard')}
                      className={`${
                        activeTab === 'dashboard'
                          ? 'border-indigo-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                    >
                      Dashboard
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </nav>

          <main className="py-10">
            <div className="max-w-7xl mx-auto sm:px-6 lg:px-8">
              {activeTab === 'chat' ? <ChatInterface /> : <Dashboard />}
            </div>
          </main>
        </div>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;