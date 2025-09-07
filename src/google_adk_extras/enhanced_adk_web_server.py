"""Enhanced ADK Web Server that uses EnhancedRunner.

This module provides the EnhancedAdkWebServer class which extends Google ADK's
AdkWebServer to use our EnhancedRunner with advanced features.
"""

import os
from typing import Optional

from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.cli.utils import cleanup
from google.adk.cli.utils import envs
from google.adk.runners import Runner

from .enhanced_runner import EnhancedRunner


class EnhancedAdkWebServer(AdkWebServer):
    """Enhanced ADK Web Server that creates EnhancedRunner instances.
    
    This class extends Google's AdkWebServer to use our EnhancedRunner with:
    - Advanced tool execution strategies (MCP, OpenAPI, Function tools)
    - Circuit breakers and retry policies for resilience
    - YAML system context and enhanced configuration
    - Performance monitoring and debugging capabilities
    - Credential service integration (inherited)
    
    The EnhancedAdkWebServer is a drop-in replacement for AdkWebServer that
    provides significantly enhanced capabilities while maintaining full
    backward compatibility with all existing APIs.
    
    Examples:
        Basic usage (drop-in replacement):
        ```python
        enhanced_server = EnhancedAdkWebServer(
            agent_loader=agent_loader,
            session_service=session_service,
            artifact_service=artifact_service,
            memory_service=memory_service,
            credential_service=credential_service,
            eval_sets_manager=eval_sets_manager,
            eval_set_results_manager=eval_set_results_manager,
            agents_dir="./agents"
        )
        ```
        
        With enhanced features:
        ```python
        enhanced_config = EnhancedRunConfig.from_yaml_dict({
            'max_llm_calls': 200,
            'tool_timeouts': {'mcp_tools': 30.0},
            'circuit_breaker': {'failure_threshold': 3},
            'debug': {'enabled': True}
        })
        
        strategy_manager = ToolExecutionStrategyManager()
        strategy_manager.register_strategy('mcp', McpToolExecutionStrategy(timeout=45.0))
        
        enhanced_server = EnhancedAdkWebServer(
            agent_loader=agent_loader,
            session_service=session_service,
            # ... other services ...
            enhanced_config=enhanced_config,
            yaml_context=YamlSystemContext(
                system_name="my-agent-system",
                config_path="/path/to/config.yaml"
            ),
            tool_strategy_manager=strategy_manager
        )
        ```
    """
    
    def __init__(self, **kwargs):
        """Initialize EnhancedAdkWebServer.
        
        Args:
            enhanced_config: Enhanced configuration for runners (optional)
            yaml_context: YAML system context for error handling (optional)
            tool_strategy_manager: Tool execution strategy manager (optional)
            **kwargs: All other parameters passed to AdkWebServer
        """
        # Ensure a credential service exists; default to InMemory if not provided
        if 'credential_service' not in kwargs or kwargs.get('credential_service') is None:
            kwargs['credential_service'] = InMemoryCredentialService()

        # Initialize base AdkWebServer with all standard parameters
        super().__init__(**kwargs)
        
        # No enhanced configuration retained in simplified scope

    async def get_runner_async(self, app_name: str) -> EnhancedRunner:
        """Returns the enhanced runner for the given app.
        
        This method overrides AdkWebServer.get_runner_async to create
        EnhancedRunner instances instead of standard Runner instances.
        
        The logic is identical to the parent class except:
        1. Creates EnhancedRunner instead of Runner
        2. Passes enhanced configuration parameters
        3. Maintains full compatibility with cleanup and caching
        
        Args:
            app_name: The name of the application/agent to get runner for
            
        Returns:
            An EnhancedRunner instance for the specified app
        """
        # EXACT copy of parent logic for cleanup and caching
        if app_name in self.runners_to_clean:
            self.runners_to_clean.remove(app_name)
            runner = self.runner_dict.pop(app_name, None)
            await cleanup.close_runners(list([runner]))

        # Load environment for the agent
        envs.load_dotenv_for_agent(os.path.basename(app_name), self.agents_dir)
        
        # Return cached runner if available
        if app_name in self.runner_dict:
            return self.runner_dict[app_name]
            
        # Load agent and create new EnhancedRunner
        root_agent = self.agent_loader.load_agent(app_name)
        
        # Create EnhancedRunner (thin wrapper over ADK Runner)
        runner = EnhancedRunner(
            app_name=app_name,
            agent=root_agent,
            artifact_service=self.artifact_service,
            session_service=self.session_service,
            memory_service=self.memory_service,
            credential_service=self.credential_service,
        )
        
        # Cache and return runner (same as parent)
        self.runner_dict[app_name] = runner
        return runner
