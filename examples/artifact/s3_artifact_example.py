"""
S3 Artifact Service Example
===========================

This example demonstrates how to use the S3ArtifactService with Google ADK.

Note: This requires AWS credentials and an S3 bucket.
"""

import asyncio
from google.genai import types

# Import our custom artifact service
from google_adk_extras.artifacts import S3ArtifactService


async def main():
    """Demonstrate S3 artifact service functionality."""
    
    print("=== S3 Artifact Service Example ===")
    
    try:
        # Initialize the S3 artifact service
        # You would need to provide actual AWS credentials and bucket name
        service = S3ArtifactService(
            bucket_name="your-bucket-name",
            region_name="us-west-2"
        )
        await service.initialize()
        print("Initialized S3 artifact service")
        
        # Note: Actual usage would require valid AWS credentials
        print("S3 service initialized (requires AWS credentials and bucket)")
        
        # Clean up
        await service.cleanup()
        print("Cleaned up S3 artifact service")
        
    except Exception as e:
        print(f"S3 example skipped (requires AWS credentials): {e}")
    
    print("=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())