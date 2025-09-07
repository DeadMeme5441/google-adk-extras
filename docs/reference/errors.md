---
title: Error Types
---

# Error Types

## YamlSystemError

Base enhanced error with YAML system context.

## ToolExecutionError

Tool execution failure with type, execution time, timeout, and suggestions.

## ConfigurationError

Raised by configuration adapters/system on load/validation problems.

## RegistryError

Issues with agent/tool registries (missing agents/tools, validation failures).

Tip: call `get_debug_info()` on exceptions for rich context.

