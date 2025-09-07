# Artifact Services Examples

This directory contains comprehensive examples for all artifact service implementations, demonstrating production-ready file and binary data management with multiple storage backends.

## Available Artifact Services

### 🗄️ SQL-Based Artifacts
- **[`sql_artifact_example.py`](sql_artifact_example.py)** - SQLArtifactService with SQLite
  - Database storage with metadata and versioning
  - Advanced querying and filtering capabilities
  - Connection pooling and transaction support
  - Support for PostgreSQL, MySQL, SQL Server

### 🍃 MongoDB Artifacts
- **[`mongodb_artifact_example.py`](mongodb_artifact_example.py)** - MongoArtifactService
  - GridFS support for large files and binary data
  - Document-based metadata with rich querying
  - Automatic chunking for large artifacts
  - Replica set and sharding support

### 📁 Local Filesystem Artifacts
- **[`local_folder_artifact_example.py`](local_folder_artifact_example.py)** - LocalFolderArtifactService
  - Organized local filesystem with metadata
  - Perfect for development and local storage
  - Automatic directory organization
  - File versioning and backup strategies

### ☁️ Cloud Storage Artifacts
- **[`s3_artifact_example.py`](s3_artifact_example.py)** - S3ArtifactService
  - AWS S3 and S3-compatible services (MinIO, DigitalOcean Spaces)
  - Scalable cloud storage with CDN integration
  - Automatic encryption and security
  - Multi-region and cross-region replication

## Features Demonstrated

Each example showcases:

### Core Artifact Operations
- **Artifact Saving**: Storing files with metadata and versioning
- **Artifact Loading**: Retrieving files by key and version
- **Key Listing**: Finding artifacts by app, user, or session
- **Version Management**: Managing multiple versions of artifacts
- **Metadata Handling**: Rich metadata storage and querying

### File Types Supported
- **Text Files**: Plain text, JSON, XML, CSV
- **Binary Files**: Images, documents, archives, executables
- **Structured Data**: Serialized objects, database exports
- **Media Files**: Audio, video, images with metadata
- **Code Assets**: Source code, documentation, build artifacts

### Advanced Features
- **Async Operations**: Full async/await support for high performance
- **Streaming Support**: Efficient handling of large files
- **Error Handling**: Graceful handling of service failures
- **Security**: Encryption, access controls, and audit trails
- **Integration**: Working with Google ADK agents and runners

### Production Patterns
- **Health Checks**: Service availability monitoring
- **Performance Optimization**: Caching, compression, and CDN
- **Backup Strategies**: Automated backup and disaster recovery
- **Monitoring**: Detailed logging and metrics collection

## Requirements

- **Python 3.12+**
- **Google ADK**: `pip install google-adk`
- **This Package**: `pip install google-adk-extras`

### External Services (Optional)

Examples gracefully handle missing services:

- **MongoDB Example**: `docker run -d --name mongo -p 27017:27017 mongo`
- **S3 Example**: AWS credentials configured (`aws configure` or environment variables)

## Running Examples

### Quick Start

```bash
cd /path/to/google-adk-extras

# SQL Artifact (always available)
uv run python examples/artifact/sql_artifact_example.py

# Local Folder (always available)
uv run python examples/artifact/local_folder_artifact_example.py

# MongoDB Artifact (requires MongoDB)
docker run -d --name mongo -p 27017:27017 mongo
uv run python examples/artifact/mongodb_artifact_example.py

# S3 Artifact (requires AWS credentials)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
uv run python examples/artifact/s3_artifact_example.py
```

### Production Configuration Examples

#### SQL with PostgreSQL
```python
from google_adk_extras.artifacts import SQLArtifactService

# Production PostgreSQL setup
artifact_service = SQLArtifactService(
    connection_string="postgresql://user:password@localhost/artifacts",
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
await artifact_service.initialize()
```

#### MongoDB with GridFS
```python
from google_adk_extras.artifacts import MongoArtifactService

# Production MongoDB with GridFS
artifact_service = MongoArtifactService(
    connection_string="mongodb://user:password@localhost:27017/artifacts?authSource=admin",
    database_name="artifacts",
    collection_name="files",
    chunk_size=1024*1024  # 1MB chunks
)
await artifact_service.initialize()
```

#### S3 with Custom Configuration
```python
from google_adk_extras.artifacts import S3ArtifactService

# Production S3 setup
artifact_service = S3ArtifactService(
    bucket="my-production-artifacts",
    region="us-east-1",
    endpoint_url="https://s3.amazonaws.com",  # or MinIO endpoint
    access_key_id="your-access-key",
    secret_access_key="your-secret-key",
    encryption="AES256"
)
await artifact_service.initialize()
```

## Integration Examples

### With Google ADK Agents

```python
from google.adk import Agent, Runner
from google_adk_extras.artifacts import S3ArtifactService
from google.genai import types

# Create artifact service
artifact_service = S3ArtifactService(bucket="agent-artifacts")
await artifact_service.initialize()

# Create agent with file handling capabilities
agent = Agent(
    name="file-processor",
    model="gemini-2.0-flash",
    instructions="You can save and retrieve files for users"
)

# Save user file
text_blob = types.Blob(data=b"User document content", mime_type="text/plain")
text_part = types.Part(inline_data=text_blob)

version = await artifact_service.save_artifact(
    app_name="file-processor",
    user_id="user_123",
    session_id="session_456", 
    filename="user_document.txt",
    artifact=text_part
)

# Load file later
loaded_artifact = await artifact_service.load_artifact(
    app_name="file-processor",
    user_id="user_123",
    filename="user_document.txt",
    version=version
)
```

### With Enhanced Configuration

```python
from google_adk_extras.artifacts import SQLArtifactService
from google_adk_extras.configuration import ConfigurationSystem

# Load configuration
config_system = ConfigurationSystem()
config = await config_system.load_config("artifacts_config.yaml")

# Create service from config
artifact_service = SQLArtifactService(
    connection_string=config["database"]["url"],
    table_name=config["database"]["table"]
)
await artifact_service.initialize()
```

## File Type Examples

### Text Files
```python
from google.genai import types

# Save JSON data
json_data = json.dumps({"key": "value", "items": [1, 2, 3]})
json_blob = types.Blob(data=json_data.encode(), mime_type="application/json")
json_part = types.Part(inline_data=json_blob)

await artifact_service.save_artifact(
    app_name="data-processor",
    user_id="user_123",
    session_id="session_456",
    filename="data.json",
    artifact=json_part
)
```

### Binary Files
```python
# Save image file
with open("image.png", "rb") as f:
    image_data = f.read()

image_blob = types.Blob(data=image_data, mime_type="image/png")
image_part = types.Part(inline_data=image_blob)

await artifact_service.save_artifact(
    app_name="image-processor",
    user_id="user_123",
    session_id="session_456",
    filename="processed_image.png", 
    artifact=image_part
)
```

### Large Files with Streaming
```python
# Handle large files efficiently
async def save_large_file(service, file_path, **kwargs):
    """Save large file with streaming support"""
    
    with open(file_path, "rb") as f:
        # Read in chunks for memory efficiency
        chunk_size = 1024 * 1024  # 1MB chunks
        chunks = []
        
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
    
    # Combine chunks and create blob
    file_data = b''.join(chunks)
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    
    blob = types.Blob(data=file_data, mime_type=mime_type)
    part = types.Part(inline_data=blob)
    
    return await service.save_artifact(
        filename=os.path.basename(file_path),
        artifact=part,
        **kwargs
    )
```

## Performance Benchmarks

Each example includes performance testing:

```python
import time
import random
import string

async def benchmark_artifact_service(service, file_sizes=[1024, 10240, 102400]):
    """Benchmark artifact operations with different file sizes"""
    
    results = {}
    
    for size in file_sizes:
        # Generate test data
        test_data = ''.join(random.choices(string.ascii_letters, k=size)).encode()
        blob = types.Blob(data=test_data, mime_type="text/plain")
        part = types.Part(inline_data=blob)
        
        # Save benchmark
        start_time = time.time()
        version = await service.save_artifact(
            app_name="benchmark",
            user_id="test_user",
            session_id="test_session",
            filename=f"test_{size}.txt",
            artifact=part
        )
        save_time = time.time() - start_time
        
        # Load benchmark
        start_time = time.time()
        loaded = await service.load_artifact(
            app_name="benchmark",
            user_id="test_user",
            filename=f"test_{size}.txt",
            version=version
        )
        load_time = time.time() - start_time
        
        results[size] = {
            'save_time': save_time,
            'load_time': load_time,
            'throughput_mbps': (size / 1024 / 1024) / (save_time + load_time)
        }
    
    return results
```

## Security Best Practices

### Data Encryption
```python
# Enable encryption at rest (S3 example)
artifact_service = S3ArtifactService(
    bucket="secure-artifacts",
    encryption="AES256",
    kms_key_id="alias/my-artifacts-key"  # AWS KMS
)

# Client-side encryption (all services)
from cryptography.fernet import Fernet

def encrypt_data(data: bytes, key: bytes) -> bytes:
    """Encrypt data before storage"""
    f = Fernet(key)
    return f.encrypt(data)

def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """Decrypt data after retrieval"""
    f = Fernet(key)
    return f.decrypt(encrypted_data)
```

### Access Controls
```python
# Implement access controls
async def save_secure_artifact(service, user_id, filename, data, access_level="private"):
    """Save artifact with access control metadata"""
    
    # Add security metadata
    metadata = {
        "owner": user_id,
        "access_level": access_level,
        "created_at": datetime.utcnow().isoformat(),
        "checksum": hashlib.sha256(data).hexdigest()
    }
    
    blob = types.Blob(data=data, mime_type="application/octet-stream")
    part = types.Part(inline_data=blob)
    
    return await service.save_artifact(
        app_name="secure-app",
        user_id=user_id,
        session_id=f"secure-{uuid.uuid4()}",
        filename=filename,
        artifact=part,
        metadata=metadata
    )
```

## Troubleshooting

### Common Issues

1. **Storage Space Issues**
   ```bash
   # Check disk space (local storage)
   df -h /path/to/artifacts
   
   # Check S3 bucket limits
   aws s3api get-bucket-location --bucket your-bucket
   ```

2. **MongoDB GridFS Issues**
   ```bash
   # Check GridFS collections
   mongo artifacts --eval "db.fs.files.find().count()"
   mongo artifacts --eval "db.fs.chunks.find().count()"
   ```

3. **S3 Permission Issues**
   ```bash
   # Test S3 access
   aws s3 ls s3://your-bucket/
   aws s3 cp test.txt s3://your-bucket/test.txt
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable service-specific debugging
logging.getLogger('google_adk_extras.artifacts').setLevel(logging.DEBUG)
```

### Performance Tuning

- **SQL**: Use appropriate indexes, connection pooling, and batch operations
- **MongoDB**: Optimize GridFS chunk size, create proper indexes
- **Local Storage**: Use fast storage devices, appropriate directory structure
- **S3**: Use appropriate storage classes, enable transfer acceleration
