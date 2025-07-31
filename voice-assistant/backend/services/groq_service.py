"""
Groq AI Service
Handles fast AI inference for generating responses using Groq's API
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from groq import Groq
import os
from dotenv import load_dotenv
import json

load_dotenv()
logger = logging.getLogger(__name__)

class GroqService:
    """Service for handling AI inference using Groq"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = Groq(api_key=self.api_key)
        self.default_model = "mixtral-8x7b-32768"  # Fast, high-quality model
        self.max_tokens = 1024
        self.temperature = 0.7
        
    async def generate_response(
        self, 
        user_message: str, 
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate AI response to user message
        
        Args:
            user_message: The user's input message
            context: Additional context from RAG system
            conversation_history: Previous conversation messages
            system_prompt: Custom system prompt
            
        Returns:
            AI-generated response or None if generation failed
        """
        try:
            # Build conversation messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({
                    "role": "system", 
                    "content": self._get_default_system_prompt()
                })
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Keep last 10 messages
            
            # Add context if available
            if context:
                context_message = f"Relevant information: {context}\n\nUser question: {user_message}"
                messages.append({"role": "user", "content": context_message})
            else:
                messages.append({"role": "user", "content": user_message})
            
            # Generate response using Groq
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            
            if response.choices and len(response.choices) > 0:
                ai_response = response.choices[0].message.content
                logger.info(f"Generated response for: '{user_message[:50]}...'")
                return ai_response
            else:
                logger.warning("No response generated from Groq")
                return None
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None
    
    async def generate_streaming_response(
        self,
        user_message: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Generate streaming AI response
        
        Args:
            user_message: The user's input message
            context: Additional context from RAG system
            conversation_history: Previous conversation messages
            system_prompt: Custom system prompt
            
        Yields:
            Response chunks as they become available
        """
        try:
            # Build conversation messages (same as above)
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({
                    "role": "system", 
                    "content": self._get_default_system_prompt()
                })
            
            if conversation_history:
                messages.extend(conversation_history[-10:])
            
            if context:
                context_message = f"Relevant information: {context}\n\nUser question: {user_message}"
                messages.append({"role": "user", "content": context_message})
            else:
                messages.append({"role": "user", "content": user_message})
            
            # Generate streaming response
            stream = self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield f"I apologize, but I'm experiencing technical difficulties. Please try again."
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for customer service"""
        return """You are a helpful AI customer service assistant. Your role is to:

1. Provide accurate, helpful information about customer accounts and services
2. Be professional, friendly, and empathetic in all interactions
3. Keep responses concise but complete - aim for 1-3 sentences
4. If you don't know something, admit it and offer to connect them with a human agent
5. Always prioritize customer satisfaction and problem resolution
6. Use the provided context information to give accurate, personalized responses
7. Maintain a conversational tone suitable for voice interactions

Guidelines:
- Be conversational and natural (this is a voice conversation)
- Avoid overly long responses that would be difficult to listen to
- Use simple, clear language
- Show empathy for customer concerns
- Offer specific next steps when possible
- If handling sensitive information, remind customers about privacy and security

Remember: You're speaking to customers, not writing to them. Keep it natural and conversational."""
    
    async def analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Analyze user intent and extract key information
        
        Args:
            user_message: The user's message to analyze
            
        Returns:
            Dictionary with intent analysis results
        """
        try:
            intent_prompt = f"""Analyze the following customer message and extract:
1. Primary intent (e.g., billing_inquiry, technical_support, account_access, general_question)
2. Urgency level (low, medium, high, critical)
3. Key entities mentioned (account numbers, product names, dates, etc.)
4. Sentiment (positive, neutral, negative, frustrated)
5. Requires human agent (true/false)

Customer message: "{user_message}"

Respond in JSON format only."""

            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "You are an intent analysis system. Respond only with valid JSON."},
                    {"role": "user", "content": intent_prompt}
                ],
                max_tokens=256,
                temperature=0.1
            )
            
            if response.choices and len(response.choices) > 0:
                try:
                    result = json.loads(response.choices[0].message.content)
                    return result
                except json.JSONDecodeError:
                    logger.warning("Failed to parse intent analysis JSON")
                    return self._get_default_intent()
            else:
                return self._get_default_intent()
                
        except Exception as e:
            logger.error(f"Error analyzing intent: {str(e)}")
            return self._get_default_intent()
    
    def _get_default_intent(self) -> Dict[str, Any]:
        """Get default intent analysis when parsing fails"""
        return {
            "primary_intent": "general_question",
            "urgency_level": "medium",
            "key_entities": [],
            "sentiment": "neutral",
            "requires_human_agent": False
        }
    
    async def health_check(self) -> bool:
        """Check if Groq service is healthy"""
        try:
            # Simple health check - try to generate a short response
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            return response.choices and len(response.choices) > 0
            
        except Exception as e:
            logger.error(f"Groq health check failed: {str(e)}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Groq models"""
        return [
            "mixtral-8x7b-32768",      # Balanced performance and quality
            "llama2-70b-4096",        # High quality, slower
            "gemma-7b-it",            # Fast, good for simple tasks
            "llama3-8b-8192",         # Latest Llama model
            "llama3-70b-8192"         # Highest quality Llama model
        ]
    
    def optimize_for_voice(self, text: str) -> str:
        """
        Optimize text response for voice output
        
        Args:
            text: Text to optimize
            
        Returns:
            Voice-optimized text
        """
        # Remove markdown formatting
        text = text.replace("**", "").replace("*", "").replace("_", "")
        
        # Replace common abbreviations with full words
        replacements = {
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "and so on",
            "&": "and",
            "@": "at",
            "#": "number",
            "%": "percent",
            "$": "dollars"
        }
        
        for abbrev, full in replacements.items():
            text = text.replace(abbrev, full)
        
        # Add natural pauses
        text = text.replace(". ", ". ... ")
        text = text.replace("? ", "? ... ")
        text = text.replace("! ", "! ... ")
        
        return text
    
    async def generate_follow_up_questions(self, conversation_context: str) -> List[str]:
        """
        Generate relevant follow-up questions based on conversation context
        
        Args:
            conversation_context: Recent conversation history
            
        Returns:
            List of suggested follow-up questions
        """
        try:
            prompt = f"""Based on this customer service conversation, suggest 3 relevant follow-up questions the customer might ask:

Conversation context: {conversation_context}

Provide 3 short, natural questions that would logically follow from this conversation. Format as a simple list."""

            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "Generate helpful follow-up questions for customer service."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.8
            )
            
            if response.choices and len(response.choices) > 0:
                questions_text = response.choices[0].message.content
                # Parse questions from response
                questions = [q.strip() for q in questions_text.split('\n') if q.strip() and not q.strip().startswith('-')]
                return questions[:3]  # Return max 3 questions
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            return []
