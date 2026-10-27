# Hosting SmartPath

The goal is to publish the existing customer and staff experience without relying on a local Mac. This is a prepared deployment path, not a live service.

## Source and hosting

Use a private GitHub repository for this source. Give Render access to that repository. The proposed Blueprint uses `Dockerfile.hosted`, one Python process and a persistent disk mounted at `/var/data`. Keep it to one instance while using SQLite and the in-process reminder loop.

The proposed service and disk are paid resources. Review current pricing and obtain the owner’s agreement before creation. Do not substitute a temporary filesystem for persistent storage while claiming enquiries will survive restarts.

## Required server settings

| Setting | Purpose |
| --- | --- |
| `APP_ENV=public_demo` | Enables the hosted entry point |
| `AI_PROVIDER=ollama_cloud` | Selects the prepared hosted provider |
| `OLLAMA_URL=https://ollama.com` | Official HTTPS endpoint accepted by the hosted configuration |
| `OLLAMA_MODEL` | Exact available cloud model name, verified before release |
| `OLLAMA_API_KEY` | Server-only provider credential |
| `STAFF_TOKEN` | New shared password of at least 32 characters |
| `DATABASE_PATH=/var/data/smartpath.sqlite3` | Persistent application database |
| `HF_HOME=/var/data/models` | Persistent retrieval model cache |
| `STATIC_DIR=/app/static` | Built frontend path in the image |
| `AI_TIMEOUT_SECONDS=60` | Timeout per model request, not a total journey target |

Never enter actual credentials in the repository or frontend bundle. Configure secrets in the hosting dashboard. Do not reuse the local staff token; keep the new token separate from the public website link.

## Release checks

1. Build the Linux container and inspect actual build logs. A local frontend build does not establish that the Docker build passes.
2. Configure a fresh database and the persistent disk. Do not upload the developer’s existing enquiries.
3. Verify the selected hosted model with real structured-output requests and realistic conversations. The current tests mock provider responses.
4. Wait for `/api/ready` to report search and AI readiness. Retrieval models load on startup; the AI health check requires the configured model to be listed by the provider.
5. Test the public URL from an unsigned browser: homepage, catalogue, question/answer flow, course facts, no-match handoff and all quiz assets.
6. Verify staff requests fail without a token, succeed with the correct token, and show the correct enquiry, draft recipient and approved outbox message.
7. Restart the service and check that the test enquiry remains. Check reminders are processed once and honour stop states.
8. Check the actual interview network can open the public site. Do not promise access before testing.

The hosted entry point starts its own reminder polling task, so do not start a second scheduler. The outbox remains application storage; no payment processing or external email delivery is added.

## Demonstration limits

Public JSON mutations are limited to 64 KiB and 60 requests per minute per proxy-visible peer. Public conversation requests have a durable site-wide limit of 100 per UTC day. The peer limit can aggregate visitors behind a hosting proxy. These are modest demonstration safeguards, not a complete abuse-prevention system or proof of a bounded provider bill. Review limits, concurrency, monitoring, backup and retention policies before broader use.

## References

- https://render.com/docs/deploy-fastapi
- https://render.com/docs/disks
- https://render.com/docs/blueprint-spec
- https://docs.ollama.com/cloud
