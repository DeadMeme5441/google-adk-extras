"""
Dynamic Chatbot Example

This example demonstrates how to create a chatbot application that can dynamically
add and remove specialized agents based on user needs or business requirements.
This showcases the power of agent instances over static directory-based loading.
"""

import asyncio
import logging
from typing import Dict, List

from google.adk.agents import Agent
from google.adk.runners import Runner

from google_adk_extras.adk_builder import AdkBuilder
from google_adk_extras.custom_agent_loader import CustomAgentLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DynamicChatbotManager:
    """Manages a collection of specialized chatbot agents dynamically."""
    
    def __init__(self):
        self.agent_loader = CustomAgentLoader()
        self.app = None
        self._specialized_agents: Dict[str, Agent] = {}
    
    def create_specialized_agent(self, specialty: str, instructions: str) -> Agent:
        """Create a specialized agent for a specific domain."""
        agent = Agent(
            name=f"{specialty}_specialist",
            model="gemini-2.0-flash",
            instructions=f"""
            You are a {specialty} specialist. {instructions}
            
            Always introduce yourself as the {specialty} specialist and focus
            your responses on topics related to {specialty}.
            """,
            tools=[],
        )
        return agent
    
    def add_specialist(self, specialty: str, instructions: str) -> bool:
        """Add a new specialist agent."""
        try:
            agent = self.create_specialized_agent(specialty, instructions)
            agent_name = f"{specialty}_specialist"
            
            self.agent_loader.register_agent(agent_name, agent)
            self._specialized_agents[agent_name] = agent
            
            logger.info("Added specialist: %s", agent_name)
            return True
        except Exception as e:
            logger.error("Failed to add specialist %s: %s", specialty, e)
            return False
    
    def remove_specialist(self, specialty: str) -> bool:
        """Remove a specialist agent."""
        agent_name = f"{specialty}_specialist"
        
        if self.agent_loader.unregister_agent(agent_name):
            self._specialized_agents.pop(agent_name, None)
            logger.info("Removed specialist: %s", agent_name)
            return True
        else:
            logger.warning("Specialist not found: %s", agent_name)
            return False
    
    def list_specialists(self) -> List[str]:
        """List all available specialist agents."""
        return self.agent_loader.list_agents()
    
    def get_specialist_info(self) -> Dict[str, str]:
        """Get information about all specialists."""
        info = {}
        for agent_name in self.agent_loader.list_agents():
            source = self.agent_loader.get_agent_source(agent_name)
            info[agent_name] = source
        return info
    
    def build_app(self, host: str = "127.0.0.1", port: int = 8000):
        """Build the FastAPI application with current agents."""
        self.app = (AdkBuilder()
                   .with_agent_loader(self.agent_loader)
                   .with_web_ui(True)
                   .with_host_port(host, port)
                   .build_fastapi_app())
        
        logger.info("Built chatbot app with %d specialists", len(self.list_specialists()))
        return self.app


def setup_initial_specialists(manager: DynamicChatbotManager):
    """Set up initial set of specialist agents."""
    
    specialists = [
        {
            "specialty": "tech_support",
            "instructions": """
            Help users with technical problems, software issues, and troubleshooting.
            Provide step-by-step solutions and ask clarifying questions when needed.
            """
        },
        {
            "specialty": "product_info",
            "instructions": """
            Provide detailed information about products, features, specifications,
            and help users choose the right products for their needs.
            """
        },
        {
            "specialty": "billing",
            "instructions": """
            Assist with billing questions, payment issues, account management,
            and subscription-related inquiries. Be helpful and professional.
            """
        }
    ]
    
    for spec in specialists:
        success = manager.add_specialist(spec["specialty"], spec["instructions"])
        if success:
            logger.info("✓ Added %s specialist", spec["specialty"])
        else:
            logger.error("✗ Failed to add %s specialist", spec["specialty"])


async def demonstrate_dynamic_management():
    """Demonstrate dynamic agent management capabilities."""
    logger.info("=== Dynamic Agent Management Demo ===")
    
    manager = DynamicChatbotManager()
    
    # Initial setup
    setup_initial_specialists(manager)
    logger.info("Initial specialists: %s", manager.list_specialists())
    
    # Simulate business need for a new specialist
    logger.info("\n--- Adding new specialist based on customer demand ---")
    manager.add_specialist(
        "legal_advice",
        """
        Provide general legal information and guidance. Always remind users
        that this is not professional legal advice and they should consult
        with a qualified attorney for specific legal matters.
        """
    )
    
    logger.info("Updated specialists: %s", manager.list_specialists())
    
    # Show specialist sources
    logger.info("\n--- Specialist Information ---")
    for name, source in manager.get_specialist_info().items():
        logger.info("%s: loaded from %s", name, source)
    
    # Simulate removing a specialist (maybe seasonal or no longer needed)
    logger.info("\n--- Removing specialist due to business changes ---")
    manager.remove_specialist("billing")  # Maybe billing moved to external system
    
    logger.info("Final specialists: %s", manager.list_specialists())
    
    return manager


def main():
    """Main example runner."""
    print("Dynamic Chatbot Example")
    print("=" * 40)
    
    # Create and configure the chatbot manager
    manager = DynamicChatbotManager()
    
    # Set up initial specialists
    setup_initial_specialists(manager)
    
    # Build the FastAPI app
    app = manager.build_app(host="127.0.0.1", port=8000)
    
    print(f"\nChatbot ready with {len(manager.list_specialists())} specialists:")
    for specialist in manager.list_specialists():
        print(f"  • {specialist}")
    
    print("\nTo run this chatbot:")
    print("  1. import uvicorn")
    print("  2. uvicorn.run(app, host='127.0.0.1', port=8000)")
    print("  3. Open http://127.0.0.1:8000 in your browser")
    
    print("\nTo see dynamic management in action:")
    print("  Run: python -c \"import asyncio; from dynamic_chatbot_example import demonstrate_dynamic_management; asyncio.run(demonstrate_dynamic_management())\"")
    
    # Demonstrate dynamic management
    print("\n" + "=" * 40)
    asyncio.run(demonstrate_dynamic_management())


if __name__ == "__main__":
    main()