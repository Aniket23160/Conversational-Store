import { useState } from 'react';
import { Star, Info, ShoppingCart, Sparkles } from 'lucide-react';
import { Product } from '../types';
import ProductModal from './ProductModal';

interface ProductGridProps {
  products: Product[];
  isSearchResults?: boolean;
}

export default function ProductGrid({ products, isSearchResults = false }: ProductGridProps) {
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(price);
  };

  const getMarginBadge = (margin: number) => {
    if (margin >= 0.7) return { label: 'Best Value', color: 'bg-green-100 text-green-800' };
    if (margin >= 0.6) return { label: 'Good Value', color: 'bg-blue-100 text-blue-800' };
    return { label: 'Premium', color: 'bg-purple-100 text-purple-800' };
  };

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map((product, index) => {
          const marginBadge = getMarginBadge(product.margin);
          
          return (
            <div
              key={product.id}
              className={`bg-white rounded-xl shadow-sm border hover:shadow-md transition-all duration-200 overflow-hidden group ${
                isSearchResults ? 'ring-1 ring-blue-200' : ''
              }`}
            >
              {/* Product Image */}
              <div className="relative aspect-square bg-gray-100">
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
                
                {/* Badges */}
                <div className="absolute top-3 left-3 flex flex-col gap-1">
                  {isSearchResults && index < 3 && (
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-600 text-white">
                      <Sparkles className="w-3 h-3 mr-1" />
                      AI Pick
                    </span>
                  )}
                  <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${marginBadge.color}`}>
                    {marginBadge.label}
                  </span>
                </div>

                {/* Quick Info Button */}
                <button
                  onClick={() => setSelectedProduct(product)}
                  className="absolute top-3 right-3 p-2 bg-white/90 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:bg-white"
                >
                  <Info className="w-4 h-4 text-gray-600" />
                </button>
              </div>

              {/* Product Info */}
              <div className="p-4">
                <div className="mb-2">
                  <h3 className="font-semibold text-gray-900 text-sm leading-tight line-clamp-2">
                    {product.name}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">{product.category}</p>
                </div>

                {/* Description */}
                <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                  {product.description}
                </p>

                {/* Skin Type & Benefits */}
                <div className="mb-3 space-y-1">
                  {product.skin_type && (
                    <div className="flex items-center text-xs text-gray-500">
                      <span className="font-medium">For:</span>
                      <span className="ml-1">{product.skin_type}</span>
                    </div>
                  )}
                  {product.benefits && (
                    <div className="flex items-center text-xs text-blue-600">
                      <span className="font-medium">Benefits:</span>
                      <span className="ml-1 line-clamp-1">{product.benefits}</span>
                    </div>
                  )}
                </div>

                {/* Price and Action */}
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-lg font-bold text-gray-900">
                      {formatPrice(product.price)}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSelectedProduct(product)}
                      className="px-3 py-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Details
                    </button>
                    <button className="flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors">
                      <ShoppingCart className="w-3 h-3 mr-1" />
                      Add
                    </button>
                  </div>
                </div>

                {/* Rating (placeholder) */}
                <div className="flex items-center mt-2 pt-2 border-t border-gray-100">
                  <div className="flex items-center">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`w-3 h-3 ${
                          i < 4 ? 'text-yellow-400 fill-current' : 'text-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-gray-500 ml-1">4.2 (127 reviews)</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Product Modal */}
      {selectedProduct && (
        <ProductModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </>
  );
}