"""SQL-based memory service implementation using SQLAlchemy."""

import json
import logging
from typing import Optional, List
import re
from datetime import datetime, timezone

try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Index
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    raise ImportError(
        "SQLAlchemy is required for SQLMemoryService. "
        "Install it with: pip install sqlalchemy"
    )

from google.genai import types
from .base_custom_memory_service import BaseCustomMemoryService


logger = logging.getLogger('google_adk_extras.' + __name__)

# Use the modern declarative_base import
Base = declarative_base()


class SQLMemoryModel(Base):
    """SQLAlchemy model for storing memory entries."""
    __tablename__ = 'adk_memory_entries'

    # Auto-incrementing ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiers
    app_name = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Content data
    content_json = Column(Text, nullable=False)  # JSON string of Content object
    author = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Search optimization
    text_content = Column(Text, nullable=False)  # Extracted text for searching
    search_terms = Column(Text, nullable=False)  # Space-separated search terms

    # Composite index for efficient querying
    __table_args__ = (
        Index('idx_app_user_query', 'app_name', 'user_id', 'search_terms'),
    )


class SQLMemoryService(BaseCustomMemoryService):
    """SQL-based memory service implementation.

    This service stores memory entries in a SQL database using SQLAlchemy.
    It supports efficient searching of memory entries by extracting and indexing
    text content from conversation events.
    """

    def __init__(self, database_url: str):
        """Initialize the SQL memory service.
        
        Args:
            database_url: Database connection string (e.g., 'sqlite:///memory.db')
        """
        super().__init__()
        self.database_url = database_url
        self.engine: Optional[object] = None
        self.session_local: Optional[object] = None

    async def _initialize_impl(self) -> None:
        """Initialize the database connection and create tables.
        
        Raises:
            RuntimeError: If database initialization fails.
        """
        try:
            self.engine = create_engine(self.database_url)
            Base.metadata.create_all(self.engine)
            self.session_local = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=self.engine
            )
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to initialize SQL memory service: {e}")

    async def _cleanup_impl(self) -> None:
        """Clean up database connections."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self.session_local = None

    def _get_db_session(self):
        """Get a database session.
        
        Returns:
            A database session object.
            
        Raises:
            RuntimeError: If the service is not initialized.
        """
        if not self.session_local:
            raise RuntimeError("Service not initialized")
        return self.session_local()

    def _serialize_content(self, content: types.Content) -> str:
        """Serialize Content object to JSON string.
        
        Args:
            content: The Content object to serialize.
            
        Returns:
            JSON string representation of the content.
            
        Raises:
            ValueError: If serialization fails.
        """
        try:
            return json.dumps(content.to_json_dict())
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize content: {e}")

    def _deserialize_content(self, content_str: str) -> types.Content:
        """Deserialize Content object from JSON string.
        
        Args:
            content_str: JSON string representation of the content.
            
        Returns:
            The deserialized Content object.
            
        Raises:
            ValueError: If deserialization fails.
        """
        try:
            content_dict = json.loads(content_str) if content_str else {}
            return types.Content(**content_dict)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to deserialize content: {e}")

    def _extract_text_from_content(self, content: types.Content) -> str:
        """Extract text content from a Content object for storage and search.
        
        Args:
            content: The Content object to extract text from.
            
        Returns:
            Extracted text content.
        """
        if not content or not content.parts:
            return ""
        
        text_parts = []
        for part in content.parts:
            if part.text:
                text_parts.append(part.text)
        
        return " ".join(text_parts)

    def _extract_search_terms(self, text: str) -> str:
        """Extract search terms from text content.
        
        Args:
            text: The text to extract search terms from.
            
        Returns:
            Space-separated unique search terms.
        """
        # Extract words from text and convert to lowercase
        words = re.findall(r'[A-Za-z]+', text.lower())
        # Return space-separated unique words
        return " ".join(sorted(set(words)))

    async def _add_session_to_memory_impl(self, session: "Session") -> None:
        """Implementation of adding a session to memory.
        
        Args:
            session: The session to add to memory.
            
        Raises:
            RuntimeError: If adding the session to memory fails.
        """
        db_session = self._get_db_session()
        try:
            # Add each event in the session as a separate memory entry
            for event in session.events:
                if not event.content or not event.content.parts:
                    continue
                
                # Extract text content and search terms
                text_content = self._extract_text_from_content(event.content)
                search_terms = self._extract_search_terms(text_content)
                
                # Create memory model
                db_memory = SQLMemoryModel(
                    app_name=session.app_name,
                    user_id=session.user_id,
                    content_json=self._serialize_content(event.content),
                    author=event.author,
                    timestamp=datetime.fromtimestamp(event.timestamp, tz=timezone.utc) if event.timestamp else None,
                    text_content=text_content,
                    search_terms=search_terms
                )
                
                # Save to database
                db_session.add(db_memory)
            
            db_session.commit()
        except SQLAlchemyError as e:
            db_session.rollback()
            raise RuntimeError(f"Failed to add session to memory: {e}")
        finally:
            db_session.close()

    async def _search_memory_impl(
        self, *, app_name: str, user_id: str, query: str
    ) -> "SearchMemoryResponse":
        """Implementation of searching memory.
        
        Args:
            app_name: The name of the application.
            user_id: The id of the user.
            query: The query to search for.
            
        Returns:
            A SearchMemoryResponse containing the matching memories.
            
        Raises:
            RuntimeError: If searching memory fails.
        """
        try:
            from google.adk.memory.base_memory_service import SearchMemoryResponse
            from google.adk.memory.memory_entry import MemoryEntry
        except Exception:  # Fallback when ADK surface differs
            from types import SimpleNamespace as MemoryEntry  # type: ignore
            SearchMemoryResponse = None  # type: ignore
        
        db_session = self._get_db_session()
        try:
            # Extract search terms from query
            query_terms = self._extract_search_terms(query)
            query_words = query_terms.split() if query_terms else []
            
            if not query_words:
                # If no searchable terms in query, return empty response
                return SearchMemoryResponse(memories=[])
            
            # Build query - find entries that match any of the query words
            db_query = db_session.query(SQLMemoryModel).filter(
                SQLMemoryModel.app_name == app_name,
                SQLMemoryModel.user_id == user_id
            )
            
            # Add search term filters - use OR logic to match any query word
            from sqlalchemy import or_
            conditions = []
            for word in query_words:
                conditions.append(SQLMemoryModel.search_terms.contains(word))
            
            if conditions:
                db_query = db_query.filter(or_(*conditions))
            
            # Execute query
            db_memories = db_query.all()
            
            # Convert to MemoryEntry objects
            memories = []
            for db_memory in db_memories:
                content = self._deserialize_content(db_memory.content_json)
                try:
                    memory_entry = MemoryEntry(
                        content=content,
                        author=db_memory.author,
                        timestamp=db_memory.timestamp.isoformat() if db_memory.timestamp else None
                    )
                except TypeError:
                    # SimpleNamespace fallback
                    from types import SimpleNamespace
                    memory_entry = SimpleNamespace(
                        content=content,
                        author=db_memory.author,
                        timestamp=db_memory.timestamp.isoformat() if db_memory.timestamp else None
                    )
                memories.append(memory_entry)

            if SearchMemoryResponse is not None:
                return SearchMemoryResponse(memories=memories)
            else:
                from types import SimpleNamespace
                return SimpleNamespace(memories=memories)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to search memory: {e}")
        finally:
            db_session.close()
