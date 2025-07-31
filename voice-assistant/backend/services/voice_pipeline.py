"""
Voice Processing Pipeline
Orchestrates the complete voice processing workflow:
Audio Input → Speech-to-Text → AI Processing → Text-to-Speech → Audio Output
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import time

from .deepgram_service import DeepgramService
from .elevenlabs_service import ElevenLabsService
from .groq_service import GroqService
from .rag_service import RAGService

logger = logging.getLogger(__name__)

@dataclass
class VoiceResponse:
    """Response from voice processing pipeline"""
    audio_data: Optional[bytes]
    transcript: str
    ai_response: str
    confidence: float
    processing_time: float
    session_id: str

class VoicePipeline:
    """Main voice processing pipeline that coordinates all AI services"""
    
    def __init__(self):
        # Initialize all services
        self.deepgram = DeepgramService()
        self.elevenlabs = ElevenLabsService()
        self.groq = GroqService()
        self.rag = RAGService()
        
        # Pipeline configuration
        self.min_confidence_threshold = 0.7
        self.max_processing_time = 5.0  # seconds
        self.enable_streaming = True
        
        # Session storage for conversation context
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def process_audio_chunk(self, audio_data: bytes, session_id: str) -> VoiceResponse:
        """
        Process a single audio chunk through the complete pipeline
        
        Args:
            audio_data: Raw audio bytes from client
            session_id: Unique session identifier
            
        Returns:
            VoiceResponse with processed audio and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Speech-to-Text with DeepGram
            logger.info(f"Processing audio chunk for session {session_id}")
            transcription_result = await self.deepgram.transcribe_audio_chunk(audio_data)
            
            if not transcription_result or not transcription_result.get("transcript"):
                logger.warning("No transcription received from DeepGram")
                return VoiceResponse(
                    audio_data=None,
                    transcript="",
                    ai_response="",
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    session_id=session_id
                )
            
            transcript = transcription_result["transcript"]
            confidence = transcription_result.get("confidence", 0.0)
            
            # Check confidence threshold
            if confidence < self.min_confidence_threshold:
                logger.warning(f"Low confidence transcription: {confidence}")
                return await self._generate_clarification_response(session_id, start_time)
            
            # Step 2: Get conversation context
            session_context = self._get_session_context(session_id)
            
            # Step 3: Retrieve relevant information using RAG
            rag_context = await self.rag.retrieve_context(
                query=transcript,
                user_id=session_context.get("user_id"),
                conversation_history=session_context.get("history", [])
            )
            
            # Step 4: Generate AI response with Groq
            ai_response = await self.groq.generate_response(
                user_message=transcript,
                context=rag_context,
                conversation_history=session_context.get("history", []),
                system_prompt=self._get_customer_service_prompt()
            )
            
            if not ai_response:
                logger.error("Failed to generate AI response")
                ai_response = "I apologize, but I'm having trouble processing your request right now. Could you please try again?"
            
            # Step 5: Optimize response for voice
            voice_optimized_response = self.groq.optimize_for_voice(ai_response)
            
            # Step 6: Convert to speech with ElevenLabs
            audio_response = await self.elevenlabs.text_to_speech(voice_optimized_response)
            
            # Step 7: Update session context
            self._update_session_context(session_id, transcript, ai_response)
            
            processing_time = time.time() - start_time
            logger.info(f"Pipeline completed in {processing_time:.2f}s for session {session_id}")
            
            return VoiceResponse(
                audio_data=audio_response,
                transcript=transcript,
                ai_response=ai_response,
                confidence=confidence,
                processing_time=processing_time,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Error in voice pipeline: {str(e)}")
            processing_time = time.time() - start_time
            
            # Generate error response
            error_response = "I'm sorry, I encountered a technical issue. Please try again or speak with a human agent."
            error_audio = await self.elevenlabs.text_to_speech(error_response)
            
            return VoiceResponse(
                audio_data=error_audio,
                transcript="",
                ai_response=error_response,
                confidence=0.0,
                processing_time=processing_time,
                session_id=session_id
            )
    
    async def process_streaming_audio(self, audio_stream, session_id: str):
        """
        Process streaming audio data
        
        Args:
            audio_stream: Async generator of audio chunks
            session_id: Unique session identifier
            
        Yields:
            VoiceResponse objects as they become available
        """
        try:
            # Process audio stream through DeepGram
            async for transcription in self.deepgram.transcribe_streaming(audio_stream):
                if transcription.get("is_final", False):
                    # Process final transcription through full pipeline
                    transcript = transcription["transcript"]
                    
                    # Create mock audio data for processing
                    # In real implementation, you'd buffer the actual audio
                    mock_audio = b"mock_audio_data"
                    
                    response = await self.process_audio_chunk(mock_audio, session_id)
                    yield response
                    
        except Exception as e:
            logger.error(f"Error in streaming pipeline: {str(e)}")
    
    def _get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context for a session"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "history": [],
                "user_id": None,
                "start_time": time.time(),
                "total_interactions": 0
            }
        return self.active_sessions[session_id]
    
    def _update_session_context(self, session_id: str, user_message: str, ai_response: str):
        """Update session context with new interaction"""
        context = self._get_session_context(session_id)
        
        # Add to conversation history
        context["history"].extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ])
        
        # Keep only last 20 messages to manage memory
        if len(context["history"]) > 20:
            context["history"] = context["history"][-20:]
        
        context["total_interactions"] += 1
        context["last_interaction"] = time.time()
    
    def _get_customer_service_prompt(self) -> str:
        """Get specialized customer service system prompt"""
        return """You are an expert AI customer service representative. Your goals are:

1. SOLVE PROBLEMS: Focus on resolving the customer's issue quickly and effectively
2. BE EMPATHETIC: Show understanding and care for customer concerns
3. STAY PROFESSIONAL: Maintain a helpful, courteous tone at all times
4. BE CONCISE: Keep responses brief but complete - this is a voice conversation
5. USE CONTEXT: Leverage provided information to give personalized responses
6. ESCALATE WHEN NEEDED: If you can't help, offer to connect with a human agent

Voice Conversation Guidelines:
- Speak naturally and conversationally
- Use short, clear sentences
- Avoid technical jargon unless necessary
- Confirm understanding when handling complex requests
- Express empathy for frustrations or problems

Remember: The customer called for help. Your job is to provide excellent service and leave them satisfied with their experience."""
    
    async def _generate_clarification_response(self, session_id: str, start_time: float) -> VoiceResponse:
        """Generate a response asking for clarification"""
        clarification_text = "I'm sorry, I didn't catch that clearly. Could you please repeat your question?"
        clarification_audio = await self.elevenlabs.text_to_speech(clarification_text)
        
        return VoiceResponse(
            audio_data=clarification_audio,
            transcript="",
            ai_response=clarification_text,
            confidence=0.0,
            processing_time=time.time() - start_time,
            session_id=session_id
        )
    
    async def check_deepgram_health(self) -> bool:
        """Check DeepGram service health"""
        return await self.deepgram.health_check()
    
    async def check_elevenlabs_health(self) -> bool:
        """Check ElevenLabs service health"""
        return await self.elevenlabs.health_check()
    
    async def check_groq_health(self) -> bool:
        """Check Groq service health"""
        return await self.groq.health_check()
    
    async def check_rag_health(self) -> bool:
        """Check RAG service health"""
        return await self.rag.health_check()
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get overall pipeline status and metrics"""
        return {
            "active_sessions": len(self.active_sessions),
            "services": {
                "deepgram": await self.check_deepgram_health(),
                "elevenlabs": await self.check_elevenlabs_health(),
                "groq": await self.check_groq_health(),
                "rag": await self.check_rag_health()
            },
            "configuration": {
                "min_confidence_threshold": self.min_confidence_threshold,
                "max_processing_time": self.max_processing_time,
                "streaming_enabled": self.enable_streaming
            }
        }
    
    async def update_knowledge_base(self):
        """Update the RAG knowledge base"""
        await self.rag.update_knowledge_base()
        logger.info("Knowledge base updated successfully")
    
    def cleanup_session(self, session_id: str):
        """Clean up session data"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Cleaned up session {session_id}")
    
    async def get_session_analytics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get analytics for a specific session"""
        if session_id not in self.active_sessions:
            return None
        
        context = self.active_sessions[session_id]
        current_time = time.time()
        
        return {
            "session_id": session_id,
            "duration": current_time - context["start_time"],
            "total_interactions": context["total_interactions"],
            "last_interaction": context.get("last_interaction", context["start_time"]),
            "conversation_length": len(context["history"]),
            "user_id": context.get("user_id")
        }
