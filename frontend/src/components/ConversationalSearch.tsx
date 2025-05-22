import { useState } from 'react';
import { Search, Send, MessageCircle, X } from 'lucide-react';
import { SearchRequest, SearchResponse, ConversationMessage } from '../types';

interface ConversationalSearchProps {
  sessionId: string;
  onSearchResults: (response: SearchResponse) => void;
  onClear: () => void;
}

export default function ConversationalSearch({ 
  sessionId, 
  onSearchResults, 
  onClear 
}: ConversationalSearchProps) {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [currentFollowUp, setCurrentFollowUp] = useState<string>('');
  const [isConversationActive, setIsConversationActive] = useState(false);

  const handleSearch = async (searchQuery: string = query) => {
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    
    try {
      const searchRequest: SearchRequest = {
        query: searchQuery,
        session_id: sessionId,
        conversation_history: conversationHistory
      };

      const response = await fetch('http://localhost:8001/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchRequest)
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data: SearchResponse = await response.json();
      
      // Update conversation history
      const newHistory = [
        ...conversationHistory,
        { role: 'user' as const, content: searchQuery },
        { role: 'assistant' as const, content: data.message }
      ];
      setConversationHistory(newHistory);
      
      // Set follow-up question if present
      setCurrentFollowUp(data.follow_up_question || '');
      
      // Show results
      onSearchResults(data);
      
      setIsConversationActive(true);
      setQuery('');
      
    } catch (error) {
      console.error('Search error:', error);
      // You could add error state handling here
    } finally {
      setIsLoading(false);
    }
  };

  const handleFollowUpClick = (followUpQuestion: string) => {
    setQuery(followUpQuestion);
  };

  const handleClear = () => {
    setConversationHistory([]);
    setCurrentFollowUp('');
    setIsConversationActive(false);
    setQuery('');
    onClear();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Main Search Bar */}
      <div className="relative">
        <div className="relative flex items-center">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isConversationActive 
              ? "Continue the conversation..." 
              : "What skincare products are you looking for? (e.g., 'serums for dry skin', 'something gentle for summer')"
            }
            className="block w-full pl-10 pr-12 py-4 border border-gray-300 rounded-xl text-lg placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
            disabled={isLoading}
          />
          
          <button
            onClick={() => handleSearch()}
            disabled={isLoading || !query.trim()}
            className="absolute inset-y-0 right-0 pr-3 flex items-center"
          >
            <Send 
              className={`h-5 w-5 transition-colors ${
                isLoading || !query.trim() 
                  ? 'text-gray-300' 
                  : 'text-blue-600 hover:text-blue-700'
              }`} 
            />
          </button>
        </div>
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute top-full left-0 right-0 mt-2">
            <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm text-gray-600">Finding your perfect products...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Follow-up Question */}
      {currentFollowUp && !isLoading && (
        <div className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
          <div className="flex items-start space-x-3">
            <MessageCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-blue-800 font-medium mb-2">Let me help you narrow it down:</p>
              <p className="text-blue-700 mb-3">{currentFollowUp}</p>
              <button
                onClick={() => handleFollowUpClick(currentFollowUp)}
                className="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
              >
                Answer this question
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Conversation History (simplified) */}
      {isConversationActive && (
        <div className="mt-4 flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center space-x-2">
            <MessageCircle className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-600">
              Conversation active • {conversationHistory.length / 2} exchanges
            </span>
          </div>
          
          <button
            onClick={handleClear}
            className="flex items-center space-x-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X className="h-4 w-4" />
            <span>Clear & start over</span>
          </button>
        </div>
      )}

      {/* Quick Examples (shown when not active) */}
      {!isConversationActive && !isLoading && (
        <div className="mt-6">
          <p className="text-sm text-gray-600 mb-3">Try these examples:</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleSearch("serums for acne-prone skin")}
              className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-full hover:border-blue-300 hover:text-blue-600 transition-colors"
            >
              "serums for acne-prone skin"
            </button>
            <button
              onClick={() => handleSearch("something gentle for summer")}
              className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-full hover:border-blue-300 hover:text-blue-600 transition-colors"
            >
              "something gentle for summer"
            </button>
            <button
              onClick={() => handleSearch("moisturizer for dry skin")}
              className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-full hover:border-blue-300 hover:text-blue-600 transition-colors"
            >
              "moisturizer for dry skin"
            </button>
          </div>
        </div>
      )}
    </div>
  );
}