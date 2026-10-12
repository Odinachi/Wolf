# Wolf

Wolf is an open-source AI builder for mobile apps, in the spirit of Lovable but for phones.
Describe an app in plain words. Wolf designs the screens, data and navigation, lets you edit
every screen directly like a design tool, connects a database, and compiles it to **Flutter**.

> Status: early development. Today you can describe an app, watch Wolf generate its screens on
> live phone frames, refine it by chatting (click any element to scope a change), roll back any AI
> change, and export a Flutter project. Direct visual editing, database setup and builds in the UI
> are next.

## Repository layout

This is a monorepo. JavaScript packages use npm workspaces and Python packages use a uv workspace.

| Path | What it is |
|------|------------|
| `apps/web` | The web app (React + Vite): home prompt, projects, chat + canvas workspace |
| `apps/api` | The API (FastAPI): auth, projects, the AI agent, builds and deploys |
| `packages/schema` | The Wolf app schema shared by the web app (TypeScript) |
| `packages/flutter-codegen` | Compiles a Wolf app schema into a Flutter project (Python) |

## Getting started

Requirements: Node 20+, [uv](https://docs.astral.sh/uv/), and optionally the
[Flutter SDK](https://docs.flutter.dev/get-started/install) to build apps.

```bash
npm install
uv sync
cp apps/api/.env.example apps/api/.env   # add your ANTHROPIC_API_KEY
npm run dev:api   # API on :8000
npm run dev       # web app on :5173 (proxies /api to :8000)
```

If port 8000 is taken, run the API elsewhere and point the web app at it:
`WOLF_API_PORT=8010 npm run dev`.

## Useful commands

| Command | What it does |
|---------|--------------|
| `npm test` | Schema tests (Vitest) and API + compiler tests (pytest) |
| `npm run typecheck` | Type-checks every TypeScript package |
| `npm run assets -w @wolf/web` | Regenerates the favicons and OG image from `apps/web/public/logo.svg` |
| `UPDATE_CATALOG=1 npm test -w @wolf/schema` | Re-exports `packages/schema/catalog.json` after changing the component catalog |

The compiler tests run a real `flutter analyze` on generated apps when the Flutter SDK is installed.

## License

[MIT](LICENSE)
