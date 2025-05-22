import { useState, useEffect } from 'react';
import { Search, ShoppingBag, Star, Filter } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import ProductGrid from '../components/ProductGrid';
import ConversationalSearch from '../components/ConversationalSearch';
import { Product, SearchResponse } from '../types';

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isSearchActive, setIsSearchActive] = useState(false);
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [searchMessage, setSearchMessage] = useState<string>('');
  const [sessionId] = useState<string>(() => uuidv4());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      
      // Fetch products
      const productsResponse = await fetch('http://localhost:8001/api/products');
      const productsData = await productsResponse.json();
      setProducts(productsData);

      // Fetch categories
      const categoriesResponse = await fetch('http://localhost:8001/api/categories');
      const categoriesData = await categoriesResponse.json();
      setCategories(['All', ...categoriesData.categories]);
      
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchResults = (response: SearchResponse) => {
    setSearchResults(response.products);
    setSearchMessage(response.message);
    setIsSearchActive(true);
  };

  const clearSearch = () => {
    setIsSearchActive(false);
    setSearchResults([]);
    setSearchMessage('');
  };

  const filteredProducts = isSearchActive 
    ? searchResults 
    : selectedCategory === 'All' 
      ? products 
      : products.filter(p => p.category === selectedCategory);

  const displayMessage = isSearchActive ? searchMessage : '';

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your skincare store...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <ShoppingBag className="h-8 w-8 text-blue-600" />
              <h1 className="ml-2 text-xl font-bold text-gray-900">
                Assignment Project
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                {products.length} Products
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Conversational Search Section */}
        <div className="mb-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Find Your Perfect Skincare
            </h2>
            <p className="text-gray-600">
              Tell me what you're looking for, and I'll help you find the perfect products
            </p>
          </div>
          
          <ConversationalSearch 
            sessionId={sessionId}
            onSearchResults={handleSearchResults}
            onClear={clearSearch}
          />
        </div>

        {/* Results Message */}
        {displayMessage && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-blue-800">{displayMessage}</p>
            {isSearchActive && (
              <button
                onClick={clearSearch}
                className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline"
              >
                Clear search and browse all products
              </button>
            )}
          </div>
        )}

        {/* Category Filter */}
        {!isSearchActive && (
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-4">
              <Filter className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Filter by category:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    selectedCategory === category
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-white text-gray-700 border border-gray-300 hover:border-blue-400 hover:text-blue-600'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Products Grid */}
        <ProductGrid 
          products={filteredProducts} 
          isSearchResults={isSearchActive}
        />
        
        {/* No Results */}
        {filteredProducts.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <Search className="h-16 w-16 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {isSearchActive ? 'No matching products found' : 'No products available'}
            </h3>
            <p className="text-gray-600 mb-4">
              {isSearchActive 
                ? 'Try adjusting your search or ask for different recommendations'
                : 'Please check back later for new products'
              }
            </p>
            {isSearchActive && (
              <button
                onClick={clearSearch}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                Browse All Products
              </button>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-600">
            <p>&copy; 2024 Glow Beauty Store. AI-powered skincare recommendations.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}