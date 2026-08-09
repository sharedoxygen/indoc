"""
Simplified main application for testing
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(
    title="inDoc API",
    description="Document Intelligence Platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to inDoc API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/v1/health")
async def api_health():
    return {"status": "healthy", "version": "1.0.0"}