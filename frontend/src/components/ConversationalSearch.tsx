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

      // Use the API URL directly with http protocol and specific port
      const apiUrl = 'http://localhost:8001';
      console.log('Sending search request to:', apiUrl, searchRequest);
      
      // Create an AbortController to handle timeouts
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout (increased since backend takes ~30s)
      
      // Try using a CORS proxy to avoid cross-origin issues in the browser
      const corsProxyUrl = window.location.hostname === 'localhost' ? 
        `${apiUrl}/api/search` : // When running locally, use direct connection
        `https://corsproxy.io/?${encodeURIComponent(`${apiUrl}/api/search`)}`; // Use CORS proxy in other environments
        
      console.log('About to fetch from:', corsProxyUrl);
      const response = await fetch(corsProxyUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        },
        body: JSON.stringify(searchRequest),
        signal: controller.signal,
        mode: 'cors',
        credentials: 'omit' // Don't send cookies for cross-origin requests
      });
      
      // Clear the timeout since the request completed
      clearTimeout(timeoutId);
      console.log('Fetch complete, status:', response.status);
      
      if (!response.ok) {
        console.error(`Search failed with status: ${response.status}`);
        throw new Error(`Search failed with status: ${response.status}`);
      }
      
      // Try to get the response text first to debug any parsing issues
      const responseText = await response.text();
      console.log('Response text length:', responseText.length);
      if (responseText.length > 100) {
        console.log('Response text preview:', responseText.substring(0, 100) + '...');
      } else {
        console.log('Response text:', responseText);
      }
      
      // Parse the JSON manually
      let data: SearchResponse;
      try {
        data = JSON.parse(responseText) as SearchResponse;
        console.log('Parsed data successfully');
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        throw new Error(`Failed to parse response: ${parseError}`);
      }
      
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
      // Add error state handling
      setIsConversationActive(true);
      setConversationHistory([
        ...conversationHistory,
        { role: 'user' as const, content: searchQuery },
        { role: 'assistant' as const, content: 'Sorry, I had trouble processing your request. Please try again.' }
      ]);
      
      // Show basic error message and no products
      onSearchResults({
        response_type: 'results',
        message: 'Sorry, I had trouble processing your request. Please try again.',
        products: [],
        session_id: sessionId
      });
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
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
            onKeyDown={handleKeyDown}
            placeholder={isConversationActive 
              ? "Continue the conversation..." 
              : "What skincare products are you looking for? (e.g., 'serums for dry skin', 'something gentle for summer')"
            }
            className="block w-full pl-10 pr-12 py-4 border border-gray-300 rounded-xl text-lg placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
            disabled={isLoading}
            data-component-name="ConversationalSearch"
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
              <div className="flex items-center space-x-2" data-component-name="ConversationalSearch">
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
              onClick={() => handleSearch("anti-aging products")}
              className="px-3 py-2 text-sm bg-white border border-gray-200 rounded-full hover:border-blue-300 hover:text-blue-600 transition-colors"
            >
              "anti-aging products"
            </button>
          </div>
        </div>
      )}
    </div>
  );
}