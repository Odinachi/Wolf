# Wolf

Wolf is an open-source AI builder for mobile apps, in the spirit of Lovable but for phones.
Describe an app in plain words. Wolf designs the screens, data and navigation, lets you edit
every screen directly like a design tool, connects a database, and compiles it to **Flutter**.

> Status: early development. Today you can describe an app, watch Wolf generate its screens on
> live phone frames, refine it by chatting (click any element to scope a change), roll back any AI
> change, and export a Flutter project. Direct visual editing, database setup and builds in the UI
> are next.

## Repository layout

The backend and the frontend live side by side and can be developed and deployed independently.

| Path | What it is |
|------|------------|
| `backend/` | The API (FastAPI): auth, projects, the AI agent, builds and sharing. A uv workspace. |
| `backend/packages/flutter-codegen` | Compiles a Wolf app schema into a Flutter project (Python) |
| `web/` | The web app (React + Vite): landing page, projects, chat + canvas workspace. An npm workspace. |
| `web/packages/schema` | The Wolf app schema: types, component catalog and tree helpers (TypeScript) |

The component catalog is defined once in `web/packages/schema` and exported to
`backend/src/wolf_api/agent/catalog.json` for the AI agent; a test fails if the two drift.

## Getting started

Requirements: Node 20+, [uv](https://docs.astral.sh/uv/), and optionally the
[Flutter SDK](https://docs.flutter.dev/get-started/install) to build apps.

**Firebase (sign-in).** Wolf signs people in with GitHub or Google through Firebase Auth.
Create a project in the [Firebase console](https://console.firebase.google.com/), then:

1. Authentication → Sign-in method: enable **GitHub** and **Google** (only these are accepted).
   GitHub needs an OAuth app; Firebase shows the callback URL to register with it.
2. Project settings → Your apps → add a **Web app** and copy its config into `web/.env`.
3. Put the project id in `backend/.env` (`FIREBASE_PROJECT_ID`).

**Backend**

```bash
cd backend
cp .env.example .env      # ANTHROPIC_API_KEY, FIREBASE_PROJECT_ID
uv sync
uv run uvicorn wolf_api.main:app --reload --port 8000
```

**Web**

```bash
cd web
cp .env.example .env      # the Firebase web config
npm install
npm run dev               # http://localhost:5173, proxies /api to the backend
```

If port 8000 is taken, run the backend on another port and start the web app with
`WOLF_API_PORT=8010 npm run dev`.

## Deploying

The backend runs on [Railway](https://railway.com) (SQLite on a volume), files and backups live in
Firebase Storage, and the web app runs on [Vercel](https://vercel.com).

**Backend on Railway**

1. New service from this repo, with **Root Directory** `backend` (it builds `backend/Dockerfile`
   using `backend/railway.json`).
2. Add a **volume** mounted at `/data`.
3. Variables:
   - `ANTHROPIC_API_KEY`, `FIREBASE_PROJECT_ID`
   - `FIREBASE_STORAGE_BUCKET` and `FIREBASE_SERVICE_ACCOUNT` (Firebase → Project settings → Service
     accounts → Generate new private key; paste the JSON) to store build files in Firebase Storage
   - `LITESTREAM_BUCKET` (the same bucket) to continuously back up the database; a fresh volume
     restores from it automatically
   - `WOLF_CORS_ORIGINS`: your Vercel URL(s)
   - `WOLF_ACCESS_MODE=waitlist` and `WOLF_ALLOWED_EMAILS=you@example.com` until launch
   - optional: `WOLF_DAILY_GENERATION_LIMIT` (default 30 AI requests per user per day)
4. Generate a public domain for the service.

**Web on Vercel**

1. Import the repo with **Root Directory** `web` (settings come from `web/vercel.json`).
2. Environment variables: the `VITE_FIREBASE_*` values, `VITE_API_URL` (your Railway URL) and
   `VITE_SITE_URL` (your site's URL, for social previews).
3. In Firebase → Authentication → Settings → Authorized domains, add your Vercel domain.

**Waitlist.** With `WOLF_ACCESS_MODE=waitlist`, every way in on the landing page opens a waitlist
form, and the API refuses sign-in for everyone except `WOLF_ALLOWED_EMAILS` (enforced on the server,
not just hidden in the UI). Signups are stored in the `waitlist` table; to export them from Railway:

```bash
railway ssh -- sqlite3 -csv -header /data/wolf.db "select email, idea, created_at from waitlist"
```

Set `WOLF_ACCESS_MODE=open` (or remove it) when you launch.

## Useful commands

| Where | Command | What it does |
|-------|---------|--------------|
| `backend/` | `uv run pytest` | API and Flutter compiler tests (runs `flutter analyze` on generated apps if Flutter is installed) |
| `web/` | `npm test` | Schema package tests |
| `web/` | `npm run typecheck` | Type-checks the app and the schema package |
| `web/` | `npm run assets` | Regenerates favicons and the OG image from `public/logo.svg` |
| `web/` | `UPDATE_CATALOG=1 npm test` | Re-exports the component catalog to the backend after changing it |

## License

[MIT](LICENSE)
