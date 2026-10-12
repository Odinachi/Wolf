# Contributing to Wolf

Thanks for helping build Wolf!

## Development

See the README for setup. The backend lives in `backend/` and the web app in `web/`.

Run all checks before opening a pull request:

```bash
cd backend && uv run pytest
cd web && npm run typecheck && npm test
```

## Guidelines

- Keep changes focused; one feature or fix per pull request.
- The app schema in `web/packages/schema` is the contract between the web app, the backend's AI
  agent and the Flutter compiler (`backend/packages/flutter-codegen`). If you change it, update all
  three and their tests, and re-export the catalog with `UPDATE_CATALOG=1 npm test` in `web/`.
- Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/) style
  (`feat(web): …`, `fix(api): …`).
