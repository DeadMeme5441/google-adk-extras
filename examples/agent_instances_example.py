"""
Agent Instances Example

This example demonstrates how to use agent instances with the enhanced AdkBuilder
instead of relying only on directory-based agent discovery. This approach provides
programmatic control over agents and enables dynamic agent management.
"""

import asyncio
import logging
from typing import Dict

from google.adk.agents import Agent
from google.adk.runners import Runner

from google_adk_extras.adk_builder import AdkBuilder
from google_adk_extras.custom_agent_loader import CustomAgentLoader
from google_adk_extras.credentials.jwt_credential_service import JWTCredentialService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_agents() -> Dict[str, Agent]:
    """Create sample agents for demonstration."""
    
    # Customer support agent
    customer_support = Agent(
        name="customer_support",
        model="gemini-2.0-flash",
        instructions="""
        You are a helpful customer support agent. Help users with their questions
        about products, orders, and general inquiries. Be friendly and professional.
        """,
        tools=[],
    )
    
    # Technical support agent
    tech_support = Agent(
        name="tech_support", 
        model="gemini-2.0-flash",
        instructions="""
        You are a technical support specialist. Help users with technical issues,
        troubleshooting, and product configuration. Provide step-by-step guidance.
        """,
        tools=[],
    )
    
    # Sales agent
    sales_agent = Agent(
        name="sales_agent",
        model="gemini-2.0-flash", 
        instructions="""
        You are a sales representative. Help potential customers understand our
        products and services. Be persuasive but honest about product capabilities.
        """,
        tools=[],
    )
    
    return {
        "customer_support": customer_support,
        "tech_support": tech_support,
        "sales_agent": sales_agent,
    }


def example_basic_agent_instances():
    """Example 1: Basic agent instances with AdkBuilder."""
    logger.info("=== Example 1: Basic Agent Instances ===")
    
    # Create sample agents
    agents = create_sample_agents()
    
    # Build FastAPI app with agent instances
    app = (AdkBuilder()
           .with_agent_instance("customer_support", agents["customer_support"])
           .with_agent_instance("tech_support", agents["tech_support"])
           .with_agent_instance("sales_agent", agents["sales_agent"])
           .with_web_ui(True)
           .with_host_port("127.0.0.1", 8000)
           .build_fastapi_app())
    
    logger.info("FastAPI app created with 3 agent instances")
    logger.info("Available endpoints:")
    logger.info("- http://127.0.0.1:8000 (Web UI)")
    logger.info("- http://127.0.0.1:8000/agents (List agents)")
    
    return app


def example_bulk_agent_registration():
    """Example 2: Bulk agent registration."""
    logger.info("=== Example 2: Bulk Agent Registration ===")
    
    # Create sample agents
    agents = create_sample_agents()
    
    # Register all agents at once
    app = (AdkBuilder()
           .with_agents(agents)
           .with_web_ui(True)
           .with_host_port("127.0.0.1", 8001)
           .build_fastapi_app())
    
    logger.info("FastAPI app created with bulk agent registration")
    return app


def example_hybrid_agent_loading():
    """Example 3: Hybrid loading (instances + directory fallback)."""
    logger.info("=== Example 3: Hybrid Agent Loading ===")
    
    # Create dynamic agents
    dynamic_agent = Agent(
        name="dynamic_agent",
        model="gemini-2.0-flash",
        instructions="I am a dynamically created agent that overrides directory agents.",
        tools=[],
    )
    
    # Build app with both instance agents and directory fallback
    app = (AdkBuilder()
           .with_agents_dir("./agents")  # Directory-based agents (if they exist)
           .with_agent_instance("dynamic_agent", dynamic_agent)  # Takes priority
           .with_web_ui(True)
           .with_host_port("127.0.0.1", 8002)
           .build_fastapi_app())
    
    logger.info("FastAPI app created with hybrid agent loading")
    logger.info("Dynamic agents take priority over directory agents")
    return app


def example_custom_agent_loader():
    """Example 4: Using CustomAgentLoader directly."""
    logger.info("=== Example 4: Custom Agent Loader ===")
    
    # Create CustomAgentLoader manually
    custom_loader = CustomAgentLoader()
    
    # Register agents programmatically
    agents = create_sample_agents()
    for name, agent in agents.items():
        custom_loader.register_agent(name, agent)
    
    # Use custom loader with AdkBuilder
    app = (AdkBuilder()
           .with_agent_loader(custom_loader)
           .with_web_ui(True)
           .with_host_port("127.0.0.1", 8003)
           .build_fastapi_app())
    
    logger.info("FastAPI app created with custom agent loader")
    logger.info("Available agents: %s", custom_loader.list_agents())
    return app


def example_with_custom_credentials():
    """Example 5: Agent instances with custom credential service."""
    logger.info("=== Example 5: Agents with Custom Credentials ===")
    
    # Create JWT credential service
    jwt_service = JWTCredentialService(
        secret="your-jwt-secret-key",
        algorithm="HS256",
        issuer="agent-app"
    )
    
    # Create agents
    agents = create_sample_agents()
    
    # Build app with custom credentials
    app = (AdkBuilder()
           .with_agents(agents)
           .with_credential_service(jwt_service)
           .with_web_ui(True)
           .with_host_port("127.0.0.1", 8004)
           .build_fastapi_app())
    
    logger.info("FastAPI app created with JWT credential service")
    return app


async def example_dynamic_agent_management():
    """Example 6: Dynamic agent management at runtime."""
    logger.info("=== Example 6: Dynamic Agent Management ===")
    
    # Create initial agents
    initial_agents = {
        "agent1": Agent(
            name="agent1",
            model="gemini-2.0-flash",
            instructions="I am agent 1",
        )
    }
    
    # Create CustomAgentLoader for dynamic management
    loader = CustomAgentLoader()
    for name, agent in initial_agents.items():
        loader.register_agent(name, agent)
    
    logger.info("Initial agents: %s", loader.list_agents())
    
    # Simulate adding an agent dynamically
    new_agent = Agent(
        name="dynamic_agent",
        model="gemini-2.0-flash", 
        instructions="I was added dynamically!",
    )
    
    loader.register_agent("dynamic_agent", new_agent)
    logger.info("After adding dynamic agent: %s", loader.list_agents())
    
    # Test loading agents
    loaded_agent1 = loader.load_agent("agent1")
    loaded_dynamic = loader.load_agent("dynamic_agent")
    
    logger.info("Successfully loaded: %s, %s", loaded_agent1.name, loaded_dynamic.name)
    
    # Remove an agent
    result = loader.unregister_agent("agent1")
    logger.info("Removed agent1: %s", result)
    logger.info("Final agents: %s", loader.list_agents())
    
    return loader


def main():
    """Run all examples."""
    print("Agent Instances Examples")
    print("=" * 50)
    
    # Example 1: Basic agent instances
    app1 = example_basic_agent_instances()
    
    # Example 2: Bulk registration
    app2 = example_bulk_agent_registration()
    
    # Example 3: Hybrid loading
    app3 = example_hybrid_agent_loading()
    
    # Example 4: Custom agent loader
    app4 = example_custom_agent_loader()
    
    # Example 5: With custom credentials
    app5 = example_with_custom_credentials()
    
    # Example 6: Dynamic management (async)
    print("\nRunning dynamic agent management example...")
    asyncio.run(example_dynamic_agent_management())
    
    print(f"\nCreated {5} FastAPI applications demonstrating agent instances")
    print("To run any of these examples, modify the script to call uvicorn.run() with the desired app")
    print("\nExample usage:")
    print("    import uvicorn")
    print("    uvicorn.run(app1, host='127.0.0.1', port=8000)")


if __name__ == "__main__":
    main()