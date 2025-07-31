"""
AI Voice Assistant Backend
FastAPI application with WebSocket support for real-time voice communication
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import logging
from typing import Dict, List
import os
from dotenv import load_dotenv

from services.voice_pipeline import VoicePipeline
from services.analytics_service import AnalyticsService
from database.database import init_db
from models.conversation import ConversationManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Voice Assistant API",
    description="Backend API for AI-powered voice customer service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
voice_pipeline = VoicePipeline()
analytics_service = AnalyticsService()
conversation_manager = ConversationManager()

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    await init_db()
    logger.info("AI Voice Assistant backend started successfully")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AI Voice Assistant API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "deepgram": await voice_pipeline.check_deepgram_health(),
            "elevenlabs": await voice_pipeline.check_elevenlabs_health(),
            "groq": await voice_pipeline.check_groq_health(),
            "database": True  # TODO: Add actual DB health check
        }
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time voice communication"""
    await websocket.accept()
    active_connections[client_id] = websocket
    
    logger.info(f"Client {client_id} connected")
    
    try:
        # Initialize conversation session
        session = await conversation_manager.create_session(client_id)
        
        while True:
            # Receive audio data or control messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "audio_chunk":
                # Process audio chunk through voice pipeline
                response = await voice_pipeline.process_audio_chunk(
                    audio_data=message["data"],
                    session_id=session.id
                )
                
                # Send response back to client
                await websocket.send_text(json.dumps({
                    "type": "ai_response",
                    "audio_data": response.audio_data,
                    "transcript": response.transcript,
                    "confidence": response.confidence
                }))
                
            elif message["type"] == "start_call":
                # Start new call session
                await websocket.send_text(json.dumps({
                    "type": "call_started",
                    "session_id": session.id,
                    "message": "Hello! I'm your AI assistant. How can I help you today?"
                }))
                
            elif message["type"] == "end_call":
                # End call and save analytics
                await analytics_service.save_call_data(session)
                await websocket.send_text(json.dumps({
                    "type": "call_ended",
                    "message": "Thank you for calling. Have a great day!"
                }))
                break
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for {client_id}: {str(e)}")
    finally:
        # Clean up connection
        if client_id in active_connections:
            del active_connections[client_id]
        await conversation_manager.end_session(client_id)

@app.get("/api/analytics/calls")
async def get_call_analytics():
    """Get call analytics for admin dashboard"""
    try:
        analytics = await analytics_service.get_call_analytics()
        return analytics
    except Exception as e:
        logger.error(f"Error fetching call analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")

@app.get("/api/analytics/common-questions")
async def get_common_questions():
    """Get most common questions asked"""
    try:
        questions = await analytics_service.get_common_questions()
        return questions
    except Exception as e:
        logger.error(f"Error fetching common questions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch common questions")

@app.get("/api/active-calls")
async def get_active_calls():
    """Get number of currently active calls"""
    return {
        "active_calls": len(active_connections),
        "connections": list(active_connections.keys())
    }

@app.post("/api/knowledge-base/update")
async def update_knowledge_base():
    """Update the RAG knowledge base"""
    try:
        await voice_pipeline.update_knowledge_base()
        return {"message": "Knowledge base updated successfully"}
    except Exception as e:
        logger.error(f"Error updating knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge base")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
