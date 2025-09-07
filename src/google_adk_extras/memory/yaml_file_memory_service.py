"""YAML file-based memory service implementation."""

import os
import json
import logging
from typing import Optional, List
from pathlib import Path
import re
from datetime import datetime

import yaml

from google.genai import types
from .base_custom_memory_service import BaseCustomMemoryService


logger = logging.getLogger('google_adk_extras.' + __name__)


class YamlFileMemoryService(BaseCustomMemoryService):
    """YAML file-based memory service implementation.

    This service stores memory entries in YAML files in a hierarchical directory structure.
    Each memory entry is stored in a separate YAML file organized by app name and user ID.
    Memory entries are searchable by extracting and indexing text content from conversation events.
    """

    def __init__(self, base_directory: str = "./memory"):
        """Initialize the YAML file memory service.
        
        Args:
            base_directory: Base directory for storing memory files. Defaults to "./memory".
        """
        super().__init__()
        self.base_directory = Path(base_directory)
        # Create base directory if it doesn't exist
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def _initialize_impl(self) -> None:
        """Initialize the file system memory service.
        
        Ensures the base directory exists.
        """
        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)

    async def _cleanup_impl(self) -> None:
        """Clean up resources (no cleanup needed for file-based service)."""
        pass

    def _get_memory_directory(self, app_name: str, user_id: str) -> Path:
        """Generate directory path for memory entries.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            
        Returns:
            Path to the memory directory.
        """
        directory = self.base_directory / app_name / user_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _get_memory_file_path(self, app_name: str, user_id: str, memory_id: str) -> Path:
        """Generate file path for a memory entry.
        
        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            memory_id: The ID of the memory entry.
            
        Returns:
            Path to the memory file.
        """
        directory = self._get_memory_directory(app_name, user_id)
        return directory / f"{memory_id}.yaml"

    def _serialize_content(self, content: types.Content) -> dict:
        """Serialize Content object to dictionary.
        
        Args:
            content: The Content object to serialize.
            
        Returns:
            Dictionary representation of the content.
            
        Raises:
            ValueError: If serialization fails.
        """
        try:
            return content.to_json_dict()
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize content: {e}")

    def _deserialize_content(self, content_dict: dict) -> types.Content:
        """Deserialize Content object from dictionary.
        
        Args:
            content_dict: Dictionary representation of the content.
            
        Returns:
            The deserialized Content object.
            
        Raises:
            ValueError: If deserialization fails.
        """
        try:
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

    def _extract_search_terms(self, text: str) -> List[str]:
        """Extract search terms from text content.
        
        Args:
            text: The text to extract search terms from.
            
        Returns:
            List of unique search terms.
        """
        # Extract words from text and convert to lowercase
        words = re.findall(r'[A-Za-z]+', text.lower())
        # Return unique words as a list
        return sorted(set(words))

    async def _add_session_to_memory_impl(self, session: "Session") -> None:
        """Implementation of adding a session to memory.
        
        Args:
            session: The session to add to memory.
            
        Raises:
            RuntimeError: If adding the session to memory fails.
        """
        try:
            # Add each event in the session as a separate memory entry
            for event in session.events:
                if not event.content or not event.content.parts:
                    continue
                
                # Extract text content and search terms
                text_content = self._extract_text_from_content(event.content)
                search_terms = self._extract_search_terms(text_content)
                
                # Generate memory ID
                memory_id = f"{session.id}_{event.timestamp}"
                
                # Create memory entry
                memory_entry = {
                    "id": memory_id,
                    "app_name": session.app_name,
                    "user_id": session.user_id,
                    "content": self._serialize_content(event.content),
                    "author": event.author,
                    "timestamp": event.timestamp,
                    "text_content": text_content,
                    "search_terms": search_terms
                }
                
                # Save to YAML file
                file_path = self._get_memory_file_path(session.app_name, session.user_id, memory_id)
                with open(file_path, 'w') as f:
                    yaml.dump(memory_entry, f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            raise RuntimeError(f"Failed to add session to memory: {e}")

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
        except Exception:
            from types import SimpleNamespace as MemoryEntry  # type: ignore
            SearchMemoryResponse = None  # type: ignore
        
        try:
            # Extract search terms from query
            query_terms = self._extract_search_terms(query)
            
            if not query_terms:
                # If no searchable terms in query, return empty response
                return SearchMemoryResponse(memories=[])
            
            # Get memory directory for this user
            memory_directory = self._get_memory_directory(app_name, user_id)
            
            # Find all memory files for this user
            memory_files = list(memory_directory.glob("*.yaml"))
            
            # Filter entries that match any of the query terms
            matching_memories = []
            for file_path in memory_files:
                try:
                    with open(file_path, 'r') as f:
                        entry = yaml.safe_load(f)
                    
                    # Check if any query term matches the search terms in this entry
                    entry_search_terms = entry.get("search_terms", [])
                    if any(term in entry_search_terms for term in query_terms):
                        matching_memories.append(entry)
                except (yaml.YAMLError, IOError):
                    # Skip invalid files
                    continue
            
            # Convert to MemoryEntry objects
            memories = []
            for entry in matching_memories:
                content = self._deserialize_content(entry["content"])
                # Format timestamp as ISO string
                timestamp_str = None
                if entry.get("timestamp"):
                    timestamp_str = datetime.fromtimestamp(entry["timestamp"]).isoformat()
                try:
                    memory_entry = MemoryEntry(
                        content=content,
                        author=entry.get("author"),
                        timestamp=timestamp_str
                    )
                except TypeError:
                    from types import SimpleNamespace
                    memory_entry = SimpleNamespace(
                        content=content,
                        author=entry.get("author"),
                        timestamp=timestamp_str
                    )
                memories.append(memory_entry)

            if SearchMemoryResponse is not None:
                return SearchMemoryResponse(memories=memories)
            else:
                from types import SimpleNamespace
                return SimpleNamespace(memories=memories)
        except Exception as e:
            raise RuntimeError(f"Failed to search memory: {e}")
