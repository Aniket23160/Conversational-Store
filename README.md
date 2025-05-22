# Conversational Store - Mini POC

A full-stack conversational e-commerce application with AI-powered product recommendations and search capabilities using local Ollama LLM.

Some screenshots of working code:
<img width="1470" alt="Screenshot 2025-05-22 at 11 11 22 PM" src="https://github.com/user-attachments/assets/2da17838-b19e-4b2f-a1f8-ca4837c0175d" />
<img width="1470" alt="Screenshot 2025-05-22 at 11 08 05 PM" src="https://github.com/user-attachments/assets/0f66b7b2-1f83-443b-80c9-87c09a16e4ec" />
<img width="1470" alt="Screenshot 2025-05-22 at 11 10 54 PM" src="https://github.com/user-attachments/assets/8a1861bf-de29-4829-a71b-ab49a191d5f0" />


## Features

- **Mini Storefront**: 30+ SKUs across 3+ categories with placeholder images
- **RAG Pipeline**: Ingests brand info, reviews, and customer tickets into vector store
- **Conversational Search**: Personal shopper experience with intelligent follow-up questions
- **Business Logic Ranking**: Products ranked by margin while meeting user needs
- **Answer Generator**: Handles both recommendations and informational queries with RAG citations

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js (TypeScript/React)
- **LLM**: Ollama (local)
- **Vector Store**: ChromaDB
- **Database**: SQLite (for products)
- **Embeddings**: sentence-transformers

## Prerequisites

1. **Ollama Installation**:
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull required model
   ollama pull llama3.1:8b
   ```

2. **Python 3.8+** and **Node.js 18+**

## One-Command Setup

```bash
git clone <your-repo-url>
cd conversational-store
chmod +x setup.sh
./setup.sh
```

## Manual Setup

### Backend Setup

1. **Create Python environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Initialize Database and RAG**:
   ```bash
   python init_data.py
   ```

4. **Start Backend**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Frontend Setup

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Environment Variables**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local if needed
   ```

3. **Start Frontend**:
   ```bash
   npm run dev
   ```

## Usage

1. **Access the application**: http://localhost:3000
2. **Browse products** in the storefront
3. **Use conversational search**:
   - Type specific keywords (e.g., "serums") for targeted results
   - Use vague queries (e.g., "something gentle for summer") for guided discovery
4. **Ask questions** about products for detailed information with citations

## Project Structure

```
conversational-store/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   ├── data/                # Product and RAG data
│   ├── init_data.py         # Database initialization
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Next.js pages
│   │   └── types/           # TypeScript types
│   ├── package.json
│   └── next.config.js
├── setup.sh                 # One-command setup
└── README.md
```

## API Endpoints

- `GET /api/products` - Fetch all products
- `GET /api/categories` - Fetch product categories
- `POST /api/search` - Conversational search
- `POST /api/ask` - Question answering with RAG

## Design Decisions

1. **Local LLM**: Uses Ollama for privacy and cost efficiency
2. **Vector Store**: ChromaDB for lightweight, persistent vector storage
3. **Session Management**: Simple in-memory storage for conversation context
4. **Margin-Based Ranking**: Products sorted by profitability within relevant results
5. **Citation System**: RAG responses include source references from reviews/tickets

## Performance Considerations

- Vector embeddings cached for faster similarity search
- Product data optimized with proper indexing
- Conversation context limited to recent turns
- Minimal LLM calls through efficient prompt engineering

## Next Steps

1. **Production Deployment**: Docker containerization and cloud deployment
2. **Advanced RAG**: Implement re-ranking and hybrid search
3. **User Sessions**: Persistent user preferences and history
4. **Analytics**: Conversion tracking and search analytics
5. **A/B Testing**: Experiment with different conversation flows

## Troubleshooting

### Ollama Issues
- Ensure Ollama service is running: `ollama serve`
- Check model availability: `ollama list`
- Verify model pulling: `ollama pull llama3.1:8b`

### Port Conflicts
- Backend runs on port 8000
- Frontend runs on port 3000
- Modify ports in respective configuration files if needed

### Database Issues
- Delete `data/products.db` and re-run `python init_data.py`
- Check ChromaDB persistence directory permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details
