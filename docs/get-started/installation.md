---
title: Installation
---

# Installation

Install the core package:

```bash
pip install google-adk-extras
```

Optional backends (install what you need):

```bash
# MongoDB
pip install google-adk-extras[mongodb]

# Redis
pip install google-adk-extras[redis]

# S3
pip install google-adk-extras[s3]

# Everything
pip install google-adk-extras[all]
```

From source (dev):

```bash
git clone https://github.com/DeadMeme5441/google-adk-extras.git
cd google-adk-extras
uv sync   # or: pip install -e .
```

Verify your environment:

- Python 3.12+
- google-adk installed automatically as a dependency
- Optional: database or services (Postgres, Redis, Mongo, AWS) if you plan to use them
