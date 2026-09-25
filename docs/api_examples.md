# API examples

Phase 1 exposes a health endpoint. The remaining endpoints will be added with the API phases.

```bash
curl http://localhost:8000/api/health
```

Expected shape:

```json
{
  "status": "ok",
  "service": "Fraud Command Center API",
  "environment": "development",
  "database": "connected"
}
```
