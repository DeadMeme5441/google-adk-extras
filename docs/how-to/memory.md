---
title: Memory (How‑To)
---

# Memory (How‑To)

Configure and search conversational memory.

## SQL

```python
from google_adk_extras.memory import SQLMemoryService
mem = SQLMemoryService("sqlite:///memory.db")
await mem.initialize()
```

Search:

```python
resp = await mem.search_memory(app_name="my_app", user_id="u1", query="calendar meeting")
for entry in resp.memories:
    print(entry.content)
```

Other backends: Redis, MongoDB, YAML files.

Notes

- SQL backend indexes extracted text content to enable simple term search.
- Large deployments should use a managed DB and periodic maintenance.

