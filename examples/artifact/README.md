# Artifact Services Examples

This directory contains examples for all custom artifact service implementations.

## Examples

- [`sql_artifact_example.py`](sql_artifact_example.py) - SQLArtifactService (SQLite)
- [`mongodb_artifact_example.py`](mongodb_artifact_example.py) - MongoArtifactService (MongoDB)
- [`local_folder_artifact_example.py`](local_folder_artifact_example.py) - LocalFolderArtifactService (File-based)
- [`s3_artifact_example.py`](s3_artifact_example.py) - S3ArtifactService (AWS S3)

## Requirements

- Python 3.10+
- Google ADK installed
- For MongoDB example: Running MongoDB instance
- For S3 example: AWS credentials configured

## Running Examples

To run any example:

```bash
cd /path/to/google-adk-extras
uv run python examples/artifact/[example_name].py
```

For example:
```bash
uv run python examples/artifact/sql_artifact_example.py
uv run python examples/artifact/mongodb_artifact_example.py
uv run python examples/artifact/local_folder_artifact_example.py
uv run python examples/artifact/s3_artifact_example.py
```

## Notes

- MongoDB and S3 examples will be skipped if their respective services aren't configured
- All examples use temporary files/databases where possible to avoid side effects
- Examples demonstrate artifact operations: save, load, list keys, list versions
- Both text and binary artifacts are demonstrated