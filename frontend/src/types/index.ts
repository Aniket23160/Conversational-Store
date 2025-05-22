export interface Product {
    id: number;
    name: string;
    category: string;
    price: number;
    margin: number;
    description: string;
    ingredients?: string;
    skin_type?: string;
    benefits?: string;
    image_url: string;
  }
  
  export interface SearchRequest {
    query: string;
    session_id: string;
    conversation_history: ConversationMessage[];
  }
  
  export interface SearchResponse {
    response_type: 'question' | 'results' | 'answer';
    message: string;
    products: Product[];
    follow_up_question?: string;
    session_id: string;
  }
  
  export interface AskRequest {
    question: string;
    product_id?: number;
    session_id: string;
  }
  
  export interface AskResponse {
    answer: string;
    citations: string[];
    session_id: string;
  }
  
  export interface ConversationMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string;
  }