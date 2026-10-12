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

**Backend**

```bash
cd backend
cp .env.example .env      # add your ANTHROPIC_API_KEY and OAuth app credentials
uv sync
uv run uvicorn wolf_api.main:app --reload --port 8000
```

Sign-in is **GitHub and Google only**. Create an OAuth app with either (or both) and put the
credentials in `backend/.env`. The callback URL to register is
`<WOLF_PUBLIC_URL>/api/auth/github/callback` (or `/google/callback`), which is
`http://localhost:5173/api/auth/github/callback` in development.

- GitHub: Settings → Developer settings → [OAuth Apps](https://github.com/settings/developers) → New OAuth App
- Google: Cloud Console → [Credentials](https://console.cloud.google.com/apis/credentials) → Create OAuth client ID → Web application

**Web**

```bash
cd web
npm install
npm run dev               # http://localhost:5173, proxies /api to the backend
```

If port 8000 is taken, run the backend on another port and start the web app with
`WOLF_API_PORT=8010 npm run dev`.

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
