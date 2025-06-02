'use client';

import { useState } from 'react';
import SearchBar from './components/SearchBar';
import ProductCard from './components/ProductCard';

interface Product {
  product_id: string;
  name: string;
  category: string;
  description: string;
  top_ingredients: string;
  tags: string;
  'price (USD)': number;
  'margin (%)': number;
}

interface SearchResponse {
  query_type: 'QUESTION' | 'RECOMMENDATION';
  answer?: string;
  products?: Product[];
  follow_up_question?: string;
  context?: string[];
  session_id: string;
  conversation_context?: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8002';

export default function Home() {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setSearchResults(null);

    try {
      const requestBody: any = { query: searchQuery };
      if (sessionId) {
        requestBody.session_id = sessionId;
      }

      const response = await fetch(`${BACKEND_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'An error occurred during search');
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data);
      
      // Store session ID for future requests
      if (data.session_id) {
        setSessionId(data.session_id);
      }
    } catch (err) {
      console.error('Search API error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFollowUpClick = (followUpQuestion: string) => {
    setQuery(followUpQuestion);
    handleSearch(followUpQuestion);
  };

  const handleNewSession = () => {
    setSessionId(null);
    setSearchResults(null);
    setQuery('');
    setError(null);
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="text-center flex-1">
              <h1 className="text-3xl font-bold text-white mb-1">
                Skincare Store
              </h1>
              <p className="text-blue-100 text-xs">
                Your AI-powered personal skincare shopper
              </p>
            </div>
            {sessionId && (
              <div className="hidden md:block">
                <div className="bg-blue-500/20 rounded-lg px-3 py-2 border border-blue-400/30">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-xs text-blue-100 font-medium">Session Active</span>
                  </div>
                  <p className="text-xs text-blue-200 mb-2">Personalized recommendations enabled</p>
                  <button
                    onClick={handleNewSession}
                    className="text-xs bg-blue-400/20 hover:bg-blue-400/30 text-blue-100 px-2 py-1 rounded border border-blue-400/30 transition-colors duration-200"
                  >
                    Start New Session
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="max-w-2xl mx-auto mb-6">
          <SearchBar onSearch={handleSearch} initialQuery={query} setQuery={setQuery} />
        </div>
        
        {loading && (
          <div className="flex flex-col items-center justify-center my-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-sm text-gray-600">
              {sessionId ? 'Analyzing your request with conversation context...' : 'Finding the perfect products for you...'}
            </p>
            {sessionId && (
              <p className="text-xs text-gray-500 mt-1">Using personalized recommendations</p>
            )}
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg shadow-sm" role="alert">
              <div className="flex items-center">
                <svg className="w-5 h-5 text-red-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-red-700 text-sm">{error}</span>
              </div>
            </div>
          </div>
        )}

        {searchResults && (
          <div className="mt-6">
            {/* Enhanced Answer Section */}
            {searchResults.answer && (
              <div className="max-w-4xl mx-auto mb-8">
                {/* Conversation Context Indicator */}
                {searchResults.conversation_context && (
                  <div className="mb-4">
                    <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-3 border border-purple-200/50">
                      <div className="flex items-center gap-2 mb-2">
                        <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span className="text-sm font-medium text-purple-700">Building on our conversation</span>
                        <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full border border-purple-200">
                          Context-Aware
                        </span>
                      </div>
                      <p className="text-xs text-purple-600 leading-relaxed">
                        I'm using insights from our previous discussion to provide more personalized recommendations.
                      </p>
                    </div>
                  </div>
                )}

                <div className="bg-gradient-to-br from-blue-50 via-white to-indigo-50 rounded-xl shadow-lg border border-blue-100/50 overflow-hidden">
                  <div className="p-6">
                    {/* Header */}
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h3 className="text-lg font-semibold text-gray-800">
                        {searchResults.query_type === 'QUESTION' ? 'Expert Answer' : 'Personalized Recommendation'}
                      </h3>
                      <span className="text-xs font-medium bg-green-100 text-green-700 px-2 py-1 rounded-full border border-green-200">
                        AI-Powered
                      </span>
                    </div>

                    {/* Answer Content */}
                    <div className="mb-6">
                      <div className="text-gray-700 leading-relaxed text-sm bg-white rounded-lg p-4 border border-gray-100 shadow-sm">
                        {searchResults.answer}
                        {searchResults.context && searchResults.context.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-gray-100">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 font-medium">Sources:</span>
                              {searchResults.context.slice(0, 3).map((_, index) => (
                                <span key={index} className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-blue-600 bg-blue-100 rounded-full border border-blue-200">
                                  {index + 1}
                                </span>
                              ))}
                              {searchResults.context.length > 3 && (
                                <span className="text-xs text-gray-400">+{searchResults.context.length - 3} more</span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Context Sources */}
                    {searchResults.context && searchResults.context.length > 0 && (
                      <details className="group">
                        <summary className="flex items-center justify-between cursor-pointer hover:bg-blue-50/50 p-2 rounded-lg transition-colors duration-200">
                          <span className="text-sm font-medium text-blue-700">View source information ({searchResults.context.length})</span>
                          <svg className="w-4 h-4 text-blue-500 transform group-open:rotate-180 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </summary>
                        <div className="mt-3 space-y-2">
                          {searchResults.context.map((contextItem, index) => (
                            <div key={index} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-blue-600 bg-blue-100 rounded-full border border-blue-200">
                                  {index + 1}
                                </span>
                                <span className="text-xs font-medium text-gray-600">Source {index + 1}</span>
                              </div>
                              <p className="text-xs text-gray-700 leading-relaxed">{contextItem}</p>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Follow-up Question */}
            {searchResults.follow_up_question && (
              <div className="max-w-2xl mx-auto mb-6">
                <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg p-4 border border-amber-200/50">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <svg className="w-3 h-3 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-amber-800 mb-2">Let me help you find exactly what you need:</h4>
                      <p className="text-sm text-amber-700 mb-3">{searchResults.follow_up_question}</p>
                      <button
                        onClick={() => handleFollowUpClick(searchResults.follow_up_question!)}
                        className="inline-flex items-center gap-2 text-xs font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded-full border border-amber-300 transition-colors duration-200"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                        Continue conversation
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Products Section */}
            {searchResults.products && searchResults.products.length > 0 && (
              <div className="max-w-6xl mx-auto">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-bold text-gray-900">
                    {searchResults.query_type === 'QUESTION' ? 'Related Products' : 'Recommended Products'}
                  </h2>
                  <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full border border-gray-200">
                    {searchResults.products.length} products found
                  </span>
                </div>
                
                {/* AI Recommendation Context */}
                {searchResults.query_type === 'RECOMMENDATION' && (
                  <div className="bg-blue-50 rounded-lg p-4 mb-6 border border-blue-100">
                    <div className="flex items-center gap-2 mb-2">
                      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      <span className="text-sm font-medium text-blue-700">Why these products?</span>
                    </div>
                    <p className="text-sm text-blue-600">These products are ranked by relevance to your needs and our highest-margin items that deliver the best value.</p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {searchResults.products.map((product) => (
                    <ProductCard key={product.product_id} product={product} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}