#!/bin/bash

# Conversational Store Setup Script
echo "🚀 Setting up Conversational Store..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required files exist
check_files() {
    print_status "Checking for required data files..."
    
    if [ ! -f "./skincare_catalog.xlsx" ]; then
        print_error "skincare_catalogue.xlsx not found in current directory"
        print_warning "Please place the Excel file in the project root"
        exit 1
    fi
    
    if [ ! -f "./Additional_info.docx" ]; then
        print_error "Additional_info.doc not found in current directory"
        print_warning "Please place the Word document in the project root"
        exit 1
    fi
    
    print_success "Data files found"
}

# Check Ollama installation
check_ollama() {
    print_status "Checking Ollama installation..."
    
    if ! command -v ollama &> /dev/null; then
        print_error "Ollama is not installed"
        print_warning "Please install Ollama: curl -fsSL https://ollama.ai/install.sh | sh"
        exit 1
    fi
    
    print_success "Ollama found"
    
    # Check if model is available
    print_status "Checking for Llama model..."
    if ! ollama list | grep -q "llama3.1:8b "; then
        print_warning "llama3.1:8b model not found. Pulling now..."
        ollama pull llama3.1:8b
        if [ $? -eq 0 ]; then
            print_success "Model pulled successfully"
        else
            print_error "Failed to pull model"
            exit 1
        fi
    else
        print_success "llama3.1:8b model found"
    fi
}

# Start Ollama service
start_ollama() {
    print_status "Starting Ollama service..."
    
    # Check if Ollama is already running
    if pgrep -x "ollama" > /dev/null; then
        print_success "Ollama is already running"
    else
        # Start Ollama in background
        ollama serve &
        sleep 3
        
        if pgrep -x "ollama" > /dev/null; then
            print_success "Ollama service started"
        else
            print_error "Failed to start Ollama service"
            exit 1
        fi
    fi
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_success "Backend dependencies installed"
    else
        print_error "Failed to install backend dependencies"
        exit 1
    fi
    
    # Copy data files to backend directory
    cp ../skincare_catalog.xlsx .
    cp ../Additional_info.docx .
    
    # Initialize database and RAG
    print_status "Initializing database and RAG system..."
    python init_data.py
    
    if [ $? -eq 0 ]; then
        print_success "Database and RAG initialized"
    else
        print_error "Failed to initialize data"
        exit 1
    fi
    
    cd ..
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    if [ $? -eq 0 ]; then
        print_success "Frontend dependencies installed"
    else
        print_error "Failed to install frontend dependencies"
        exit 1
    fi
    
    # Create environment file
    if [ ! -f ".env.local" ]; then
        cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8001
EOF
        print_success "Frontend environment file created"
    fi
    
    cd ..
}

# Start services
start_services() {
    print_status "Starting services..."
    
    # Start backend in background
    cd backend
    source venv/bin/activate
    nohup uvicorn main:app --reload --port 8001 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    # Wait a moment for backend to start
    sleep 3
    
    # Check if backend is running
    if kill -0 $BACKEND_PID 2>/dev/null; then
        print_success "Backend started (PID: $BACKEND_PID)"
    else
        print_error "Failed to start backend"
        echo "📄 Showing backend.log output:"
        tail -n 30 ./backend.log
        exit 1
    fi
    
    # Start frontend in background
    cd frontend
    nohup npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # Wait a moment for frontend to start
    sleep 5
    
    # Check if frontend is running
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        print_success "Frontend started (PID: $FRONTEND_PID)"
    else
        print_error "Failed to start frontend"
        exit 1
    fi
    
    # Save PIDs for cleanup
    echo $BACKEND_PID > backend.pid
    echo $FRONTEND_PID > frontend.pid
}

# Main setup flow
main() {
    echo "════════════════════════════════════════"
    echo "   Conversational Store Setup"
    echo "════════════════════════════════════════"
    echo
    
    # Check prerequisites
    check_files
    check_ollama
    start_ollama
    
    # Setup components
    setup_backend
    setup_frontend
    
    # Start services
    start_services
    
    echo
    echo "════════════════════════════════════════"
    echo "✅ Setup Complete!"
    echo "════════════════════════════════════════"
    echo
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 Backend API: http://localhost:8001"
    echo "📊 API Docs: http://localhost:8001/docs"
    echo
    echo "📝 Logs:"
    echo "   Backend: tail -f backend.log"
    echo "   Frontend: tail -f frontend.log"
    echo
    echo "🛑 To stop services:"
    echo "   kill \$(cat backend.pid frontend.pid)"
    echo
    print_success "Your conversational store is ready!"
}

# Run main function
main