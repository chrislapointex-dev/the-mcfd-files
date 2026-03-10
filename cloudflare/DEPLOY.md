# Cloudflare Deployment Guide — The MCFD Files

## Prerequisites

- Cloudflare account with a domain added
- `cloudflared` CLI installed on the Mac Mini: `brew install cloudflared`
- Docker running on Mac Mini (backend + DB)
- Domain pointed to Cloudflare nameservers

---

## Frontend — Cloudflare Pages

### Build settings (set in Cloudflare Pages dashboard)

| Setting | Value |
|---------|-------|
| Framework preset | Vite |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `frontend` |

### Environment variables (set in Pages dashboard)

| Variable | Value |
|----------|-------|
| `NODE_VERSION` | `20` |

### _redirects file

Before deploying, edit `frontend/public/_redirects` — replace `themcfdfiles.ca` with your actual domain:

```
/api/* https://api.themcfdfiles.ca/:splat 200
```

This proxies all `/api/*` requests from the frontend to your backend tunnel URL.
Commit the updated file before pushing.

---

## Backend — Cloudflare Tunnel (Mac Mini)

### 1. Authenticate cloudflared

```bash
cloudflared tunnel login
```

### 2. Create the tunnel

```bash
cloudflared tunnel create mcfd-files
# Note the tunnel ID printed — copy it
```

### 3. Configure the tunnel

Edit `cloudflare/tunnel-config.yml` — replace `<TUNNEL_ID>` and `themcfdfiles.ca`:

```yaml
tunnel: <paste-tunnel-id-here>
credentials-file: /root/.cloudflared/<paste-tunnel-id-here>.json

ingress:
  - hostname: api.themcfdfiles.ca
    service: http://localhost:8000
  - service: http_status:404
```

### 4. Add DNS record

```bash
cloudflared tunnel route dns mcfd-files api.themcfdfiles.ca
```

### 5. Run the tunnel

```bash
cloudflared tunnel --config cloudflare/tunnel-config.yml run mcfd-files
```

To run as a persistent service:

```bash
sudo cloudflared service install --config /path/to/cloudflare/tunnel-config.yml
sudo launchctl start com.cloudflare.cloudflared
```

---

## Backend Security — API Key

### Generate a key

```bash
openssl rand -hex 32
```

### Set it in .env

```bash
echo "MCFD_API_KEY=<generated-key>" >> .env
```

### Restart the backend

```bash
docker-compose restart backend
```

### Use the key in requests

All protected endpoints require the header:

```
X-API-Key: <your-key>
```

The Cloudflare Pages frontend sends this automatically if you set `VITE_API_KEY` as an environment
variable in the Pages dashboard and pass it in fetch headers. Or use a Cloudflare Worker to inject
the header transparently.

---

## Public vs. Protected Endpoints

### Public (no key required)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Health check |
| `GET /api/costs` | Cost calculator data |
| `GET /api/costs/scale` | BC scale projection |
| `GET /api/export/media-package` | Public media package JSON |

### Protected (require `X-API-Key` header in production)

- All `/api/contradictions/*`
- All `/api/crossexam/*`
- All `/api/witnesses/*`
- All `/api/search/*`
- All `/api/vault/*`
- All `/api/timeline/*`
- All `/api/patterns/*`
- All `/api/decisions/*`
- All `/api/ask/*`
- All `/api/brain/*`
- `GET /api/export/trial-package`
- `GET /api/export/trial-summary`
- `GET /api/export/trial-report.md`
- `GET /api/export/trial-report.pdf`

### Dev mode

Leave `MCFD_API_KEY` unset (or empty) in `.env` — all endpoints open. No restart needed to switch.

---

## Verification

```bash
# Health check
curl https://api.themcfdfiles.ca/api/health

# Public endpoint — no key
curl https://api.themcfdfiles.ca/api/costs

# Protected endpoint — no key (should return 401)
curl https://api.themcfdfiles.ca/api/contradictions

# Protected endpoint — with key (should return 200)
curl -H "X-API-Key: <your-key>" https://api.themcfdfiles.ca/api/contradictions
```

---

## Checklist Before Going Public

- [ ] Domain added to Cloudflare
- [ ] `_redirects` updated with real domain
- [ ] Cloudflare Pages project created and connected to GitHub
- [ ] `cloudflared` installed and authenticated on Mac Mini
- [ ] Tunnel created and DNS record added
- [ ] `MCFD_API_KEY` set in `.env` and backend restarted
- [ ] All protected endpoints return 401 without key
- [ ] All public endpoints return 200 without key
- [ ] Frontend loads at `https://themcfdfiles.ca`
- [ ] `/share` page loads without any key
