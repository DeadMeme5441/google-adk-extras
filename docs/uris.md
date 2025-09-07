# URIs & Configuration

Builder methods accept URIs for quick configuration.

## Sessions
- SQLite: `sqlite:///./sessions.db`
- Postgres: `postgresql://user:pass@host/db`
- MySQL: `mysql://user:pass@host/db`
- MongoDB: `mongodb://host:27017/db`
- Redis: `redis://localhost:6379`
- YAML: `yaml://./sessions`

## Artifacts
- Local folder: `local://./artifacts`
- S3: `s3://bucket-name`
- SQL / MongoDB: same schemes as sessions

## Memory
- YAML/Redis/SQL/MongoDB, same schemes as sessions

## Credentials
- Google OAuth2: `oauth2-google://client_id:secret@scopes=openid,email,profile`
- GitHub OAuth2: `oauth2-github://client_id:secret@scopes=user,repo`
- Microsoft OAuth2: `oauth2-microsoft://<tenant>/<client_id>:<secret>@scopes=User.Read`
- X OAuth2: `oauth2-x://client_id:secret@scopes=tweet.read,users.read`
- JWT: `jwt://<secret>@algorithm=HS256&issuer=my-app&expiration_minutes=60`
- HTTP Basic: `basic-auth://username:password@realm=My%20API`

Tips
- Use service instances when you need advanced options.
- Some backends require installing extras (`[sql]`, `[mongodb]`, `[redis]`, `[yaml]`, `[s3]`, `[jwt]`).
