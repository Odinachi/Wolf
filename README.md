# Wolf

Wolf is an open-source AI builder for mobile apps, in the spirit of Lovable but for phones.
Describe an app in plain words. Wolf designs the screens, data and navigation, lets you edit
every screen directly like a design tool, connects a database, and compiles it to **Flutter**.

> Status: early development.

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
npm run dev       # web app on :5173
```

## License

[MIT](LICENSE)
