# Phase 1: Enhanced Runner Foundation

## Overview

Phase 1 of the Enhanced ADK Runner system provides a solid foundation for YAML-driven agent systems with advanced configurability, robust error handling, and flexible tool execution strategies. This phase extends Google ADK's Runner with enhanced capabilities while maintaining full backward compatibility.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      EnhancedRunner                             │
├─────────────────────────────────────────────────────────────────┤
│ • Extends Google ADK Runner                                     │
│ • YAML-driven configuration                                     │
│ • Rich error handling with context                             │
│ • Performance metrics collection                               │
│ • Configurable tool execution strategies                       │
└─────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
         ┌──────────▼──────────┐   │    ┌─────────▼─────────┐
         │  EnhancedRunConfig  │   │    │ YamlSystemContext │
         ├─────────────────────┤   │    ├───────────────────┤
         │ • YAML config       │   │    │ • System tracking │
         │ • Tool timeouts     │   │    │ • Error context   │
         │ • Retry policies    │   │    │ • Location info   │
         │ • Debug settings    │   │    └───────────────────┘
         └─────────────────────┘   │
                                    │
                    ┌───────────────▼───────────────┐
                    │    ToolExecutionStrategy      │
                    │         Manager               │
                    ├───────────────────────────────┤
                    │ • Strategy routing            │
                    │ • MCP/OpenAPI/Function tools  │
                    │ • Timeout & retry management  │
                    │ • Circuit breaker pattern     │
                    └───────────────────────────────┘
```

## Core Components

### 1. EnhancedRunner

The main runner class that extends Google ADK's Runner with enhanced capabilities.

**Key Features:**
- Drop-in replacement for ADK's Runner
- YAML-driven configuration support
- Rich error handling with system context
- Performance metrics collection
- Configurable tool execution strategies

**Basic Usage:**
```python
from google_adk_extras.runners import EnhancedRunner, EnhancedRunConfig

# Drop-in replacement usage
runner = EnhancedRunner(
    app_name="my-agent-system",
    agent=my_agent,
    session_service=session_service,
)

# With enhanced configuration
enhanced_config = EnhancedRunConfig.from_yaml_dict({
    'max_llm_calls': 200,
    'tool_timeouts': {'mcp_tools': 30.0},
    'debug': {'enabled': True}
})

runner = EnhancedRunner(
    app_name="yaml-system",
    agent=my_agent,
    session_service=session_service,
    enhanced_config=enhanced_config
)
```

### 2. EnhancedRunConfig

A comprehensive configuration class that extends ADK's RunConfig with YAML support and advanced features.

**Configuration Structure:**
```yaml
# Basic ADK settings
streaming_mode: "NONE"
max_llm_calls: 150

# Tool execution timeouts
tool_timeouts:
  mcp_tools: 30.0
  openapi_tools: 60.0
  function_tools: 10.0
  mcp_connection_timeout: 10.0
  openapi_connection_timeout: 15.0
  tool_specific_timeouts:
    slow_mcp_tool: 120.0
    critical_api: 5.0

# Retry policies for different operation types
retry_policies:
  default:
    max_attempts: 3
    strategy: "EXPONENTIAL_BACKOFF"
    base_delay: 1.0
    max_delay: 60.0
    jitter: true
  mcp_tools:
    max_attempts: 2
    strategy: "IMMEDIATE"
  openapi_tools:
    max_attempts: 4
    strategy: "FIXED_DELAY"
    base_delay: 2.0

# A2A (Agent-to-Agent) configuration
a2a_config:
  timeout: 30.0
  connection_pool_size: 10
  retry_config:
    max_attempts: 3
    strategy: "EXPONENTIAL_BACKOFF"

# Debug and development settings
debug:
  enabled: true
  trace_agent_flow: true
  trace_tool_execution: false
  performance_profiling: true
  log_level: "DEBUG"
  capture_exceptions: true

# Advanced features
enable_circuit_breaker: true
enable_tool_registry: true
enable_agent_registry: true
max_concurrent_tools: 5
tool_execution_queue_size: 100
validate_tool_configs: true
strict_mode: false
```

**Programmatic Usage:**
```python
from google_adk_extras.runners.config import EnhancedRunConfig

# From YAML dictionary
config = EnhancedRunConfig.from_yaml_dict(yaml_config)

# Direct creation
config = EnhancedRunConfig(
    base_config=RunConfig(max_llm_calls=200),
    tool_timeouts=ToolTimeoutConfig(mcp_tools=45.0),
    enable_circuit_breaker=True
)

# Configuration merging
updated_config = config.merge_with_yaml({
    'tool_timeouts': {'mcp_tools': 60.0},
    'enable_circuit_breaker': False
})
```

### 3. Error Handling System

Rich error handling with YAML system context for enhanced debugging.

**Error Classes:**
- `YamlSystemError`: Base error class with system context
- `ToolExecutionError`: Specific to tool execution failures
- `ConfigurationError`: Configuration-related errors
- `RegistryError`: Agent/tool registry errors

**YamlSystemContext:**
```python
from google_adk_extras.runners.errors import YamlSystemContext

context = YamlSystemContext(
    system_name="customer-support",
    config_path="/path/to/config.yaml",
    current_agent="main_agent",
    current_tool="extract_data",
    invocation_id="inv_123",
    session_id="sess_456",
    user_id="user_789"
)

# Context chaining
agent_context = context.with_agent("new_agent")
tool_context = agent_context.with_tool("new_tool")
```

**Error Usage:**
```python
from google_adk_extras.runners.errors import ToolExecutionError

try:
    # Tool execution
    result = await execute_tool()
except Exception as e:
    raise ToolExecutionError(
        "Tool execution failed due to timeout",
        context=context.with_tool("failing_tool"),
        original_error=e,
        tool_type="mcp",
        execution_time=30.5,
        timeout=30.0,
        suggested_fixes=[
            "Increase tool timeout in configuration",
            "Check MCP server connectivity"
        ]
    )
```

### 4. Tool Execution Strategies

Flexible tool execution system supporting different tool types with specific handling.

**Strategy Types:**
- `DefaultToolExecutionStrategy`: Basic tool execution with timeout and retry
- `McpToolExecutionStrategy`: MCP-specific handling with connection timeouts
- `OpenApiToolExecutionStrategy`: API tools with circuit breaker pattern
- `FunctionToolExecutionStrategy`: Python function tools with optimizations

**Usage:**
```python
from google_adk_extras.runners.strategies import (
    ToolExecutionStrategyManager,
    McpToolExecutionStrategy,
    OpenApiToolExecutionStrategy
)

# Custom strategy manager
manager = ToolExecutionStrategyManager()

# Register strategies
mcp_strategy = McpToolExecutionStrategy(
    timeout=45.0,
    connection_timeout=10.0,
    retry_config=RetryConfig(max_attempts=2)
)
manager.register_strategy('mcp', mcp_strategy)

openapi_strategy = OpenApiToolExecutionStrategy(
    timeout=60.0,
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3)
)
manager.register_strategy('openapi', openapi_strategy)

# Use with runner
runner = EnhancedRunner(
    app_name="custom-strategy-app",
    agent=agent,
    session_service=session_service,
    tool_strategy_manager=manager
)
```

**Circuit Breaker Pattern:**
```python
from google_adk_extras.runners.strategies import CircuitBreaker, CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,      # Open circuit after 5 failures
    recovery_timeout=60.0,    # Wait 60s before trying half-open
    success_threshold=3,      # Need 3 successes to close circuit
    timeout=30.0             # Individual request timeout
)

circuit_breaker = CircuitBreaker(config)

# Check if can execute
if circuit_breaker.can_execute():
    try:
        result = await execute_operation()
        circuit_breaker.record_success()
    except Exception:
        circuit_breaker.record_failure()
        raise
```

**Retry System:**
```python
from google_adk_extras.runners.strategies import RetryExecutor, RetryConfig, RetryStrategy

retry_config = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=1.0,
    max_delay=60.0,
    backoff_multiplier=2.0,
    jitter=True
)

executor = RetryExecutor(retry_config)

result = await executor.execute(async_operation)
```

## Performance Monitoring

Built-in performance metrics collection for monitoring system health.

**Available Metrics:**
- `total_invocations`: Total number of runner invocations
- `total_tool_executions`: Total tool executions
- `avg_invocation_time`: Average invocation time
- `avg_tool_execution_time`: Average tool execution time
- `error_count`: Total number of errors
- `error_rate`: Error rate (errors / total invocations)
- `success_rate`: Success rate (1 - error_rate)

**Usage:**
```python
# Get performance metrics
metrics = runner.get_performance_metrics()
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Average invocation time: {metrics['avg_invocation_time']:.2f}s")

# Reset metrics
runner.reset_performance_metrics()

# Get debug information
debug_info = runner.get_debug_info()
print(debug_info['performance_metrics'])
```

## Integration with Agent-Compose-Kit

The Enhanced Runner is designed for seamless integration with agent-compose-kit's YAML-driven systems.

**Agent-Compose-Kit Configuration:**
```yaml
# In agent-compose-kit config
runtime:
  streaming_mode: "NONE"
  max_llm_calls: 200
  tool_timeouts:
    mcp_tools: 30.0
    openapi_tools: 60.0
  retry_policies:
    default:
      max_attempts: 3
      strategy: "EXPONENTIAL_BACKOFF"
  debug:
    enabled: true
    trace_agent_flow: true
```

**Integration Code:**
```python
# In agent-compose-kit integration
from google_adk_extras.runners import EnhancedRunner, EnhancedRunConfig

def create_enhanced_runner(system_config, agent, services):
    # Extract runtime configuration
    runtime_config = system_config.get('runtime', {})
    
    # Create enhanced config
    enhanced_config = EnhancedRunConfig.from_yaml_dict(runtime_config)
    
    # Create YAML context
    yaml_context = YamlSystemContext(
        system_name=system_config['name'],
        config_path=system_config['_config_path'],
        current_agent=system_config['agents'][0]['name']
    )
    
    # Create enhanced runner
    return EnhancedRunner(
        app_name=system_config['name'],
        agent=agent,
        session_service=services['session'],
        artifact_service=services.get('artifact'),
        memory_service=services.get('memory'),
        enhanced_config=enhanced_config,
        yaml_context=yaml_context
    )
```

## Error Debugging

Enhanced error messages with full context for easier debugging.

**Error Message Example:**
```
[customer-support -> agent:main_agent -> tool:extract_data] Tool execution timed out (tool_type: mcp) (executed for 30.5s, timeout: 30.0s)
  Caused by: ConnectionError: Connection to MCP server failed
  Error Code: TOOL_TIMEOUT_001
  Suggested fixes:
    1. Increase tool timeout in configuration
    2. Check MCP server connectivity  
    3. Verify network configuration
    4. Review MCP server logs
```

**Debug Information:**
```python
try:
    result = await runner.run_async(...)
except YamlSystemError as e:
    debug_info = e.get_debug_info()
    
    print(f"Error Type: {debug_info['error_type']}")
    print(f"System: {debug_info['context']['system_name']}")
    print(f"Agent: {debug_info['context']['current_agent']}")
    print(f"Tool: {debug_info['context']['current_tool']}")
    print(f"Invocation: {debug_info['context']['invocation_id']}")
    
    if debug_info.get('original_error'):
        print(f"Original Error: {debug_info['original_error']['type']}")
        print("Traceback:", debug_info['original_error']['traceback'])
```

## Configuration Management

Dynamic configuration updates and merging capabilities.

**Runtime Configuration Updates:**
```python
# Update configuration at runtime
runner.merge_config_from_yaml({
    'tool_timeouts': {'mcp_tools': 60.0},
    'debug': {'trace_tool_execution': True},
    'max_concurrent_tools': 10
})

# Update YAML context
new_context = runner.yaml_context.with_agent("new_agent")
runner.update_yaml_context(new_context)

# Complete configuration replacement
new_config = EnhancedRunConfig.from_yaml_dict(new_yaml_config)
runner.update_enhanced_config(new_config)
```

## Best Practices

### 1. Configuration Organization
```python
# Organize configurations by environment
dev_config = {
    'debug': {'enabled': True, 'trace_agent_flow': True},
    'tool_timeouts': {'mcp_tools': 60.0},  # Longer timeouts for development
    'strict_mode': False
}

prod_config = {
    'debug': {'enabled': False, 'performance_profiling': True},
    'tool_timeouts': {'mcp_tools': 30.0},
    'enable_circuit_breaker': True,
    'strict_mode': True
}
```

### 2. Error Handling
```python
# Always provide context in error handling
try:
    result = await runner.run_async(...)
except YamlSystemError as e:
    logger.error(f"System error in {e.context.get_location_string()}: {e}")
    
    # Log debug info for investigation
    debug_info = e.get_debug_info()
    logger.debug(f"Full error context: {debug_info}")
    
    # Apply suggested fixes if available
    for fix in e.suggested_fixes:
        logger.info(f"Suggested fix: {fix}")
```

### 3. Performance Monitoring
```python
# Regular metrics collection
async def monitor_performance():
    while True:
        metrics = runner.get_performance_metrics()
        
        if metrics['error_rate'] > 0.1:  # 10% error rate
            logger.warning(f"High error rate: {metrics['error_rate']:.2%}")
        
        if metrics['avg_invocation_time'] > 5.0:  # 5 second average
            logger.warning(f"High latency: {metrics['avg_invocation_time']:.2f}s")
        
        await asyncio.sleep(60)  # Check every minute
```

### 4. Tool Strategy Configuration
```python
# Configure strategies based on tool characteristics
def configure_strategies(runner, tool_info):
    for tool_name, info in tool_info.items():
        if info['type'] == 'mcp':
            # Configure MCP tools with appropriate timeouts
            if info.get('slow', False):
                runner.enhanced_config.tool_timeouts.tool_specific_timeouts[tool_name] = 120.0
            
        elif info['type'] == 'openapi':
            # Configure API tools with circuit breakers for external services
            if info.get('external', False):
                # These will use circuit breaker by default
                pass
```

## Testing

Comprehensive test coverage with both unit and integration tests.

**Unit Tests:**
- `tests/unit/test_enhanced_runner_config.py`: Configuration system tests
- `tests/unit/test_enhanced_runner_errors.py`: Error handling tests  
- `tests/unit/test_enhanced_runner_strategies.py`: Strategy system tests
- `tests/unit/test_enhanced_runner.py`: Main runner tests

**Integration Tests:**
- `tests/integration/test_phase1_integration.py`: End-to-end integration tests

**Running Tests:**
```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=google_adk_extras.runners tests/
```

## API Reference

### EnhancedRunner

```python
class EnhancedRunner(Runner):
    def __init__(
        self,
        *,
        app_name: str,
        agent: BaseAgent,
        plugins: Optional[List[BasePlugin]] = None,
        artifact_service: Optional[BaseArtifactService] = None,
        session_service: BaseSessionService,
        memory_service: Optional[BaseMemoryService] = None,
        credential_service: Optional[BaseCredentialService] = None,
        enhanced_config: Optional[EnhancedRunConfig] = None,
        yaml_context: Optional[YamlSystemContext] = None,
        tool_strategy_manager: Optional[ToolExecutionStrategyManager] = None,
        tool_registry: Optional[Any] = None,
        agent_registry: Optional[Any] = None,
    )
    
    async def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        new_message: types.Content,
        state_delta: Optional[Dict[str, Any]] = None,
        run_config: Optional[RunConfig] = None,
    ) -> AsyncGenerator[Event, None]
    
    def get_performance_metrics(self) -> Dict[str, Any]
    def reset_performance_metrics(self) -> None
    def update_yaml_context(self, context: YamlSystemContext) -> None
    def update_enhanced_config(self, config: EnhancedRunConfig) -> None
    def merge_config_from_yaml(self, yaml_config: Dict[str, Any]) -> None
    def get_debug_info(self) -> Dict[str, Any]
```

### EnhancedRunConfig

```python
class EnhancedRunConfig(BaseModel):
    base_config: RunConfig
    tool_timeouts: ToolTimeoutConfig
    retry_policies: Dict[str, RetryConfig]
    a2a_config: A2AConfig
    enable_circuit_breaker: bool
    circuit_breaker_config: CircuitBreakerConfig
    enable_tool_registry: bool
    enable_agent_registry: bool
    max_concurrent_tools: int
    tool_execution_queue_size: int
    debug_config: DebugConfig
    validate_tool_configs: bool
    strict_mode: bool
    
    @classmethod
    def from_yaml_dict(cls, yaml_config: Dict[str, Any]) -> 'EnhancedRunConfig'
    
    def to_base_run_config(self) -> RunConfig
    def get_tool_timeout(self, tool_name: str, tool_type: str = "function") -> float
    def get_retry_config(self, operation_type: str = "default") -> RetryConfig
    def merge_with_yaml(self, yaml_config: Dict[str, Any]) -> 'EnhancedRunConfig'
```

### YamlSystemContext

```python
@dataclass
class YamlSystemContext:
    system_name: str
    config_path: Optional[Union[str, Path]] = None
    current_agent: Optional[str] = None
    current_tool: Optional[str] = None
    invocation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def with_agent(self, agent_name: str) -> 'YamlSystemContext'
    def with_tool(self, tool_name: str) -> 'YamlSystemContext'
    def with_invocation(self, invocation_id: str, session_id: str, user_id: str) -> 'YamlSystemContext'
    def add_context(self, key: str, value: Any) -> 'YamlSystemContext'
    def get_location_string(self) -> str
```

## Migration Guide

### From Standard ADK Runner

```python
# Before: Standard ADK Runner
from google.adk.runners import Runner

runner = Runner(
    app_name="my-app",
    agent=agent,
    session_service=session_service,
)

# After: Enhanced ADK Runner (drop-in replacement)
from google_adk_extras.runners import EnhancedRunner

runner = EnhancedRunner(
    app_name="my-app", 
    agent=agent,
    session_service=session_service,
    # No other changes required!
)
```

### Adding Enhanced Features

```python
# Add YAML configuration
enhanced_config = EnhancedRunConfig.from_yaml_dict(yaml_config)

runner = EnhancedRunner(
    app_name="my-app",
    agent=agent,
    session_service=session_service,
    enhanced_config=enhanced_config,  # Add enhanced config
    yaml_context=YamlSystemContext(   # Add context tracking
        system_name="my-system",
        config_path="/path/to/config.yaml"
    )
)
```

## Troubleshooting

### Common Issues

**1. Import Errors**
```python
# Make sure to import from the correct module
from google_adk_extras.runners import EnhancedRunner  # Correct
from google_adk_extras import EnhancedRunner  # Incorrect
```

**2. Configuration Validation Errors**
```python
# Enable strict mode to catch configuration errors early
config = EnhancedRunConfig.from_yaml_dict({
    'strict_mode': True,  # Will validate configurations strictly
    'validate_tool_configs': True  # Will validate tool configurations
})
```

**3. Performance Issues**
```python
# Monitor and adjust configuration
metrics = runner.get_performance_metrics()
if metrics['avg_invocation_time'] > 5.0:
    # Increase concurrent tools or adjust timeouts
    runner.merge_config_from_yaml({
        'max_concurrent_tools': 10,
        'tool_timeouts': {'mcp_tools': 45.0}
    })
```

**4. Circuit Breaker Issues**
```python
# Check circuit breaker state in debug info
debug_info = runner.get_debug_info()
for strategy_name, strategy in runner.tool_strategy_manager.strategies.items():
    if hasattr(strategy, 'circuit_breaker'):
        print(f"{strategy_name} circuit breaker state: {strategy.circuit_breaker.state}")
```

## Next Steps

Phase 1 provides the foundation for enhanced ADK Runner functionality. The next phases will build upon this foundation:

- **Phase 2**: Registry integration for dynamic agent/tool loading
- **Phase 3**: Advanced developer experience with debugging utilities and performance profiling

For more information about upcoming phases, see the project roadmap and phase-specific documentation.