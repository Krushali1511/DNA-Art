"""
ElevenLabs Text-to-Speech Service
Handles AI voice synthesis using ElevenLabs API
"""

import asyncio
import logging
from typing import Optional, AsyncGenerator
import httpx
from elevenlabs import generate, Voice, VoiceSettings
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv
import io

load_dotenv()
logger = logging.getLogger(__name__)

class ElevenLabsService:
    """Service for handling text-to-speech conversion using ElevenLabs"""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required")
        
        self.client = ElevenLabs(api_key=self.api_key)
        self.default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        self.voice_settings = VoiceSettings(
            stability=0.75,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
        
    async def text_to_speech(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """
        Convert text to speech audio
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID to use (defaults to Rachel)
            
        Returns:
            Audio bytes in MP3 format or None if conversion failed
        """
        try:
            voice_id = voice_id or self.default_voice_id
            
            # Generate speech using ElevenLabs
            audio = generate(
                text=text,
                voice=Voice(
                    voice_id=voice_id,
                    settings=self.voice_settings
                ),
                model="eleven_multilingual_v2"
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join(audio)
            
            logger.info(f"Generated speech for text: '{text[:50]}...'")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    async def text_to_speech_streaming(self, text: str, voice_id: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        """
        Convert text to speech with streaming audio output
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID to use
            
        Yields:
            Audio chunks as they become available
        """
        try:
            voice_id = voice_id or self.default_voice_id
            
            # Use ElevenLabs streaming API
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": self.voice_settings.stability,
                    "similarity_boost": self.voice_settings.similarity_boost,
                    "style": self.voice_settings.style,
                    "use_speaker_boost": self.voice_settings.use_speaker_boost
                }
            }
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, headers=headers, json=data) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes(chunk_size=1024):
                            if chunk:
                                yield chunk
                    else:
                        logger.error(f"ElevenLabs API error: {response.status_code}")
                        
        except Exception as e:
            logger.error(f"Error in streaming TTS: {str(e)}")
    
    async def get_available_voices(self) -> list:
        """Get list of available voices"""
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category,
                    "description": voice.description,
                    "preview_url": voice.preview_url,
                    "available_for_tiers": voice.available_for_tiers,
                    "settings": {
                        "stability": voice.settings.stability if voice.settings else 0.75,
                        "similarity_boost": voice.settings.similarity_boost if voice.settings else 0.75,
                        "style": voice.settings.style if voice.settings else 0.0,
                        "use_speaker_boost": voice.settings.use_speaker_boost if voice.settings else True
                    }
                }
                for voice in voices.voices
            ]
        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}")
            return []
    
    async def clone_voice(self, name: str, description: str, files: list) -> Optional[str]:
        """
        Clone a voice from audio samples
        
        Args:
            name: Name for the cloned voice
            description: Description of the voice
            files: List of audio file paths for voice cloning
            
        Returns:
            Voice ID of the cloned voice or None if failed
        """
        try:
            # This would require implementing voice cloning
            # For now, return None as it's an advanced feature
            logger.info(f"Voice cloning requested for: {name}")
            return None
            
        except Exception as e:
            logger.error(f"Error cloning voice: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """Check if ElevenLabs service is healthy"""
        try:
            # Simple health check - try to get voices
            voices = await self.get_available_voices()
            return len(voices) > 0
            
        except Exception as e:
            logger.error(f"ElevenLabs health check failed: {str(e)}")
            return False
    
    def get_recommended_voices(self) -> dict:
        """Get recommended voices for different use cases"""
        return {
            "customer_service": {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "name": "Rachel",
                "description": "Professional, friendly female voice ideal for customer service"
            },
            "professional_male": {
                "voice_id": "29vD33N1CtxCmqQRPOHJ",  # Drew
                "name": "Drew", 
                "description": "Professional male voice with clear articulation"
            },
            "warm_female": {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Bella
                "name": "Bella",
                "description": "Warm, empathetic female voice"
            },
            "authoritative": {
                "voice_id": "VR6AewLTigWG4xSOukaG",  # Arnold
                "name": "Arnold",
                "description": "Authoritative male voice for important announcements"
            }
        }
    
    def optimize_for_streaming(self, text: str) -> list:
        """
        Split text into optimal chunks for streaming TTS
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks optimized for streaming
        """
        # Split on sentence boundaries for natural pauses
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add sentence to current chunk
            test_chunk = current_chunk + sentence + ". "
            
            # If chunk is getting too long, start a new one
            if len(test_chunk) > 200:  # Optimal chunk size for streaming
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                current_chunk = test_chunk
        
        # Add remaining text
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def get_character_count(self) -> dict:
        """Get current character usage and limits"""
        try:
            # This would require implementing usage tracking
            # For now, return mock data
            return {
                "character_count": 0,
                "character_limit": 10000,
                "can_extend": True,
                "next_reset_unix": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting character count: {str(e)}")
            return {
                "character_count": 0,
                "character_limit": 10000,
                "can_extend": False,
                "next_reset_unix": 0
            }
