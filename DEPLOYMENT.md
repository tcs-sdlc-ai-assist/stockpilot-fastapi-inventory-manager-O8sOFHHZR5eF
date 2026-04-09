# StockPilot Deployment Guide

## Deploying to Vercel

This guide covers deploying the StockPilot FastAPI application to Vercel's serverless platform.

---

## Prerequisites

1. **Vercel Account** — Sign up at [vercel.com](https://vercel.com) if you don't have one.
2. **Vercel CLI** (optional but recommended):
   ```bash
   npm install -g vercel
   ```
3. **Git Repository** — Your project should be pushed to GitHub, GitLab, or Bitbucket.
4. **Python 3.12** — Vercel's Python runtime must match the project's target version.

---

## Environment Variables

All environment variables must be configured in the Vercel dashboard under **Project Settings → Environment Variables** before deployment.

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | Cryptographic key for JWT signing and session security. Must be a long, random string. | `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9` |
| `DEFAULT_ADMIN_USERNAME` | **Yes** | Username for the initial admin account created on first startup. | `admin` |
| `DEFAULT_ADMIN_PASSWORD` | **Yes** | Password for the initial admin account. Must be strong in production. | `Ch@ng3M3!Str0ng#2024` |
| `DATABASE_URL` | **Yes** | Full connection string for the database. Use a hosted provider (e.g., Neon, PlanetScale, Supabase, Turso). | `sqlite+aiosqlite:///./stockpilot.db` or `postgresql+asyncpg://user:pass@host/db` |
| `ENVIRONMENT` | No | Deployment environment identifier. Defaults to `production`. | `production` |
| `CORS_ORIGINS` | No | Comma-separated list of allowed CORS origins. | `https://stockpilot.vercel.app` |

### Setting Environment Variables via Vercel CLI

```bash
vercel env add SECRET_KEY production
vercel env add DEFAULT_ADMIN_USERNAME production
vercel env add DEFAULT_ADMIN_PASSWORD production
vercel env add DATABASE_URL production
```

### Generating a Secure SECRET_KEY

```bash
# Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Using OpenSSL
openssl rand -hex 32
```

> ⚠️ **SECURITY WARNING:** Never commit secrets to version control. Never reuse the same `SECRET_KEY` across environments. Rotate keys periodically in production.

---

## vercel.json Explanation

The `vercel.json` file at the project root configures how Vercel builds and routes the application:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/app/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### Configuration Breakdown

| Key | Purpose |
|---|---|
| `builds[0].src` | Points to the FastAPI entry point (`app/main.py`). Vercel looks for the ASGI `app` object here. |
| `builds[0].use` | Specifies the `@vercel/python` builder, which installs dependencies from `requirements.txt` and packages the serverless function. |
| `routes[0]` | Routes static file requests (`/static/*`) directly to the static directory, bypassing the Python runtime for better performance. |
| `routes[1]` | Catches all other requests and forwards them to the FastAPI application for dynamic handling. |

### Important Notes on vercel.json

- The **order of routes matters** — more specific routes (like `/static/`) must come before the catch-all `/(.*)`
- The `@vercel/python` builder automatically detects `requirements.txt` in the project root
- Vercel expects the ASGI application object to be named `app` in the entry point module

---

## Deployment Steps

### Option A: Deploy via Vercel Dashboard (Recommended)

1. **Push your code** to a Git repository (GitHub, GitLab, or Bitbucket).

2. **Import the project** in the Vercel dashboard:
   - Go to [vercel.com/new](https://vercel.com/new)
   - Select your repository
   - Vercel auto-detects the framework settings from `vercel.json`

3. **Configure environment variables:**
   - Navigate to **Settings → Environment Variables**
   - Add all required variables listed above
   - Select the appropriate environments (Production, Preview, Development)

4. **Deploy:**
   - Click **Deploy**
   - Vercel will install dependencies, build the project, and deploy the serverless function

5. **Verify:**
   - Visit your deployment URL (e.g., `https://stockpilot-xxxx.vercel.app`)
   - Check the `/docs` endpoint for the interactive API documentation
   - Verify the admin account was created by logging in

### Option B: Deploy via Vercel CLI

```bash
# 1. Login to Vercel
vercel login

# 2. Link your project (first time only)
vercel link

# 3. Set environment variables (first time only)
vercel env add SECRET_KEY production
vercel env add DEFAULT_ADMIN_USERNAME production
vercel env add DEFAULT_ADMIN_PASSWORD production
vercel env add DATABASE_URL production

# 4. Deploy to preview
vercel

# 5. Deploy to production
vercel --prod
```

### Option C: Automatic Deployments via Git

Once your project is linked in Vercel:

- **Production deployments** trigger automatically on pushes to the `main` branch
- **Preview deployments** trigger automatically on pull requests
- Each preview deployment gets a unique URL for testing

---

## Database Considerations

### SQLite (Development Only)

SQLite with `sqlite+aiosqlite:///` works for local development but **is not suitable for Vercel production** because:
- Vercel serverless functions have an ephemeral filesystem — data is lost between invocations
- Concurrent writes from multiple function instances cause locking errors

### Recommended Production Databases

| Provider | Connection String Format | Notes |
|---|---|---|
| **Neon (PostgreSQL)** | `postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require` | Free tier available, serverless-friendly |
| **Supabase (PostgreSQL)** | `postgresql+asyncpg://postgres:pass@db.xxx.supabase.co:5432/postgres` | Free tier available |
| **PlanetScale (MySQL)** | `mysql+aiomysql://user:pass@aws.connect.psdb.cloud/dbname?ssl=true` | Requires `aiomysql` in requirements.txt |
| **Turso (SQLite edge)** | Requires `libsql` adapter | Edge-distributed SQLite |

> 💡 **Tip:** For PostgreSQL providers, ensure `asyncpg` is in your `requirements.txt`. For MySQL, ensure `aiomysql` is listed.

---

## Troubleshooting

### 404 Not Found Errors

**Symptom:** All routes return 404 after deployment.

**Causes and Fixes:**

1. **Missing or incorrect `vercel.json` routes:**
   - Ensure the catch-all route `"src": "/(.*)"` points to the correct entry point
   - Verify the `dest` path matches your actual file structure

2. **Router prefix duplication:**
   - If a router defines `APIRouter(prefix="/api")` and `main.py` also adds `app.include_router(router, prefix="/api")`, routes become `/api/api/...`
   - Fix: Define the prefix in only ONE place

3. **Missing `app` object:**
   - Vercel looks for an ASGI object named `app` in the entry point
   - Ensure `app/main.py` exports `app = FastAPI(...)`

### Cold Start Latency

**Symptom:** First request after idle period takes 3–10 seconds.

**Causes and Mitigations:**

1. **Large dependency bundle:**
   - Minimize `requirements.txt` — remove unused packages
   - Avoid heavy packages (e.g., `torch`, `tensorflow`) unless absolutely necessary

2. **Startup initialization:**
   - Keep the lifespan handler lightweight
   - Defer heavy initialization (e.g., ML model loading) to first request or background tasks

3. **Database connection establishment:**
   - Use connection pooling with reasonable limits
   - Consider providers with serverless-optimized connection handling (Neon, PlanetScale)

4. **Vercel Pro/Enterprise:**
   - Upgrade for reduced cold start times and higher execution limits

### Static Files Not Loading

**Symptom:** CSS, JavaScript, or images return 404 or are served with wrong content type.

**Causes and Fixes:**

1. **Route ordering in `vercel.json`:**
   - Static file routes MUST come before the catch-all route
   - Verify the `dest` path matches the actual static directory location

2. **File not included in deployment:**
   - Check `.vercelignore` (if present) isn't excluding static files
   - Verify static files are committed to the repository

3. **Incorrect `StaticFiles` mount in FastAPI:**
   - Ensure the mount path matches what `vercel.json` routes expect:
     ```python
     app.mount("/static", StaticFiles(directory=static_path), name="static")
     ```
   - Use absolute paths resolved from `__file__` to avoid CWD issues

### 500 Internal Server Error

**Symptom:** Application crashes on startup or during requests.

**Debugging Steps:**

1. **Check Vercel Function Logs:**
   - Go to **Vercel Dashboard → Deployments → [latest] → Functions**
   - Click on the function to view runtime logs

2. **Common startup crashes:**
   - Missing environment variables → `ValidationError` from Pydantic Settings
   - Missing dependencies → `ModuleNotFoundError`
   - Database connection failure → `ConnectionRefusedError` or timeout

3. **Test locally with production settings:**
   ```bash
   # Simulate Vercel environment locally
   ENVIRONMENT=production \
   SECRET_KEY=test-secret-key \
   DEFAULT_ADMIN_USERNAME=admin \
   DEFAULT_ADMIN_PASSWORD=testpass123 \
   DATABASE_URL=sqlite+aiosqlite:///./test.db \
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Function Timeout

**Symptom:** Requests fail with 504 Gateway Timeout.

**Causes and Fixes:**

1. **Vercel Hobby plan limit:** 10-second execution limit
   - Optimize slow database queries (add indexes, reduce joins)
   - Paginate large result sets
   - Move heavy processing to background tasks

2. **Database query timeout:**
   - Ensure your database provider is in the same region as your Vercel deployment
   - Add connection timeout settings to your `DATABASE_URL`

---

## Security Warnings for Production

### Credentials

- **Change default admin credentials immediately** after first deployment. The `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` are only used to seed the initial account.
- **Use a strong `DEFAULT_ADMIN_PASSWORD`** — minimum 12 characters with uppercase, lowercase, numbers, and symbols.
- **Rotate `SECRET_KEY` periodically.** Changing the key invalidates all existing JWT tokens, forcing users to re-authenticate.
- **Never reuse credentials** across environments (development, staging, production).

### Environment Variables

- **Never commit `.env` files** to version control. Add `.env` to `.gitignore`.
- **Use Vercel's encrypted environment variables** — they are encrypted at rest and injected at runtime.
- **Scope variables to specific environments** (Production, Preview, Development) in the Vercel dashboard to prevent preview deployments from accessing production databases.

### CORS Configuration

- **Never use `allow_origins=["*"]` in production.** Restrict to your actual frontend domain(s):
  ```
  CORS_ORIGINS=https://stockpilot.vercel.app,https://www.stockpilot.com
  ```

### Database

- **Use SSL/TLS connections** for all production database connections. Most hosted providers require this by default (`?sslmode=require`).
- **Create a dedicated database user** with minimal required permissions — never use the root/admin database account.
- **Enable connection encryption** and verify certificates when possible.

### HTTPS

- Vercel provides automatic HTTPS with SSL certificates for all deployments. No additional configuration is needed.
- If using a custom domain, Vercel automatically provisions and renews SSL certificates.

---

## Post-Deployment Checklist

- [ ] Application loads without errors at the deployment URL
- [ ] `/docs` endpoint shows the interactive API documentation
- [ ] Admin account login works with the configured credentials
- [ ] Default admin password has been changed via the application
- [ ] CORS origins are restricted to your frontend domain(s)
- [ ] Database is hosted on a persistent provider (not local SQLite)
- [ ] Environment variables are scoped to the correct environments
- [ ] Function logs show no startup errors
- [ ] Static assets (CSS, JS, images) load correctly
- [ ] All API endpoints return expected responses