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
    allow_origins=["http://localhost:3000"],
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
        self.model = "phi3.5:latest"
    
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
        
        # Build search query
        base_query = """
        SELECT * FROM products 
        WHERE (name LIKE ? OR description LIKE ? OR category LIKE ? OR benefits LIKE ?)
        """
        params = [f"%{query}%"] * 4
        
        if filters:
            if filters.get("category"):
                base_query += " AND category = ?"
                params.append(filters["category"])
            if filters.get("skin_type"):
                base_query += " AND skin_type LIKE ?"
                params.append(f"%{filters['skin_type']}%")
        
        # Order by margin (business logic)
        base_query += " ORDER BY margin DESC"
        
        cursor.execute(base_query, params)
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
        
        if not intent_analysis.get("needs_followup"):
            return None
        
        categories = list(set([p.category for p in products[:10]]))
        
        prompt = f"""
        User searched for: "{query}"
        Available product categories: {categories}
        
        Generate ONE specific, helpful follow-up question to better understand their needs.
        Keep it conversational and focused on narrowing down their choice.
        Examples:
        - "What skin concern are you targeting — hydration, acne, or anti-aging?"
        - "Are you looking for daily essentials or specific treatments?"
        - "What's your skin type — oily, dry, combination, or sensitive?"
        
        Generate a natural follow-up question:
        """
        
        return self.ollama.generate(prompt, max_tokens=100)
    
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
        
        categories = list(set([p.category for p in products]))
        
        prompt = f"""
        User searched for: "{query}"
        Found {len(products)} products across categories: {categories}
        
        Generate a brief, friendly response that:
        1. Acknowledges their search
        2. Highlights what you found
        3. Is encouraging and helpful
        
        Keep it under 30 words and conversational.
        Example: "Great choice! I found some excellent serums for hydration and anti-aging."
        
        Response:
        """
        
        return self.ollama.generate(prompt, max_tokens=50)
    
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
        response = conversational_service.process_search(request)

        # Add LLM output if the field exists
        llm_output = f"LLM interpretation of search query: {request.query}"
        if hasattr(response, "llm_output"):
            response.llm_output = llm_output

        return response
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


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