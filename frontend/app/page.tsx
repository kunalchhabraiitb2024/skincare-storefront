'use client';

import { useState, useEffect } from 'react';
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
}

interface SearchBarProps {
    onSearch: (query: string) => void;
    initialQuery: string;
    setQuery: (query: string) => void;
}

interface ProductCardProps {
    product: Product;
}

const BACKEND_URL = 'https://skincare-storefront.onrender.com';

export default function Home() {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setSearchResults(null);

    try {
      const response = await fetch(`${BACKEND_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'An error occurred during search');
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data);
    } catch (err) {
      console.error('Search API error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-center text-white mb-1">
            Skincare Store
          </h1>
          <p className="text-center text-blue-100 text-xs">
            Discover your perfect skincare products
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="max-w-2xl mx-auto mb-6">
          <SearchBar onSearch={handleSearch} initialQuery={query} setQuery={setQuery} />
        </div>
        
        {loading && (
          <div className="flex justify-center my-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-red-50 border-l-4 border-red-500 p-3 rounded-r-lg shadow-sm" role="alert">
              <div className="flex items-center">
                <span className="text-red-700 text-xs">{error}</span>
              </div>
            </div>
          </div>
        )}

        {searchResults && (
          <div className="mt-4">
            {searchResults.query_type === 'QUESTION' && (
              <>
                {searchResults.answer && (
                  <div className="mb-6">
                    <h2 className="text-xl font-semibold mb-2">Answer:</h2>
                    <p>{searchResults.answer}</p>
                  </div>
                )}
                {searchResults.products && searchResults.products.length > 0 && (
                  <div>
                    <h2 className="text-xl font-semibold mb-2">Related Products:</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {searchResults.products.map((product) => (
                        <ProductCard key={product.product_id} product={product} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {searchResults.query_type === 'RECOMMENDATION' && (
              <>
                {searchResults.follow_up_question && (
                  <div className="max-w-2xl mx-auto mb-6">
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm p-4 border border-blue-100">
                      <h3 className="text-xs font-semibold text-blue-800 mb-1 uppercase tracking-wider">Suggested Question:</h3>
                      <p className="text-blue-600 text-xs">{searchResults.follow_up_question}</p>
                    </div>
                  </div>
                )}

                {searchResults.products && (
                  <div>
                    <h2 className="text-xl font-semibold mb-2">Recommended Products:</h2>
                    {searchResults.products.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {searchResults.products.map((product) => (
                          <ProductCard key={product.product_id} product={product} />
                        ))}
                      </div>
                    ) : (
                      <p>No products found matching your criteria.</p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </main>
  );
} 