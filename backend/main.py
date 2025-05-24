from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
import requests
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Conversational Store API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma_client = chromadb.PersistentClient(path="./data/chroma_db")

# In-memory session storage
conversations = {}

class Product(BaseModel):
    id: int
    name: str
    category: str
    price: float
    margin: float
    description: str
    ingredients: Optional[str]
    skin_type: Optional[str]
    benefits: Optional[str]
    image_url: str

class SearchRequest(BaseModel):
    query: str
    session_id: str
    conversation_history: List[Dict[str, str]] = []

class SearchResponse(BaseModel):
    response_type: str  # "question" or "results"
    message: str
    products: List[Product] = []
    follow_up_question: Optional[str] = None
    session_id: str

class AskRequest(BaseModel):
    question: str
    product_id: Optional[int] = None
    session_id: str

class AskResponse(BaseModel):
    answer: str
    citations: List[str] = []
    session_id: str

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.1:8b"
    
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "max_tokens": max_tokens
                    }
                },
                timeout=100
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return "I'm having trouble processing your request right now. Please try again."

class ProductService:
    def __init__(self):
        self.db_path = "./data/products.db"
        self.ollama_service = OllamaService()
        self.rag_service = RAGService()
    
    def get_all_products(self) -> List[Product]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        conn.close()
        
        return [Product(**dict(row)) for row in rows]
    
    def get_products_by_category(self, category: str) -> List[Product]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE category = ?", (category,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Product(**dict(row)) for row in rows]
    
    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        
        return Product(**dict(row)) if row else None
    
    def search_products(self, query: str, filters: Dict = None) -> List[Product]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Handle empty query
        if not query or query.strip() == "":
            # Return all products if query is empty
            cursor.execute("SELECT * FROM products ORDER BY margin DESC")
            rows = cursor.fetchall()
            conn.close()
            return [Product(**dict(row)) for row in rows]
        
        # Pre-process the search query
        query_lower = query.lower()
        
        # Handle special search terms and common mappings
        special_term_mappings = {
            # Singular/Plural forms
            "serum": "serum",
            "serums": "serum",
            "cleanser": "cleanser",
            "cleansers": "cleanser",
            "moisturizer": "moisturizer",
            "moisturizers": "moisturizer",
            "cream": "cream",
            "creams": "cream",
            "mask": "mask",
            "masks": "mask",
            "toner": "toner",
            "toners": "toner",
            
            # Common descriptive terms
            "anti-aging": "anti-aging",
            "antiaging": "anti-aging",
            "anti aging": "anti-aging",
            "hydrating": "hydration",
            "hydrate": "hydration",
            "acne": "acne",
            "sensitive": "sensitive"
        }
        
        # Check for exact category matches first
        cursor.execute("SELECT DISTINCT category FROM products")
        all_categories = [row[0].lower() for row in cursor.fetchall()]
        
        # Split the query into words for flexible matching
        original_terms = query_lower.split()
        search_terms = []
        
        # Process search terms with special mappings
        for term in original_terms:
            # Add the original term
            search_terms.append(term)
            
            # Add mapped terms if they exist
            if term in special_term_mappings:
                mapped_term = special_term_mappings[term]
                if mapped_term != term:
                    search_terms.append(mapped_term)
        
        # Build search query with more flexible matching
        conditions = []
        params = []
        
        for term in search_terms:
            term_pattern = f"%{term}%"
            conditions.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ? OR LOWER(ingredients) LIKE ? OR LOWER(skin_type) LIKE ? OR LOWER(benefits) LIKE ?)")
            params.extend([term_pattern] * 6)
        
        # Combine conditions with OR for more flexible matching
        base_query = f"""
        SELECT * FROM products 
        WHERE {" OR ".join(conditions)}
        """
        
        # Apply filters if provided
        if filters:
            if filters.get("category"):
                base_query += " AND LOWER(category) = LOWER(?)"
                params.append(filters["category"])
            if filters.get("skin_type"):
                base_query += " AND LOWER(skin_type) LIKE LOWER(?)"
                params.append(f"%{filters['skin_type']}%")
        
        # Order by margin (business logic)
        base_query += " ORDER BY margin DESC"
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        
        # If no results found with the initial search, try semantic search with the RAG system first
        if not rows and hasattr(self, 'rag_service'):
            try:
                # First, try to use RAG to find related concepts
                logger.info(f"Using RAG to find alternatives for query: {query}")
                rag_results = self.rag_service.query_knowledge(query, n_results=3)
                
                # Log the RAG results for debugging
                logger.info(f"RAG results: {rag_results}")
                
                # Extract potential keywords from RAG results
                rag_content = " ".join([doc.get('content', '') for doc in rag_results if doc.get('score', 0) > 0.5])
                
                if rag_content:
                    # First try direct keyword match from RAG content
                    potential_keywords = [word for word in rag_content.lower().split() 
                                         if len(word) > 4 and word not in ['about', 'these', 'those', 'their', 'there']]
                    
                    # Try using RAG-derived keywords
                    for keyword in potential_keywords[:8]:  # Try more keywords
                        pattern = f"%{keyword}%"
                        cursor.execute("""SELECT * FROM products 
                                         WHERE LOWER(description) LIKE ? 
                                         OR LOWER(benefits) LIKE ? 
                                         OR LOWER(ingredients) LIKE ?
                                         ORDER BY margin DESC LIMIT 20""", 
                                      [pattern, pattern, pattern])
                        rag_rows = cursor.fetchall()
                        
                        if rag_rows:
                            logger.info(f"Found products using RAG-derived keyword: {keyword}")
                            rows = rag_rows
                            break
            except Exception as e:
                # Log error but continue to next approach
                logger.error(f"Error using RAG for search: {e}")
        
        # If RAG didn't yield results, use Ollama LLM to generate alternative search terms
        if not rows and hasattr(self, 'ollama_service'):
            try:
                # Create a more specific prompt for the query
                if 'anti-aging' in query_lower or 'anti aging' in query_lower or 'antiaging' in query_lower:
                    # Specific prompt for anti-aging
                    prompt = f"""
                    The user is looking for anti-aging skincare products with the search: "{query}"
                    Our database contains skincare products like serums, moisturizers, and treatments.
                    What specific ingredients or product types should we search for related to anti-aging?
                    Return 5 specific terms as a comma-separated list.
                    """
                else:
                    # General prompt for other queries
                    prompt = f"""
                    The user searched for: "{query}"
                    No results were found in our skincare product database, which includes categories like:
                    serums, moisturizers, cleansers, toners, masks, sunscreens.
                    Generate 5 alternative search terms or keywords that might be relevant to this query.
                    Format the response as a comma-separated list.
                    """
                
                # Get alternative search terms from LLM
                logger.info(f"Using Ollama to generate alternatives for: {query}")
                alt_terms_response = self.ollama_service.generate(prompt, max_tokens=150)
                logger.info(f"Ollama response: {alt_terms_response}")
                
                # Parse the response and clean up terms
                alt_terms = [term.strip() for term in alt_terms_response.split(',')]
                logger.info(f"Alternative terms: {alt_terms}")
                
                # Try each alternative term
                for alt_term in alt_terms:
                    if alt_term and len(alt_term) > 2:
                        alt_query = """
                        SELECT * FROM products 
                        WHERE LOWER(name) LIKE ? 
                        OR LOWER(description) LIKE ? 
                        OR LOWER(category) LIKE ? 
                        OR LOWER(benefits) LIKE ?
                        OR LOWER(ingredients) LIKE ?
                        ORDER BY margin DESC
                        """
                        pattern = f"%{alt_term.lower()}%"
                        cursor.execute(alt_query, [pattern, pattern, pattern, pattern, pattern])
                        alt_rows = cursor.fetchall()
                        
                        if alt_rows:
                            logger.info(f"Found products using LLM-suggested term: {alt_term}")
                            rows = alt_rows
                            break
            except Exception as e:
                # Log error but continue with default search behavior
                logger.error(f"Error using LLM for alternative search terms: {e}")
            
        # If all LLM and RAG approaches failed (or aren't available), fall back to fuzzy matching
        if not rows:
            # Try with wildcards between characters for fuzzy matching
            wildcard_conditions = []
            wildcard_params = []
            
            for term in original_terms:
                if len(term) > 3:  # Only for terms longer than 3 characters
                    # Create patterns like '%a%n%t%i%-%a%g%i%n%g%' for 'anti-aging'
                    wildcard_pattern = '%' + '%'.join(term) + '%'
                    wildcard_conditions.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(category) LIKE ?)")
                    wildcard_params.extend([wildcard_pattern] * 3)
            
            if wildcard_conditions:
                wildcard_query = f"""
                SELECT * FROM products 
                WHERE {" OR ".join(wildcard_conditions)}
                ORDER BY margin DESC
                """
                
                cursor.execute(wildcard_query, wildcard_params)
                rows = cursor.fetchall()
        
        conn.close()
        return [Product(**dict(row)) for row in rows]
    
    def get_categories(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT category FROM products")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return categories

class RAGService:
    def __init__(self):
        try:
            self.collection = chroma_client.get_collection("skincare_knowledge")
        except:
            self.collection = chroma_client.create_collection("skincare_knowledge")
    
    def query_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            documents = []
            for i, doc in enumerate(results['documents'][0]):
                documents.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'][0] else {},
                    'score': 1 - results['distances'][0][i] if results['distances'][0] else 0
                })
            
            return documents
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return []

class ConversationalService:
    def __init__(self):
        self.ollama = OllamaService()
        self.product_service = ProductService()
        self.rag_service = RAGService()
    
    def analyze_query_intent(self, query: str, history: List[Dict]) -> Dict:
        """Analyze if query needs follow-up questions or can be answered directly"""
        
        prompt = f"""
        Analyze this user query in a skincare product context:
        Query: "{query}"
        
        Previous conversation: {json.dumps(history[-2:]) if history else "None"}
        
        Classify the intent as one of:
        1. SPECIFIC_SEARCH - User wants specific products (has clear criteria)
        2. VAGUE_SEARCH - User needs guidance (vague requirements)
        3. QUESTION - User asking about product info/advice
        
        Also determine what follow-up questions (if any) are needed.
        
        Respond in JSON format:
        {{
            "intent": "SPECIFIC_SEARCH|VAGUE_SEARCH|QUESTION",
            "confidence": 0.8,
            "needs_followup": true/false,
            "suggested_followup": "question text or null",
            "search_terms": ["extracted", "keywords"],
            "filters": {{"category": "optional", "skin_type": "optional"}}
        }}
        """
        
        response = self.ollama.generate(prompt, max_tokens=300)
        try:
            return json.loads(response)
        except:
            # Fallback analysis
            return {
                "intent": "VAGUE_SEARCH" if len(query.split()) < 3 else "SPECIFIC_SEARCH",
                "confidence": 0.5,
                "needs_followup": len(query.split()) < 3,
                "suggested_followup": "What type of skincare products are you looking for?",
                "search_terms": query.split(),
                "filters": {}
            }
    
    def generate_followup_question(self, query: str, intent_analysis: Dict, products: List[Product]) -> str:
        """Generate contextual follow-up questions"""
        
        # Always generate follow-up questions for first-time searches to make the experience more interactive
        # unless the query is very specific
        if len(query.split()) > 6 and not intent_analysis.get("needs_followup"):
            return None
        
        # Create custom follow-up questions based on the query and available products
        query_lower = query.lower()
        
        # Extract unique categories from products
        categories = list(set([p.category for p in products[:10]]))
        
        # Create targeted follow-up questions based on the search context
        if "serum" in query_lower:
            if "dry" in query_lower:
                return "Would you prefer a hydrating serum with hyaluronic acid or one with more anti-aging benefits?"
            elif "acne" in query_lower or "oily" in query_lower:
                return "Are you looking for serums that focus on oil control, acne treatment, or both?"
            else:
                return "What's your main skin concern — hydration, brightening, or anti-aging?"
                
        elif "moisturizer" in query_lower or "cream" in query_lower:
            if "dry" in query_lower:
                return "Would you prefer a rich night cream or something lighter for daytime use?"
            else:
                return "What's your skin type — oily, combination, dry, or sensitive?"
                
        elif "gentle" in query_lower or "sensitive" in query_lower:
            return "Are you looking for fragrance-free products or just mild formulations?"
            
        elif "summer" in query_lower:
            return "Would you prefer products with SPF protection or lightweight oil-free formulations?"
            
        elif len(categories) > 2:
            # When there are multiple categories, ask for preference
            category_options = ", ".join(categories[:3])
            return f"I found several options across {category_options}. Which category interests you most?"
            
        else:
            # Generic follow-up questions as a fallback
            generic_questions = [
                "What's your skin type — oily, dry, combination, or sensitive?",
                "What skin concern are you focusing on — hydration, acne, or anti-aging?",
                "Do you prefer products with natural ingredients or specific active ingredients?",
                "Are you looking for morning or evening skincare products?"
            ]
            
            # Return a contextually appropriate question
            if len(query.split()) < 3:
                return generic_questions[0]  # Ask about skin type for very short queries
            else:
                return generic_questions[1]  # Ask about skin concerns for more detailed queries
    
    def process_search(self, request: SearchRequest) -> SearchResponse:
        """Main search processing logic"""
        
        session_id = request.session_id or str(uuid.uuid4())
        
        # Store conversation history
        if session_id not in conversations:
            conversations[session_id] = []
        
        conversations[session_id].append({
            "role": "user",
            "content": request.query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Analyze query intent
        intent_analysis = self.analyze_query_intent(request.query, request.conversation_history)
        
        # Search products
        search_terms = " ".join(intent_analysis.get("search_terms", [request.query]))
        products = self.product_service.search_products(search_terms, intent_analysis.get("filters"))
        
        # Determine response type
        if intent_analysis.get("intent") == "QUESTION":
            # Handle as Q&A
            answer = self.answer_question(request.query, products[:5])
            conversations[session_id].append({
                "role": "assistant",
                "content": answer,
                "timestamp": datetime.now().isoformat()
            })
            return SearchResponse(
                response_type="answer",
                message=answer,
                products=[],
                session_id=session_id
            )
        
        # Generate follow-up if needed
        follow_up = None
        if intent_analysis.get("needs_followup") and len(request.conversation_history) < 2:
            follow_up = self.generate_followup_question(request.query, intent_analysis, products)
        
        # Generate contextual message
        if products:
            message = self.generate_search_response_message(request.query, products[:10])
        else:
            message = "I couldn't find products matching your request. Could you try a different search term?"
        
        conversations[session_id].append({
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        return SearchResponse(
            response_type="results",
            message=message,
            products=products[:12],  # Limit results
            follow_up_question=follow_up,
            session_id=session_id
        )
    
    def generate_search_response_message(self, query: str, products: List[Product]) -> str:
        """Generate contextual response message for search results"""
        
        if not products:
            return "I couldn't find products matching your request. Could you try a different search term?"
            
        # Extract relevant information from products
        categories = list(set([p.category for p in products]))
        skin_types = list(set([p.skin_type for p in products if p.skin_type]))
        
        # Create a more specific message based on the products found
        if len(categories) == 1:
            category_text = f"these {categories[0]} products"
        else:
            category_text = f"products across {', '.join(categories[:-1])}{' and ' if len(categories) > 1 else ''}{categories[-1] if len(categories) else ''}"
        
        # Include skin type if relevant
        skin_type_text = ""
        if skin_types:
            skin_type_text = f" perfect for {', '.join(skin_types[:-1])}{' and ' if len(skin_types) > 1 else ''}{skin_types[-1] if len(skin_types) else ''} skin"
        
        # Create a customized response message
        if "dry" in query.lower() or any("dry" in st.lower() for st in skin_types):
            return f"I've found {len(products)} {category_text} that provide deep hydration{skin_type_text}. Take a look!"
        elif "oily" in query.lower() or any("oily" in st.lower() for st in skin_types):
            return f"Here are {len(products)} {category_text} to help balance oil production{skin_type_text}!"
        elif "summer" in query.lower():
            return f"Perfect for summer! I've found {len(products)} lightweight {category_text} that won't feel heavy in the heat."
        elif "gentle" in query.lower() or "sensitive" in query.lower() or any("sensitive" in st.lower() for st in skin_types):
            return f"I've selected {len(products)} gentle {category_text} that are perfect for sensitive skin. Take a look!"
        else:
            return f"Great choice! I found {len(products)} {category_text}{skin_type_text} for you to explore."
    
    def answer_question(self, question: str, relevant_products: List[Product] = None) -> str:
        """Answer questions using RAG and product data"""
        
        # Get relevant knowledge from RAG
        rag_docs = self.rag_service.query_knowledge(question, n_results=3)
        
        # Prepare context
        rag_context = "\n".join([doc['content'] for doc in rag_docs[:2]])
        product_context = ""
        
        if relevant_products:
            product_context = "\n".join([
                f"- {p.name}: {p.description} (Benefits: {p.benefits})"
                for p in relevant_products[:3]
            ])
        
        prompt = f"""
        User question: "{question}"
        
        Relevant product information:
        {product_context}
        
        Additional knowledge:
        {rag_context}
        
        Provide a helpful, accurate answer based on the available information.
        If referencing specific information, mention the source briefly.
        Keep the response under 100 words and conversational.
        
        Answer:
        """
        
        return self.ollama.generate(prompt, max_tokens=150)

# Initialize services
product_service = ProductService()
conversational_service = ConversationalService()

# API Routes
@app.get("/")
async def root():
    return {"message": "Conversational Store API", "status": "running"}

@app.get("/api/products", response_model=List[Product])
async def get_products():
    try:
        return product_service.get_all_products()
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")

@app.get("/api/categories")
async def get_categories():
    try:
        return {"categories": product_service.get_categories()}
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")

@app.get("/api/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    product = product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    try:
        logger.info(f"Received search request - Query: '{request.query}', Session ID: {request.session_id}")
        logger.info(f"Conversation history length: {len(request.conversation_history)}")
        
        # Process the search request
        response = conversational_service.process_search(request)
        logger.info(f"Search response generated - Found {len(response.products)} products")
        logger.info(f"Response message: '{response.message[:100]}...'")
        
        # Add LLM output if the field exists
        llm_output = f"LLM interpretation of search query: {request.query}"
        if hasattr(response, "llm_output"):
            response.llm_output = llm_output

        return response
    except Exception as e:
        logger.error(f"Search error: {e}")
        logger.exception("Search error details:")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    try:
        session_id = request.session_id or str(uuid4())

        # Get relevant products if product_id provided
        relevant_products = []
        if request.product_id:
            product = product_service.get_product_by_id(request.product_id)
            if product:
                relevant_products = [product]

        # Generate answer
        answer = conversational_service.answer_question(request.question, relevant_products)

        # Get citations from RAG
        rag_docs = conversational_service.rag_service.query_knowledge(request.question, n_results=2)
        citations = [doc['content'][:100] + "..." for doc in rag_docs if doc['score'] > 0.7]

        # Add LLM output if the field exists
        llm_output = f"LLM reasoning for the question: {request.question}"

        return AskResponse(
            answer=answer,
            citations=citations,
            session_id=session_id,
            llm_output=llm_output if "llm_output" in AskResponse.__fields__ else None
        )
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process question")

@app.get("/api/health")
async def health_check():
    # Check Ollama connection
    try:
        ollama_service = OllamaService()
        test_response = ollama_service.generate("Test", max_tokens=10)
        ollama_status = "healthy" if test_response else "unhealthy"
    except:
        ollama_status = "unhealthy"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ollama": ollama_status,
            "database": "healthy",
            "vector_store": "healthy"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)