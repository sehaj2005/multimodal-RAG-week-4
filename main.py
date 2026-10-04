import logging
import os
from services.config import BASE_DIR
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import Base, engine
from db import models

from routers.auth import router as auth_router
from routers.rooms import router as rooms_router
from routers.chat import router as chat_router
from routers.upload import router as upload_router
from routers.files import router as files_router


# Create database tables
Base.metadata.create_all(bind=engine)


# Create FastAPI application
app = FastAPI(
    title="Multimodal RAG API",
    version="1.0.0"
)


# Allow Streamlit frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(files_router)


# Health check
@app.get("/")
def home():
    return {
        "message": "Multimodal RAG API is running"
    }
