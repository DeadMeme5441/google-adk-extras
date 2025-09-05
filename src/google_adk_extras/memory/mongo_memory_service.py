"""MongoDB-based memory service implementation using PyMongo."""

import json
import logging
from typing import Optional, List
import re
from datetime import datetime

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    from bson import ObjectId
except ImportError:
    raise ImportError(
        "PyMongo is required for MongoMemoryService. "
        "Install it with: pip install pymongo"
    )

from google.genai import types
from .base_custom_memory_service import BaseCustomMemoryService


logger = logging.getLogger('google_adk_extras.' + __name__)


class MongoMemoryService(BaseCustomMemoryService):
    """MongoDB-based memory service implementation."""

    def __init__(self, connection_string: str, database_name: str = "adk_memory"):
        """Initialize the MongoDB memory service.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        super().__init__()
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db: Optional[object] = None

    async def _initialize_impl(self) -> None:
        """Initialize the MongoDB connection."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Create indexes for efficient querying
            memory_collection = self.db["memory_entries"]
            memory_collection.create_index([("app_name", 1), ("user_id", 1)])
            memory_collection.create_index([("search_terms", 1)])
            memory_collection.create_index([("app_name", 1), ("user_id", 1), ("search_terms", 1)])
        except PyMongoError as e:
            raise RuntimeError(f"Failed to initialize MongoDB memory service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up MongoDB connections."""
        if self.client:
            self.client.close()
            self.client = None
        self.db = None

    def _serialize_content(self, content: types.Content) -> dict:
        """Serialize Content object to dictionary."""
        try:
            return content.to_json_dict()
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize content: {e}")

    def _deserialize_content(self, content_dict: dict) -> types.Content:
        """Deserialize Content object from dictionary."""
        try:
            return types.Content(**content_dict)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to deserialize content: {e}")

    def _extract_text_from_content(self, content: types.Content) -> str:
        """Extract text content from a Content object for storage and search."""
        if not content or not content.parts:
            return ""
        
        text_parts = []
        for part in content.parts:
            if part.text:
                text_parts.append(part.text)
        
        return " ".join(text_parts)

    def _extract_search_terms(self, text: str) -> List[str]:
        """Extract search terms from text content."""
        # Extract words from text and convert to lowercase
        words = re.findall(r'[A-Za-z]+', text.lower())
        # Return unique words as a list
        return sorted(set(words))

    async def _add_session_to_memory_impl(self, session: "Session") -> None:
        """Implementation of adding a session to memory."""
        if not self.db:
            raise RuntimeError("Service not initialized")
        
        try:
            memory_collection = self.db["memory_entries"]
            
            # Add each event in the session as a separate memory entry
            for event in session.events:
                if not event.content or not event.content.parts:
                    continue
                
                # Extract text content and search terms
                text_content = self._extract_text_from_content(event.content)
                search_terms = self._extract_search_terms(text_content)
                
                # Create memory document
                memory_document = {
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "content": self._serialize_content(event.content),
                    "author": event.author,
                    "timestamp": datetime.fromtimestamp(event.timestamp) if event.timestamp else None,
                    "text_content": text_content,
                    "search_terms": search_terms
                }
                
                # Save to MongoDB
                memory_collection.insert_one(memory_document)
                
        except PyMongoError as e:
            raise RuntimeError(f"Failed to add session to memory: {e}")

    async def _search_memory_impl(
        self, *, app_name: str, user_id: str, query: str
    ) -> "SearchMemoryResponse":
        """Implementation of searching memory."""
        from google.adk.memory.base_memory_service import SearchMemoryResponse
        from google.adk.memory.memory_entry import MemoryEntry
        
        if not self.db:
            raise RuntimeError("Service not initialized")
        
        try:
            memory_collection = self.db["memory_entries"]
            
            # Extract search terms from query
            query_terms = self._extract_search_terms(query)
            
            if not query_terms:
                # If no searchable terms in query, return empty response
                return SearchMemoryResponse(memories=[])
            
            # Build query - find entries that match any of the query words
            # Using MongoDB's $in operator to match any of the search terms
            mongo_query = {
                "app_name": app_name,
                "user_id": user_id,
                "search_terms": {"$in": query_terms}
            }
            
            # Execute query
            cursor = memory_collection.find(mongo_query)
            
            # Convert to MemoryEntry objects
            memories = []
            for doc in cursor:
                content = self._deserialize_content(doc["content"])
                memory_entry = MemoryEntry(
                    content=content,
                    author=doc.get("author"),
                    timestamp=doc["timestamp"].isoformat() if doc.get("timestamp") else None
                )
                memories.append(memory_entry)
            
            return SearchMemoryResponse(memories=memories)
        except PyMongoError as e:
            raise RuntimeError(f"Failed to search memory: {e}")