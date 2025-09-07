---
title: Service URI Cheatsheet
---

# Service URI Cheatsheet

Sessions

- SQL: `sqlite:///path.db`, `postgresql://user:pass@host/db`, `mysql://...`
- Redis: `redis://host:6379`
- MongoDB: `mongodb://host:27017/db`
- YAML: `yaml://./sessions`

Memory

- SQL: `sqlite:///memory.db`, `postgresql://...`
- Redis: `redis://host:6379`
- MongoDB: `mongodb://host:27017/db`
- YAML: `yaml://./memory`

Artifacts

- Local: `local://./artifacts`
- S3: `s3://bucket-name`
- SQL: `sqlite:///artifacts.db`, `postgresql://...`
- MongoDB: `mongodb://host:27017/db`

Credentials

- Google OAuth2: `oauth2-google://client_id:secret@scopes=openid,email`
- GitHub OAuth2: `oauth2-github://client_id:secret@scopes=user,repo`
- Microsoft OAuth2: `oauth2-microsoft://tenant/client_id:secret@scopes=User.Read`
- X OAuth2: `oauth2-x://client_id:secret@scopes=tweet.read`
- JWT: `jwt://secret@algorithm=HS256&issuer=...&audience=...&expiration_minutes=60`
- Basic: `basic-auth://username:password@realm=My%20API`

