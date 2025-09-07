# Memory Services Examples

This directory contains comprehensive examples for all memory service implementations, demonstrating production-ready conversational memory and search capabilities with multiple storage backends.

## Available Memory Services

### 🗄️ SQL-Based Memory
- **[`sql_memory_example.py`](sql_memory_example.py)** - SQLMemoryService with SQLite
  - Persistent memory with SQL-based full-text search
  - Advanced querying and filtering capabilities
  - Transaction support and ACID compliance
  - Support for PostgreSQL, MySQL, SQL Server with specialized search

### 🍃 MongoDB Memory
- **[`mongodb_memory_example.py`](mongodb_memory_example.py)** - MongoMemoryService
  - Document-based memory with MongoDB's powerful query engine
  - Text search with language-specific stemming
  - Aggregation pipelines for complex queries
  - Geospatial and time-series memory capabilities

### ⚡ Redis Memory
- **[`redis_memory_example.py`](redis_memory_example.py)** - RedisMemoryService  
  - Fast in-memory storage with Redis search capabilities
  - Real-time search with RediSearch module
  - Stream processing for real-time memory updates
  - Clustering and high availability support

### 📄 YAML File Memory
- **[`yaml_memory_example.py`](yaml_memory_example.py)** - YamlFileMemoryService
  - Human-readable memory storage for development
  - Git-friendly format for version control
  - Perfect for debugging and inspection
  - Automatic file organization and indexing

## Features Demonstrated

Each example showcases:

### Core Memory Operations
- **Session Storage**: Adding complete sessions to memory
- **Memory Search**: Full-text search across conversational context
- **Content Filtering**: Searching by app, user, or time ranges
- **Relevance Ranking**: Intelligent ranking of search results
- **Context Retrieval**: Getting relevant context for agent interactions

### Advanced Search Capabilities
- **Semantic Search**: Context-aware search beyond keyword matching
- **Multi-field Search**: Searching across different session components
- **Time-based Queries**: Finding conversations from specific time periods
- **User-specific Memory**: Personalized memory per user
- **Cross-session Search**: Finding information across multiple conversations

### Memory Management
- **Memory Cleanup**: Automatic cleanup of old or irrelevant memories
- **Memory Optimization**: Efficient storage and retrieval patterns  
- **Privacy Controls**: User data isolation and cleanup
- **Memory Analytics**: Understanding memory usage patterns

### Production Patterns
- **Async Operations**: High-performance async search and storage
- **Connection Pooling**: Efficient database connection management
- **Error Handling**: Graceful handling of search failures
- **Monitoring**: Performance metrics and health monitoring

## Requirements

- **Python 3.12+**
- **Google ADK**: `pip install google-adk`
- **This Package**: `pip install google-adk-extras`

### External Services (Optional)

Examples gracefully handle missing services:

- **MongoDB Example**: `docker run -d --name mongo -p 27017:27017 mongo`
- **Redis Example**: `docker run -d --name redis -p 6379:6379 redis`

## Running Examples

### Quick Start

```bash
cd /path/to/google-adk-extras

# SQL Memory (always available)
uv run python examples/memory/sql_memory_example.py

# YAML Memory (always available)
uv run python examples/memory/yaml_memory_example.py

# MongoDB Memory (requires MongoDB)
docker run -d --name mongo -p 27017:27017 mongo
uv run python examples/memory/mongodb_memory_example.py

# Redis Memory (requires Redis)
docker run -d --name redis -p 6379:6379 redis
uv run python examples/memory/redis_memory_example.py
```

### Production Configuration Examples

#### SQL with Full-Text Search
```python
from google_adk_extras.memory import SQLMemoryService

# PostgreSQL with full-text search
memory_service = SQLMemoryService(
    connection_string="postgresql://user:password@localhost/memory",
    enable_full_text_search=True,
    search_language="english",
    pool_size=15
)
await memory_service.initialize()
```

#### MongoDB with Text Indexing  
```python
from google_adk_extras.memory import MongoMemoryService

# MongoDB with advanced text search
memory_service = MongoMemoryService(
    connection_string="mongodb://user:password@localhost:27017/memory?authSource=admin",
    database_name="conversational_memory",
    collection_name="sessions",
    text_search_enabled=True
)
await memory_service.initialize()
```

#### Redis with RediSearch
```python
from google_adk_extras.memory import RedisMemoryService

# Redis with search capabilities
memory_service = RedisMemoryService(
    host="redis-cluster-endpoint",
    port=6379,
    password="your-redis-password",
    enable_search=True,
    search_index_name="memory_search"
)
await memory_service.initialize()
```

## Integration Examples

### With Google ADK Agents

```python
from google.adk import Agent, Runner
from google_adk_extras.memory import SQLMemoryService
from google.adk.sessions.session import Session
from google.adk.events.event import Event

# Create memory service
memory_service = SQLMemoryService("postgresql://localhost/memory")
await memory_service.initialize()

# Create agent with memory
agent = Agent(
    name="memory-assistant", 
    model="gemini-2.0-flash",
    instructions="You have access to conversational memory and can recall past interactions"
)

# Add session to memory
session = Session(
    id="session_123",
    app_name="assistant",
    user_id="user_456",
    events=[
        Event(content="User said: I love pizza"),
        Event(content="Assistant said: Great choice! What's your favorite topping?"),
        Event(content="User said: Pepperoni and mushrooms")
    ]
)

await memory_service.add_session_to_memory(session)

# Search memory for context
search_results = await memory_service.search_memory(
    app_name="assistant",
    user_id="user_456", 
    query="pizza preferences"
)

print(f"Found {len(search_results.memories)} relevant memories")
```

### Smart Context Retrieval

```python
async def get_relevant_context(memory_service, app_name, user_id, current_query, max_results=5):
    """Get relevant context for current conversation"""
    
    # Search for relevant memories
    search_results = await memory_service.search_memory(
        app_name=app_name,
        user_id=user_id,
        query=current_query,
        max_results=max_results
    )
    
    # Format context for agent
    context_items = []
    for memory in search_results.memories:
        # Extract key information from memory
        session_id = memory.get('session_id')
        events = memory.get('events', [])
        timestamp = memory.get('timestamp')
        
        # Create context summary
        context_summary = {
            'session_id': session_id,
            'timestamp': timestamp,
            'relevant_events': [
                event['content'] for event in events[-3:]  # Last 3 events
            ]
        }
        context_items.append(context_summary)
    
    return context_items

# Use in conversation
context = await get_relevant_context(
    memory_service, 
    "assistant", 
    "user_456", 
    "What restaurants do I like?"
)
```

### Memory-Aware Agent Runner

```python
from google_adk_extras.runners import EnhancedRunner

class MemoryAwareRunner(EnhancedRunner):
    """Runner that automatically manages conversational memory"""
    
    def __init__(self, agent, memory_service, **kwargs):
        super().__init__(agent, **kwargs)
        self.memory_service = memory_service
    
    async def run(self, message, user_id, **kwargs):
        """Run with automatic memory context"""
        
        # Get relevant context from memory
        context = await self.memory_service.search_memory(
            app_name=self.app_name,
            user_id=user_id,
            query=message,
            max_results=3
        )
        
        # Add context to agent instructions
        if context.memories:
            context_text = "Relevant context from previous conversations:\n"
            for memory in context.memories:
                context_text += f"- {memory['summary']}\n"
            
            enhanced_message = f"{context_text}\n\nCurrent message: {message}"
        else:
            enhanced_message = message
        
        # Run with enhanced context
        result = await super().run(enhanced_message, user_id, **kwargs)
        
        # Store this conversation in memory
        if result.session:
            await self.memory_service.add_session_to_memory(result.session)
        
        return result

# Usage
memory_service = SQLMemoryService("sqlite:///conversations.db")
await memory_service.initialize()

runner = MemoryAwareRunner(
    agent=my_agent,
    memory_service=memory_service,
    app_name="smart_assistant"
)

result = await runner.run("What did we discuss about my vacation plans?", "user_123")
```

## Search Pattern Examples

### Basic Text Search
```python
# Simple keyword search
results = await memory_service.search_memory(
    app_name="assistant",
    user_id="user_123", 
    query="vacation plans"
)

print(f"Found {len(results.memories)} memories about vacation plans")
```

### Advanced Search Patterns
```python
# Multi-field search with filters
results = await memory_service.search_memory(
    app_name="assistant",
    user_id="user_123",
    query="travel booking flight hotel",
    filters={
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "session_type": "planning"
    },
    max_results=10
)

# Search across multiple users (admin/support scenarios)
results = await memory_service.search_memory(
    app_name="support_system",
    query="billing issue payment problem",
    user_id=None,  # Search all users
    max_results=20
)

# Time-based search
import datetime
last_week = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

results = await memory_service.search_memory(
    app_name="assistant", 
    user_id="user_123",
    query="project status update",
    filters={"start_date": last_week}
)
```

### Semantic Search Examples
```python
# Search for concepts, not just keywords
conceptual_queries = [
    "food preferences and dietary restrictions",
    "work schedule and availability", 
    "family members and relationships",
    "hobbies and interests",
    "technical skills and experience"
]

for query in conceptual_queries:
    results = await memory_service.search_memory(
        app_name="personal_assistant",
        user_id="user_123", 
        query=query,
        max_results=5
    )
    print(f"'{query}': {len(results.memories)} relevant memories")
```

## Performance Benchmarks

Each example includes performance testing:

```python
import time
import random
from google.adk.sessions.session import Session
from google.adk.events.event import Event

async def benchmark_memory_service(service, num_sessions=100, num_searches=50):
    """Benchmark memory operations"""
    
    # Generate test sessions
    sessions = []
    topics = ["travel", "food", "work", "family", "hobbies", "technology"]
    
    for i in range(num_sessions):
        topic = random.choice(topics)
        session = Session(
            id=f"session_{i}",
            app_name="benchmark",
            user_id=f"user_{i % 10}",  # 10 different users
            events=[
                Event(content=f"Discussion about {topic} and related topics"),
                Event(content=f"User asked about {topic} recommendations"),
                Event(content=f"Assistant provided {topic} suggestions")
            ]
        )
        sessions.append(session)
    
    # Benchmark session storage
    start_time = time.time()
    for session in sessions:
        await service.add_session_to_memory(session)
    storage_time = time.time() - start_time
    
    print(f"Stored {num_sessions} sessions in {storage_time:.2f}s ({num_sessions/storage_time:.1f} sessions/sec)")
    
    # Benchmark search performance
    search_queries = [f"information about {topic}" for topic in topics]
    
    start_time = time.time()
    for _ in range(num_searches):
        query = random.choice(search_queries)
        user_id = f"user_{random.randint(0, 9)}"
        
        results = await service.search_memory(
            app_name="benchmark",
            user_id=user_id,
            query=query,
            max_results=10
        )
    
    search_time = time.time() - start_time
    print(f"Executed {num_searches} searches in {search_time:.2f}s ({num_searches/search_time:.1f} searches/sec)")
```

## Memory Analytics

### Usage Patterns Analysis
```python
async def analyze_memory_usage(memory_service, app_name, time_period_days=30):
    """Analyze memory usage patterns"""
    
    from datetime import datetime, timedelta
    
    # Get recent conversations
    start_date = (datetime.now() - timedelta(days=time_period_days)).isoformat()
    
    # Analyze search patterns (this would require enhanced service methods)
    popular_queries = await memory_service.get_popular_search_terms(
        app_name=app_name,
        start_date=start_date,
        limit=20
    )
    
    # User engagement analysis
    active_users = await memory_service.get_active_users(
        app_name=app_name,
        start_date=start_date
    )
    
    # Memory growth analysis
    memory_stats = await memory_service.get_memory_statistics(
        app_name=app_name,
        start_date=start_date
    )
    
    return {
        'popular_queries': popular_queries,
        'active_users': len(active_users),
        'total_memories': memory_stats['total_sessions'],
        'average_events_per_session': memory_stats['avg_events_per_session']
    }
```

## Troubleshooting

### Common Issues

1. **Search Performance Issues**
   ```python
   # Check if indexes are properly created
   # SQL: EXPLAIN QUERY PLAN SELECT * FROM memories WHERE content MATCH 'search_term'
   # MongoDB: db.sessions.explain().find({$text: {$search: "search_term"}})
   # Redis: FT.INFO memory_search_index
   ```

2. **Memory Growth Issues**
   ```python
   # Implement memory cleanup strategy
   async def cleanup_old_memories(service, days_to_keep=90):
       cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
       
       # This would require enhanced service method
       await service.cleanup_memories_before(cutoff_date)
   ```

3. **Search Accuracy Issues**
   ```python
   # Improve search with better preprocessing
   def preprocess_search_query(query):
       # Remove stopwords, normalize text, extract key terms
       import re
       
       # Basic preprocessing
       query = re.sub(r'[^\w\s]', '', query.lower())
       stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
       words = [w for w in query.split() if w not in stopwords]
       
       return ' '.join(words)
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable memory service debugging
logging.getLogger('google_adk_extras.memory').setLevel(logging.DEBUG)
```

### Performance Tuning

- **SQL**: Create full-text search indexes, optimize query patterns
- **MongoDB**: Use compound indexes, enable text search indexes
- **Redis**: Configure RediSearch properly, use appropriate data structures
- **YAML**: Keep memory files organized, implement efficient file searching
