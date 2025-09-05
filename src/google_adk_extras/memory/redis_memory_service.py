"""Redis-based memory service implementation using redis-py."""

import json
import logging
from typing import Optional, List
import re
from datetime import datetime

try:
    import redis
    from redis.exceptions import RedisError
except ImportError:
    raise ImportError(
        "Redis-py is required for RedisMemoryService. "
        "Install it with: pip install redis"
    )

from google.genai import types
from .base_custom_memory_service import BaseCustomMemoryService


logger = logging.getLogger('google_adk_extras.' + __name__)


class RedisMemoryService(BaseCustomMemoryService):
    """Redis-based memory service implementation."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize the Redis memory service.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
        """
        super().__init__()
        self.host = host
        self.port = port
        self.db = db
        self.client: Optional[redis.Redis] = None

    async def _initialize_impl(self) -> None:
        """Initialize the Redis connection."""
        try:
            self.client = redis.Redis(host=self.host, port=self.port, db=self.db)
            # Test connection
            self.client.ping()
        except RedisError as e:
            raise RuntimeError(f"Failed to initialize Redis memory service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up Redis connections."""
        if self.client:
            self.client.close()
            self.client = None

    def _serialize_content(self, content: types.Content) -> str:
        """Serialize Content object to JSON string."""
        try:
            return json.dumps(content.to_json_dict())
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize content: {e}")

    def _deserialize_content(self, content_str: str) -> types.Content:
        """Deserialize Content object from JSON string."""
        try:
            content_dict = json.loads(content_str) if content_str else {}
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

    def _get_user_key(self, app_name: str, user_id: str) -> str:
        """Generate Redis key for user's memory entries."""
        return f"memory:{app_name}:{user_id}"

    async def _add_session_to_memory_impl(self, session: "Session") -> None:
        """Implementation of adding a session to memory."""
        if not self.client:
            raise RuntimeError("Service not initialized")
        
        try:
            user_key = self._get_user_key(session.app_name, session.user_id)
            
            # Add each event in the session as a separate memory entry
            for event in session.events:
                if not event.content or not event.content.parts:
                    continue
                
                # Extract text content and search terms
                text_content = self._extract_text_from_content(event.content)
                search_terms = self._extract_search_terms(text_content)
                
                # Create memory entry
                memory_entry = {
                    "id": f"{session.id}:{event.timestamp}",
                    "content": self._serialize_content(event.content),
                    "author": event.author,
                    "timestamp": event.timestamp,
                    "text_content": text_content,
                    "search_terms": search_terms
                }
                
                # Store in Redis with a score based on timestamp for ordering
                score = event.timestamp if event.timestamp else 0
                self.client.zadd(user_key, {json.dumps(memory_entry): score})
                
        except RedisError as e:
            raise RuntimeError(f"Failed to add session to memory: {e}")
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"Failed to serialize memory entry: {e}")

    async def _search_memory_impl(
        self, *, app_name: str, user_id: str, query: str
    ) -> "SearchMemoryResponse":
        """Implementation of searching memory."""
        from google.adk.memory.base_memory_service import SearchMemoryResponse
        from google.adk.memory.memory_entry import MemoryEntry
        
        if not self.client:
            raise RuntimeError("Service not initialized")
        
        try:
            user_key = self._get_user_key(app_name, user_id)
            
            # Extract search terms from query
            query_terms = self._extract_search_terms(query)
            
            if not query_terms:
                # If no searchable terms in query, return empty response
                return SearchMemoryResponse(memories=[])
            
            # Get all memory entries for the user
            memory_entries = self.client.zrange(user_key, 0, -1, withscores=True)
            
            # Filter entries that match any of the query terms
            matching_memories = []
            for entry_data, _ in memory_entries:
                try:
                    entry = json.loads(entry_data)
                    
                    # Check if any query term matches the search terms in this entry
                    entry_search_terms = entry.get("search_terms", [])
                    if any(term in entry_search_terms for term in query_terms):
                        matching_memories.append(entry)
                except (TypeError, ValueError):
                    # Skip invalid entries
                    continue
            
            # Convert to MemoryEntry objects
            memories = []
            for entry in matching_memories:
                content = self._deserialize_content(entry["content"])
                # Format timestamp as ISO string
                timestamp_str = None
                if entry.get("timestamp"):
                    timestamp_str = datetime.fromtimestamp(entry["timestamp"]).isoformat()
                
                memory_entry = MemoryEntry(
                    content=content,
                    author=entry.get("author"),
                    timestamp=timestamp_str
                )
                memories.append(memory_entry)
            
            return SearchMemoryResponse(memories=memories)
        except RedisError as e:
            raise RuntimeError(f"Failed to search memory: {e}")
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"Failed to deserialize memory entry: {e}")