"""
DeepGram Speech-to-Text Service
Handles real-time speech recognition using DeepGram's API
"""

import asyncio
import json
import logging
from typing import Optional, AsyncGenerator
import websockets
from deepgram import Deepgram
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class DeepgramService:
    """Service for handling speech-to-text conversion using DeepGram"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")
        
        self.deepgram = Deepgram(self.api_key)
        self.connection = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Establish connection to DeepGram streaming API"""
        try:
            # DeepGram streaming configuration
            options = {
                "model": "nova-2",
                "language": "en-US",
                "encoding": "linear16",
                "sample_rate": 16000,
                "channels": 1,
                "interim_results": True,
                "punctuate": True,
                "smart_format": True,
                "utterance_end_ms": 1000,
                "vad_events": True
            }
            
            self.connection = self.deepgram.transcription.live(options)
            
            # Set up event handlers
            self.connection.registerHandler(
                self.connection.event.CLOSE, 
                self._on_close
            )
            self.connection.registerHandler(
                self.connection.event.ERROR, 
                self._on_error
            )
            
            self.is_connected = True
            logger.info("Connected to DeepGram streaming API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to DeepGram: {str(e)}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from DeepGram streaming API"""
        if self.connection:
            try:
                await self.connection.finish()
                self.is_connected = False
                logger.info("Disconnected from DeepGram")
            except Exception as e:
                logger.error(f"Error disconnecting from DeepGram: {str(e)}")
    
    async def transcribe_audio_chunk(self, audio_data: bytes) -> Optional[dict]:
        """
        Transcribe an audio chunk and return the result
        
        Args:
            audio_data: Raw audio bytes (16kHz, 16-bit, mono)
            
        Returns:
            Dictionary with transcription result or None if no speech detected
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            # Send audio data to DeepGram
            self.connection.send(audio_data)
            
            # Wait for transcription result
            # Note: In a real implementation, you'd handle this asynchronously
            # with callbacks or event handlers
            await asyncio.sleep(0.1)  # Small delay to allow processing
            
            # This is a simplified version - in practice, you'd handle
            # the response through event handlers
            return {
                "transcript": "",  # Will be populated by event handlers
                "confidence": 0.0,
                "is_final": False
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None
    
    async def transcribe_streaming(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[dict, None]:
        """
        Transcribe streaming audio data
        
        Args:
            audio_stream: Async generator yielding audio chunks
            
        Yields:
            Transcription results as they become available
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            async for audio_chunk in audio_stream:
                if audio_chunk:
                    self.connection.send(audio_chunk)
                    
                    # In a real implementation, transcription results would
                    # be handled by event handlers and yielded here
                    yield {
                        "transcript": "Sample transcription",
                        "confidence": 0.95,
                        "is_final": False,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    
        except Exception as e:
            logger.error(f"Error in streaming transcription: {str(e)}")
        finally:
            await self.disconnect()
    
    def _on_close(self, close_msg):
        """Handle connection close event"""
        logger.info("DeepGram connection closed")
        self.is_connected = False
    
    def _on_error(self, error_msg):
        """Handle connection error event"""
        logger.error(f"DeepGram connection error: {error_msg}")
        self.is_connected = False
    
    async def health_check(self) -> bool:
        """Check if DeepGram service is healthy"""
        try:
            # Simple health check - try to create a connection
            test_connection = self.deepgram.transcription.live({
                "model": "nova-2",
                "language": "en-US"
            })
            
            if test_connection:
                await test_connection.finish()
                return True
            return False
            
        except Exception as e:
            logger.error(f"DeepGram health check failed: {str(e)}")
            return False
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return [
            "en-US", "en-GB", "en-AU", "en-NZ", "en-IN",
            "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"
        ]
    
    def get_supported_models(self) -> list:
        """Get list of supported models"""
        return [
            "nova-2",      # Latest general model
            "nova",        # Previous general model  
            "enhanced",    # Enhanced model for better accuracy
            "base",        # Base model for faster processing
            "meeting",     # Optimized for meetings
            "phonecall",   # Optimized for phone calls
            "voicemail",   # Optimized for voicemail
            "finance",     # Domain-specific for finance
            "conversationalai"  # Optimized for conversational AI
        ]
