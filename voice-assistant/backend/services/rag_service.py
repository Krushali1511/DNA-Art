"""
RAG (Retrieval-Augmented Generation) Service
Handles knowledge base retrieval for contextual AI responses
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class RAGService:
    """Service for retrieving relevant context using vector embeddings"""
    
    def __init__(self):
        # Initialize ChromaDB for vector storage
        self.chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory="./chroma_db"
        ))
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Collection names
        self.company_collection_name = "company_guidelines"
        self.user_collection_name = "user_information"
        self.faq_collection_name = "frequently_asked_questions"
        
        # Initialize collections
        self._initialize_collections()
        
    def _initialize_collections(self):
        """Initialize ChromaDB collections"""
        try:
            # Company guidelines collection
            self.company_collection = self.chroma_client.get_or_create_collection(
                name=self.company_collection_name,
                metadata={"description": "Company policies, procedures, and guidelines"}
            )
            
            # User information collection
            self.user_collection = self.chroma_client.get_or_create_collection(
                name=self.user_collection_name,
                metadata={"description": "User account information and history"}
            )
            
            # FAQ collection
            self.faq_collection = self.chroma_client.get_or_create_collection(
                name=self.faq_collection_name,
                metadata={"description": "Frequently asked questions and answers"}
            )
            
            logger.info("ChromaDB collections initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB collections: {str(e)}")
    
    async def retrieve_context(
        self, 
        query: str, 
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_results: int = 5
    ) -> str:
        """
        Retrieve relevant context for a user query
        
        Args:
            query: User's question or statement
            user_id: Optional user identifier for personalized results
            conversation_history: Recent conversation context
            max_results: Maximum number of results to retrieve
            
        Returns:
            Formatted context string for AI processing
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search across all collections
            contexts = []
            
            # 1. Search company guidelines
            company_results = self.company_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(max_results, 3)
            )
            
            if company_results['documents'] and company_results['documents'][0]:
                contexts.extend([
                    f"Company Policy: {doc}" 
                    for doc in company_results['documents'][0]
                ])
            
            # 2. Search FAQ
            faq_results = self.faq_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(max_results, 3)
            )
            
            if faq_results['documents'] and faq_results['documents'][0]:
                contexts.extend([
                    f"FAQ: {doc}" 
                    for doc in faq_results['documents'][0]
                ])
            
            # 3. Search user information (if user_id provided)
            if user_id:
                user_results = self.user_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(max_results, 2),
                    where={"user_id": user_id}
                )
                
                if user_results['documents'] and user_results['documents'][0]:
                    contexts.extend([
                        f"User Info: {doc}" 
                        for doc in user_results['documents'][0]
                    ])
            
            # Format and return context
            if contexts:
                formatted_context = "\n\n".join(contexts[:max_results])
                logger.info(f"Retrieved {len(contexts)} context items for query: '{query[:50]}...'")
                return formatted_context
            else:
                logger.info(f"No relevant context found for query: '{query[:50]}...'")
                return ""
                
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return ""
    
    async def add_company_guideline(self, content: str, title: str, category: str = "general"):
        """Add a company guideline to the knowledge base"""
        try:
            # Generate embedding
            embedding = self.embedding_model.encode([content]).tolist()[0]
            
            # Add to collection
            self.company_collection.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "title": title,
                    "category": category,
                    "type": "company_guideline"
                }],
                ids=[f"guideline_{len(self.company_collection.get()['ids'])}"]
            )
            
            logger.info(f"Added company guideline: {title}")
            
        except Exception as e:
            logger.error(f"Error adding company guideline: {str(e)}")
    
    async def add_faq_item(self, question: str, answer: str, category: str = "general"):
        """Add a FAQ item to the knowledge base"""
        try:
            # Combine question and answer for better retrieval
            content = f"Q: {question}\nA: {answer}"
            
            # Generate embedding
            embedding = self.embedding_model.encode([content]).tolist()[0]
            
            # Add to collection
            self.faq_collection.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "question": question,
                    "answer": answer,
                    "category": category,
                    "type": "faq"
                }],
                ids=[f"faq_{len(self.faq_collection.get()['ids'])}"]
            )
            
            logger.info(f"Added FAQ item: {question[:50]}...")
            
        except Exception as e:
            logger.error(f"Error adding FAQ item: {str(e)}")
    
    async def add_user_information(self, user_id: str, information: str, info_type: str = "general"):
        """Add user-specific information to the knowledge base"""
        try:
            # Generate embedding
            embedding = self.embedding_model.encode([information]).tolist()[0]
            
            # Add to collection
            self.user_collection.add(
                embeddings=[embedding],
                documents=[information],
                metadatas=[{
                    "user_id": user_id,
                    "info_type": info_type,
                    "type": "user_info"
                }],
                ids=[f"user_{user_id}_{len(self.user_collection.get()['ids'])}"]
            )
            
            logger.info(f"Added user information for {user_id}: {info_type}")
            
        except Exception as e:
            logger.error(f"Error adding user information: {str(e)}")
    
    async def update_knowledge_base(self):
        """Update knowledge base from data files"""
        try:
            # Load company guidelines
            guidelines_path = "data/company_guidelines.json"
            if os.path.exists(guidelines_path):
                with open(guidelines_path, 'r') as f:
                    guidelines = json.load(f)
                
                for guideline in guidelines:
                    await self.add_company_guideline(
                        content=guideline['content'],
                        title=guideline['title'],
                        category=guideline.get('category', 'general')
                    )
            
            # Load FAQ items
            faq_path = "data/faq.json"
            if os.path.exists(faq_path):
                with open(faq_path, 'r') as f:
                    faqs = json.load(f)
                
                for faq in faqs:
                    await self.add_faq_item(
                        question=faq['question'],
                        answer=faq['answer'],
                        category=faq.get('category', 'general')
                    )
            
            logger.info("Knowledge base updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating knowledge base: {str(e)}")
    
    async def search_similar_questions(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar questions in the FAQ"""
        try:
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            results = self.faq_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            similar_questions = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    similar_questions.append({
                        "question": metadata.get('question', ''),
                        "answer": metadata.get('answer', ''),
                        "similarity": 1 - distance,  # Convert distance to similarity
                        "category": metadata.get('category', 'general')
                    })
            
            return similar_questions
            
        except Exception as e:
            logger.error(f"Error searching similar questions: {str(e)}")
            return []
    
    async def get_user_context(self, user_id: str) -> str:
        """Get all relevant context for a specific user"""
        try:
            # Get all user information
            user_results = self.user_collection.get(
                where={"user_id": user_id}
            )
            
            if user_results['documents']:
                context_items = user_results['documents']
                return "\n".join([f"User Context: {item}" for item in context_items])
            else:
                return ""
                
        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return ""
    
    async def health_check(self) -> bool:
        """Check if RAG service is healthy"""
        try:
            # Test basic functionality
            test_query = "test query"
            test_embedding = self.embedding_model.encode([test_query]).tolist()[0]
            
            # Test collection access
            self.company_collection.query(
                query_embeddings=[test_embedding],
                n_results=1
            )
            
            return True
            
        except Exception as e:
            logger.error(f"RAG health check failed: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base collections"""
        try:
            return {
                "company_guidelines": len(self.company_collection.get()['ids']),
                "user_information": len(self.user_collection.get()['ids']),
                "faq_items": len(self.faq_collection.get()['ids']),
                "total_documents": (
                    len(self.company_collection.get()['ids']) +
                    len(self.user_collection.get()['ids']) +
                    len(self.faq_collection.get()['ids'])
                )
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                "company_guidelines": 0,
                "user_information": 0,
                "faq_items": 0,
                "total_documents": 0
            }
