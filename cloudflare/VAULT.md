# VAULT FILE DEPLOYMENT

## The Problem

`court-final.pdf` is 171MB — too large for git (GitHub limit: 100MB).
It is excluded via `.gitignore` (`data/vault/*.pdf`).
It must be present on the deployment host manually before going live.

---

## Current Location (local)

```
data/vault/court-final.pdf   (171MB)
```

---

## Options (choose one before deploying)

### Option A — Local host + Cloudflare Tunnel (RECOMMENDED for now)

If backend runs on Mac Mini with Cloudflare Tunnel:
- The file is already present locally at `data/vault/court-final.pdf`
- Docker Compose mounts `./data:/app/data` — no extra steps needed
- Verify it's visible inside the container:

```bash
docker exec the-mcfd-files-backend-1 ls -la /app/data/vault/
```

**No action needed.** The file is already there.

### Option B — SCP to remote host (if backend moves to VPS)

```bash
scp data/vault/court-final.pdf user@your-server:/path/to/app/data/vault/
```

### Option C — Cloudflare R2 (if backend moves to cloud)

1. Create R2 bucket: `mcfd-vault`
2. Upload `court-final.pdf` to bucket
3. Update `backend/app/routers/vault.py` to stream from R2
4. Set R2 credentials in environment

---

## Domain Placeholders — Update Before Go-Live

Three files need `YOUR-DOMAIN.ca` replaced with actual domain:

| File | Line | Replace with |
|------|------|-------------|
| `frontend/public/_redirects` | `/api/* https://api.YOUR-DOMAIN.ca/:splat 200` | actual domain |
| `cloudflare/tunnel-config.yml` | `hostname: api.YOUR-DOMAIN.ca` | actual domain |
| `cloudflare/DEPLOY.md` | multiple references | actual domain |

Domain registered: `themcfdfiles.ca` (update these files before deploying)

---

## Verify Vault Working

```bash
# Get key from .env
MCFD_KEY=$(grep MCFD_API_KEY .env | cut -d= -f2)

# Vault file accessible with auth:
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-API-Key: $MCFD_KEY" \
  http://localhost:8000/api/vault/court-final.pdf
# Expect: 200
```

---

## Pre-Deploy Checklist

- [ ] `court-final.pdf` present on host at `data/vault/`
- [ ] `MCFD_API_KEY` set in `.env` (and loaded into container)
- [ ] `YOUR-DOMAIN.ca` replaced in `_redirects`, `tunnel-config.yml`
- [ ] Cloudflare Tunnel running: `cloudflared tunnel run mcfd-files`
- [ ] Frontend deployed to Cloudflare Pages
- [ ] DNS propagated
- [ ] `/api/health` returns 200 via public domain
- [ ] `/share` loads with real data
