"""
Analytics Service
Handles call analytics, metrics collection, and reporting for the admin dashboard
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import re

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for collecting and analyzing voice assistant usage data"""
    
    def __init__(self):
        # In-memory storage for analytics (in production, use a proper database)
        self.call_logs: List[Dict[str, Any]] = []
        self.interaction_logs: List[Dict[str, Any]] = []
        self.error_logs: List[Dict[str, Any]] = []
        self.performance_metrics: List[Dict[str, Any]] = []
        
        # Common questions tracking
        self.question_patterns = {}
        self.intent_categories = defaultdict(int)
        
    async def save_call_data(self, session) -> None:
        """Save call session data for analytics"""
        try:
            call_data = {
                "session_id": session.id,
                "client_id": session.client_id,
                "user_id": session.user_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else datetime.now().isoformat(),
                "duration": session.get_duration(),
                "total_interactions": session.total_interactions,
                "status": session.status,
                "conversation_history": session.conversation_history,
                "metadata": session.metadata
            }
            
            self.call_logs.append(call_data)
            
            # Process interactions for analytics
            await self._process_interactions(session.conversation_history, session.id)
            
            logger.info(f"Saved call data for session {session.id}")
            
        except Exception as e:
            logger.error(f"Error saving call data: {str(e)}")
    
    async def _process_interactions(self, conversation_history: List[Dict[str, str]], session_id: str):
        """Process conversation interactions for analytics"""
        try:
            for interaction in conversation_history:
                if interaction["role"] == "user":
                    # Extract and categorize user questions
                    question = interaction["content"].lower().strip()
                    
                    # Store interaction
                    interaction_data = {
                        "session_id": session_id,
                        "timestamp": interaction.get("timestamp", datetime.now().isoformat()),
                        "user_message": question,
                        "confidence": interaction.get("confidence", 1.0),
                        "intent": self._classify_intent(question),
                        "question_category": self._categorize_question(question)
                    }
                    
                    self.interaction_logs.append(interaction_data)
                    
                    # Update question patterns
                    self._update_question_patterns(question)
                    
        except Exception as e:
            logger.error(f"Error processing interactions: {str(e)}")
    
    def _classify_intent(self, message: str) -> str:
        """Classify user intent based on message content"""
        message = message.lower()
        
        # Define intent patterns
        intent_patterns = {
            "billing_inquiry": ["bill", "charge", "payment", "invoice", "cost", "price", "fee"],
            "technical_support": ["not working", "error", "problem", "issue", "broken", "fix", "help"],
            "account_access": ["login", "password", "account", "access", "locked", "reset"],
            "product_information": ["what is", "how does", "features", "benefits", "compare"],
            "cancellation": ["cancel", "unsubscribe", "terminate", "end", "stop"],
            "complaint": ["angry", "frustrated", "disappointed", "terrible", "awful", "bad"],
            "compliment": ["great", "excellent", "amazing", "wonderful", "love", "perfect"],
            "general_question": ["question", "ask", "wondering", "curious", "information"]
        }
        
        # Score each intent
        intent_scores = {}
        for intent, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message)
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent or default
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        else:
            return "general_question"
    
    def _categorize_question(self, question: str) -> str:
        """Categorize questions into broad categories"""
        question = question.lower()
        
        categories = {
            "account_management": ["account", "profile", "settings", "personal"],
            "billing_payment": ["bill", "payment", "charge", "invoice", "cost"],
            "technical_issues": ["error", "problem", "not working", "broken", "issue"],
            "product_features": ["feature", "how to", "what is", "can i", "does it"],
            "service_inquiry": ["service", "support", "help", "assistance"],
            "other": []  # Default category
        }
        
        for category, keywords in categories.items():
            if any(keyword in question for keyword in keywords):
                return category
        
        return "other"
    
    def _update_question_patterns(self, question: str):
        """Update common question patterns"""
        # Normalize question
        normalized = re.sub(r'[^\w\s]', '', question.lower())
        words = normalized.split()
        
        # Create patterns from question
        if len(words) >= 3:
            # Use first 3 words as pattern
            pattern = ' '.join(words[:3])
            self.question_patterns[pattern] = self.question_patterns.get(pattern, 0) + 1
    
    async def get_call_analytics(self) -> Dict[str, Any]:
        """Get comprehensive call analytics"""
        try:
            if not self.call_logs:
                return self._get_empty_analytics()
            
            # Calculate time-based metrics
            now = datetime.now()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Filter calls by time periods
            today_calls = [call for call in self.call_logs 
                          if datetime.fromisoformat(call["start_time"]).date() == today]
            
            week_calls = [call for call in self.call_logs 
                         if datetime.fromisoformat(call["start_time"]) >= week_ago]
            
            month_calls = [call for call in self.call_logs 
                          if datetime.fromisoformat(call["start_time"]) >= month_ago]
            
            # Calculate metrics
            total_calls = len(self.call_logs)
            avg_duration = sum(call["duration"] for call in self.call_logs) / total_calls if total_calls > 0 else 0
            avg_interactions = sum(call["total_interactions"] for call in self.call_logs) / total_calls if total_calls > 0 else 0
            
            # Success rate (calls that ended normally vs errors)
            successful_calls = len([call for call in self.call_logs if call["status"] == "ended"])
            success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
            
            # Peak hours analysis
            hour_distribution = defaultdict(int)
            for call in self.call_logs:
                hour = datetime.fromisoformat(call["start_time"]).hour
                hour_distribution[hour] += 1
            
            peak_hour = max(hour_distribution, key=hour_distribution.get) if hour_distribution else 0
            
            return {
                "overview": {
                    "total_calls": total_calls,
                    "calls_today": len(today_calls),
                    "calls_this_week": len(week_calls),
                    "calls_this_month": len(month_calls),
                    "average_duration": round(avg_duration, 2),
                    "average_interactions": round(avg_interactions, 2),
                    "success_rate": round(success_rate, 2),
                    "peak_hour": peak_hour
                },
                "trends": {
                    "daily_calls": self._get_daily_call_trend(),
                    "hourly_distribution": dict(hour_distribution),
                    "duration_trend": self._get_duration_trend(),
                    "interaction_trend": self._get_interaction_trend()
                },
                "performance": {
                    "average_response_time": self._get_average_response_time(),
                    "error_rate": self._get_error_rate(),
                    "user_satisfaction": self._estimate_user_satisfaction()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting call analytics: {str(e)}")
            return self._get_empty_analytics()
    
    async def get_common_questions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common questions asked"""
        try:
            if not self.interaction_logs:
                return []
            
            # Count question patterns
            pattern_counts = Counter(self.question_patterns)
            
            # Count intent categories
            intent_counts = Counter([log["intent"] for log in self.interaction_logs])
            
            # Count question categories
            category_counts = Counter([log["question_category"] for log in self.interaction_logs])
            
            # Get most common patterns
            common_patterns = []
            for pattern, count in pattern_counts.most_common(limit):
                # Find example questions for this pattern
                examples = [
                    log["user_message"] for log in self.interaction_logs 
                    if pattern in log["user_message"].lower()
                ][:3]  # Get up to 3 examples
                
                common_patterns.append({
                    "pattern": pattern,
                    "count": count,
                    "percentage": round((count / len(self.interaction_logs)) * 100, 2),
                    "examples": examples
                })
            
            return {
                "common_patterns": common_patterns,
                "intent_distribution": dict(intent_counts.most_common()),
                "category_distribution": dict(category_counts.most_common()),
                "total_questions": len(self.interaction_logs)
            }
            
        except Exception as e:
            logger.error(f"Error getting common questions: {str(e)}")
            return []
    
    def _get_empty_analytics(self) -> Dict[str, Any]:
        """Return empty analytics structure"""
        return {
            "overview": {
                "total_calls": 0,
                "calls_today": 0,
                "calls_this_week": 0,
                "calls_this_month": 0,
                "average_duration": 0,
                "average_interactions": 0,
                "success_rate": 0,
                "peak_hour": 0
            },
            "trends": {
                "daily_calls": [],
                "hourly_distribution": {},
                "duration_trend": [],
                "interaction_trend": []
            },
            "performance": {
                "average_response_time": 0,
                "error_rate": 0,
                "user_satisfaction": 0
            }
        }
    
    def _get_daily_call_trend(self) -> List[Dict[str, Any]]:
        """Get daily call trend for the last 30 days"""
        daily_counts = defaultdict(int)
        
        for call in self.call_logs:
            date = datetime.fromisoformat(call["start_time"]).date()
            daily_counts[date] += 1
        
        # Create trend data for last 30 days
        trend_data = []
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            trend_data.append({
                "date": date.isoformat(),
                "calls": daily_counts.get(date, 0)
            })
        
        return list(reversed(trend_data))
    
    def _get_duration_trend(self) -> List[Dict[str, Any]]:
        """Get average call duration trend"""
        daily_durations = defaultdict(list)
        
        for call in self.call_logs:
            date = datetime.fromisoformat(call["start_time"]).date()
            daily_durations[date].append(call["duration"])
        
        trend_data = []
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            durations = daily_durations.get(date, [])
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            trend_data.append({
                "date": date.isoformat(),
                "average_duration": round(avg_duration, 2)
            })
        
        return list(reversed(trend_data))
    
    def _get_interaction_trend(self) -> List[Dict[str, Any]]:
        """Get average interactions per call trend"""
        daily_interactions = defaultdict(list)
        
        for call in self.call_logs:
            date = datetime.fromisoformat(call["start_time"]).date()
            daily_interactions[date].append(call["total_interactions"])
        
        trend_data = []
        for i in range(30):
            date = datetime.now().date() - timedelta(days=i)
            interactions = daily_interactions.get(date, [])
            avg_interactions = sum(interactions) / len(interactions) if interactions else 0
            
            trend_data.append({
                "date": date.isoformat(),
                "average_interactions": round(avg_interactions, 2)
            })
        
        return list(reversed(trend_data))
    
    def _get_average_response_time(self) -> float:
        """Calculate average response time (mock implementation)"""
        # In a real implementation, you'd track actual response times
        return 1.2  # Mock: 1.2 seconds average response time
    
    def _get_error_rate(self) -> float:
        """Calculate error rate"""
        if not self.call_logs:
            return 0.0
        
        error_calls = len([call for call in self.call_logs if call["status"] == "error"])
        return round((error_calls / len(self.call_logs)) * 100, 2)
    
    def _estimate_user_satisfaction(self) -> float:
        """Estimate user satisfaction based on conversation patterns"""
        if not self.interaction_logs:
            return 0.0
        
        # Simple heuristic: longer conversations with more interactions = higher satisfaction
        # In reality, you'd use sentiment analysis and explicit feedback
        
        positive_indicators = 0
        negative_indicators = 0
        
        for log in self.interaction_logs:
            message = log["user_message"].lower()
            
            # Positive indicators
            if any(word in message for word in ["thank", "great", "good", "helpful", "perfect"]):
                positive_indicators += 1
            
            # Negative indicators  
            if any(word in message for word in ["bad", "terrible", "awful", "frustrated", "angry"]):
                negative_indicators += 1
        
        total_indicators = positive_indicators + negative_indicators
        if total_indicators == 0:
            return 75.0  # Default neutral satisfaction
        
        satisfaction = (positive_indicators / total_indicators) * 100
        return round(satisfaction, 2)
    
    async def log_error(self, error_type: str, error_message: str, session_id: Optional[str] = None):
        """Log an error for analytics"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "session_id": session_id
        }
        
        self.error_logs.append(error_data)
        logger.info(f"Logged error: {error_type}")
    
    async def get_error_analytics(self) -> Dict[str, Any]:
        """Get error analytics"""
        if not self.error_logs:
            return {"total_errors": 0, "error_types": {}, "recent_errors": []}
        
        error_types = Counter([error["error_type"] for error in self.error_logs])
        recent_errors = sorted(self.error_logs, key=lambda x: x["timestamp"], reverse=True)[:10]
        
        return {
            "total_errors": len(self.error_logs),
            "error_types": dict(error_types),
            "recent_errors": recent_errors
        }
