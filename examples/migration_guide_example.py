"""
Migration Guide Example: From Directory-Based to Instance-Based Agents

This example demonstrates how to migrate from traditional directory-based
agent loading to the new instance-based approach, showing the benefits
and step-by-step migration process.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List

from google.adk.agents import Agent
from google.adk.cli.utils.agent_loader import AgentLoader

from google_adk_extras.adk_builder import AdkBuilder
from google_adk_extras.custom_agent_loader import CustomAgentLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationExample:
    """Demonstrates migration from directory-based to instance-based agents."""
    
    def __init__(self):
        self.agents_dir = "./sample_agents"
        self.ensure_sample_agents_exist()
    
    def ensure_sample_agents_exist(self):
        """Create sample agent directory structure if it doesn't exist."""
        agents_path = Path(self.agents_dir)
        if agents_path.exists():
            return
        
        logger.info("Creating sample agent directory structure...")
        
        # Create directory structure
        (agents_path / "customer_service").mkdir(parents=True, exist_ok=True)
        (agents_path / "sales_assistant").mkdir(parents=True, exist_ok=True)
        
        # Create customer service agent
        customer_service_content = '''
from google.adk.agents import Agent

root_agent = Agent(
    name="customer_service",
    model="gemini-2.0-flash",
    instructions="""
    You are a customer service representative. Help customers with their 
    questions, complaints, and requests in a friendly and professional manner.
    """,
    tools=[]
)
'''
        with open(agents_path / "customer_service" / "agent.py", "w") as f:
            f.write(customer_service_content)
        
        # Create sales assistant agent
        sales_assistant_content = '''
from google.adk.agents import Agent

root_agent = Agent(
    name="sales_assistant", 
    model="gemini-2.0-flash",
    instructions="""
    You are a sales assistant. Help potential customers understand our products
    and services, answer pricing questions, and guide them through the purchase process.
    """,
    tools=[]
)
'''
        with open(agents_path / "sales_assistant" / "agent.py", "w") as f:
            f.write(sales_assistant_content)
        
        logger.info("Sample agent directories created at: %s", agents_path.absolute())
    
    def demonstrate_old_approach(self):
        """Demonstrate the traditional directory-based approach."""
        logger.info("=== OLD APPROACH: Directory-Based Agents ===")
        
        # Traditional AdkBuilder usage (still works)
        app = (AdkBuilder()
               .with_agents_dir(self.agents_dir)
               .with_web_ui(True)
               .with_host_port("127.0.0.1", 8100)
               .build_fastapi_app())
        
        logger.info("✓ Created app with directory-based agents")
        logger.info("  Agents directory: %s", self.agents_dir)
        logger.info("  Limitations:")
        logger.info("    - Agents must be in specific directory structure")
        logger.info("    - Hard to dynamically modify agents")
        logger.info("    - Difficult to unit test individual agents")
        logger.info("    - No programmatic control over agent lifecycle")
        
        return app
    
    def create_equivalent_instances(self) -> Dict[str, Agent]:
        """Create agent instances equivalent to the directory agents."""
        logger.info("=== MIGRATION STEP: Creating Equivalent Instances ===")
        
        # Create agent instances programmatically
        customer_service = Agent(
            name="customer_service",
            model="gemini-2.0-flash",
            instructions="""
            You are a customer service representative. Help customers with their 
            questions, complaints, and requests in a friendly and professional manner.
            """,
            tools=[]
        )
        
        sales_assistant = Agent(
            name="sales_assistant",
            model="gemini-2.0-flash", 
            instructions="""
            You are a sales assistant. Help potential customers understand our products
            and services, answer pricing questions, and guide them through the purchase process.
            """,
            tools=[]
        )
        
        agents = {
            "customer_service": customer_service,
            "sales_assistant": sales_assistant,
        }
        
        logger.info("✓ Created %d agent instances", len(agents))
        for name in agents.keys():
            logger.info("  - %s", name)
        
        return agents
    
    def demonstrate_new_approach(self, agents: Dict[str, Agent]):
        """Demonstrate the new instance-based approach."""
        logger.info("=== NEW APPROACH: Instance-Based Agents ===")
        
        # New AdkBuilder usage with instances
        app = (AdkBuilder()
               .with_agents(agents)  # Pass instances directly
               .with_web_ui(True)
               .with_host_port("127.0.0.1", 8101)
               .build_fastapi_app())
        
        logger.info("✓ Created app with instance-based agents")
        logger.info("  Benefits:")
        logger.info("    - Full programmatic control over agents")
        logger.info("    - Easy to unit test individual agents")
        logger.info("    - Dynamic agent management at runtime")
        logger.info("    - No file system dependencies")
        logger.info("    - Better integration with existing code")
        
        return app
    
    def demonstrate_hybrid_approach(self, agents: Dict[str, Agent]):
        """Demonstrate hybrid approach combining both methods."""
        logger.info("=== HYBRID APPROACH: Best of Both Worlds ===")
        
        # Add a dynamic agent that doesn't exist in directories
        dynamic_agent = Agent(
            name="dynamic_support",
            model="gemini-2.0-flash",
            instructions="""
            You are a specialized dynamic support agent that was created
            programmatically and takes priority over directory agents.
            """,
            tools=[]
        )
        
        # Hybrid: Directory fallback + dynamic instances
        app = (AdkBuilder()
               .with_agents_dir(self.agents_dir)  # Directory fallback
               .with_agents(agents)               # Instance agents (take priority)
               .with_agent_instance("dynamic_support", dynamic_agent)  # Additional dynamic agent
               .with_web_ui(True)
               .with_host_port("127.0.0.1", 8102)
               .build_fastapi_app())
        
        logger.info("✓ Created hybrid app with both approaches")
        logger.info("  Features:")
        logger.info("    - Directory agents as fallback")
        logger.info("    - Instance agents take priority")
        logger.info("    - Can add dynamic agents at runtime")
        logger.info("    - Smooth migration path")
        
        return app
    
    def demonstrate_advanced_patterns(self):
        """Demonstrate advanced patterns with CustomAgentLoader."""
        logger.info("=== ADVANCED PATTERNS: Custom Agent Loader ===")
        
        # Create custom loader with advanced features
        loader = CustomAgentLoader()
        
        # Load existing directory agents as fallback
        directory_loader = AgentLoader(self.agents_dir)
        fallback_loader = CustomAgentLoader(fallback_loader=directory_loader)
        
        # Add dynamic agents
        specialized_agents = {
            "emergency_support": Agent(
                name="emergency_support",
                model="gemini-2.0-flash",
                instructions="Handle urgent customer issues with highest priority.",
                tools=[]
            ),
            "technical_specialist": Agent(
                name="technical_specialist",
                model="gemini-2.0-flash",
                instructions="Provide advanced technical support and troubleshooting.",
                tools=[]
            )
        }
        
        for name, agent in specialized_agents.items():
            fallback_loader.register_agent(name, agent)
        
        # Build app with custom loader
        app = (AdkBuilder()
               .with_agent_loader(fallback_loader)
               .with_web_ui(True)
               .with_host_port("127.0.0.1", 8103)
               .build_fastapi_app())
        
        logger.info("✓ Created advanced app with custom loader")
        logger.info("  Available agents: %s", fallback_loader.list_agents())
        logger.info("  Advanced Features:")
        logger.info("    - Custom loading logic")
        logger.info("    - Priority-based agent resolution")
        logger.info("    - Runtime agent management")
        logger.info("    - Extensible architecture")
        
        return app
    
    def show_migration_benefits(self):
        """Show the key benefits of migrating to instance-based agents."""
        logger.info("=== MIGRATION BENEFITS SUMMARY ===")
        
        benefits = [
            "🚀 Performance: No file system I/O for agent loading",
            "🧪 Testing: Easy to mock and test individual agents",
            "⚡ Dynamic: Add/remove agents at runtime",
            "🎯 Control: Full programmatic control over agent lifecycle", 
            "🔧 Integration: Better integration with existing applications",
            "📦 Deployment: No need to manage agent directory structures",
            "🔄 Migration: Gradual migration path with hybrid approach",
            "🛠️ Debugging: Easier to debug agent configuration issues"
        ]
        
        for benefit in benefits:
            logger.info("  %s", benefit)
    
    def cleanup(self):
        """Clean up sample agent directories."""
        import shutil
        if os.path.exists(self.agents_dir):
            shutil.rmtree(self.agents_dir)
            logger.info("Cleaned up sample agent directories")


def main():
    """Run the migration example."""
    print("Migration Guide: Directory-Based to Instance-Based Agents")
    print("=" * 60)
    
    migration = MigrationExample()
    
    try:
        # Step 1: Show old approach
        app_old = migration.demonstrate_old_approach()
        
        # Step 2: Create equivalent instances
        agents = migration.create_equivalent_instances()
        
        # Step 3: Show new approach
        app_new = migration.demonstrate_new_approach(agents)
        
        # Step 4: Show hybrid approach
        app_hybrid = migration.demonstrate_hybrid_approach(agents)
        
        # Step 5: Show advanced patterns
        app_advanced = migration.demonstrate_advanced_patterns()
        
        # Step 6: Show benefits
        migration.show_migration_benefits()
        
        print("\n" + "=" * 60)
        print("Migration Example Complete!")
        print("\nCreated 4 different FastAPI applications:")
        print("  1. Old (Directory-based): Port 8100")
        print("  2. New (Instance-based):  Port 8101")
        print("  3. Hybrid:                Port 8102") 
        print("  4. Advanced:              Port 8103")
        
        print("\nTo run any application:")
        print("  import uvicorn")
        print("  uvicorn.run(app_new, host='127.0.0.1', port=8101)")
        
    finally:
        # Clean up
        migration.cleanup()


if __name__ == "__main__":
    main()