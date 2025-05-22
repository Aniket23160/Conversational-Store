import { useState } from 'react';
import { X, Star, ShoppingCart, MessageCircle, Send } from 'lucide-react';
import { Product, AskRequest, AskResponse } from '../types';
import { v4 as uuidv4 } from 'uuid';

interface ProductModalProps {
  product: Product;
  onClose: () => void;
}

export default function ProductModal({ product, onClose }: ProductModalProps) {
  const [activeTab, setActiveTab] = useState<'details' | 'ask'>('details');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [sessionId] = useState(() => uuidv4());

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(price);
  };

  const handleAskQuestion = async () => {
    if (!question.trim()) return;

    setIsAsking(true);
    try {
      const askRequest: AskRequest = {
        question: question,
        product_id: product.id,
        session_id: sessionId
      };

      const response = await fetch('http://localhost:8001/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(askRequest)
      });

      if (response.ok) {
        const data: AskResponse = await response.json();
        setAnswer(data);
      }
    } catch (error) {
      console.error('Error asking question:', error);
    } finally {
      setIsAsking(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAskQuestion();
    }
  };

  const quickQuestions = [
    "Is this suitable for sensitive skin?",
    "How often should I use this?",
    "What are the key ingredients?",
    "Can I use this with other products?"
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Product Details</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Product Overview */}
          <div className="p-6 border-b">
            <div className="flex items-start space-x-4">
              <img
                src={product.image_url}
                alt={product.name}
                className="w-20 h-20 object-cover rounded-lg"
              />
              <div className="flex-1">
                <h3 className="font-semibold text-lg text-gray-900 mb-1">
                  {product.name}
                </h3>
                <p className="text-sm text-gray-600 mb-2">{product.category}</p>
                <div className="flex items-center space-x-4">
                  <span className="text-2xl font-bold text-gray-900">
                    {formatPrice(product.price)}
                  </span>
                  <div className="flex items-center">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`w-4 h-4 ${
                          i < 4 ? 'text-yellow-400 fill-current' : 'text-gray-300'
                        }`}
                      />
                    ))}
                    <span className="text-sm text-gray-500 ml-1">4.2 (127)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b">
            <div className="flex">
              <button
                onClick={() => setActiveTab('details')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'details'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Product Details
              </button>
              <button
                onClick={() => setActiveTab('ask')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'ask'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Ask Questions
              </button>
            </div>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'details' ? (
              <div className="space-y-6">
                {/* Description */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Description</h4>
                  <p className="text-gray-700">{product.description}</p>
                </div>

                {/* Benefits */}
                {product.benefits && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Key Benefits</h4>
                    <p className="text-gray-700">{product.benefits}</p>
                  </div>
                )}

                {/* Skin Type */}
                {product.skin_type && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Suitable for</h4>
                    <p className="text-gray-700">{product.skin_type}</p>
                  </div>
                )}

                {/* Ingredients */}
                {product.ingredients && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Key Ingredients</h4>
                    <p className="text-gray-700">{product.ingredients}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Ask Question Interface */}
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Ask about this product</h4>
                  <div className="relative">
                    <textarea
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask me anything about this product..."
                      className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      rows={3}
                      disabled={isAsking}
                    />
                    <button
                      onClick={handleAskQuestion}
                      disabled={isAsking || !question.trim()}
                      className="absolute bottom-3 right-3 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Quick Questions */}
                <div>
                  <p className="text-sm text-gray-600 mb-2">Or try these common questions:</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {quickQuestions.map((q, index) => (
                      <button
                        key={index}
                        onClick={() => setQuestion(q)}
                        className="text-left p-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Loading */}
                {isAsking && (
                  <div className="flex items-center space-x-2 p-4 bg-gray-50 rounded-lg">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-sm text-gray-600">Getting your answer...</span>
                  </div>
                )}

                {/* Answer */}
                {answer && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start space-x-2">
                      <MessageCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-blue-900 mb-2">{answer.answer}</p>
                        {answer.citations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-blue-200">
                            <p className="text-xs text-blue-700 font-medium mb-1">Sources:</p>
                            {answer.citations.map((citation, index) => (
                              <p key={index} className="text-xs text-blue-600 mb-1">
                                "...{citation}..."
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-600">
            Free shipping on orders over $50
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:text-gray-900 transition-colors"
            >
              Close
            </button>
            <button className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              <ShoppingCart className="w-4 h-4 mr-2" />
              Add to Cart
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}