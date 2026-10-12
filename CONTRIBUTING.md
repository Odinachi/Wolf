# Contributing to Wolf

Thanks for helping build Wolf!

## Development

```bash
npm install && uv sync
npm run dev:api
npm run dev
```

Run all checks before opening a pull request:

```bash
npm run typecheck
npm test
```

## Guidelines

- Keep changes focused; one feature or fix per pull request.
- The app schema in `packages/schema` is the contract between the web app, the API and the
  Flutter compiler. If you change it, update all three and their tests.
- Write commit messages in the [Conventional Commits](https://www.conventionalcommits.org/) style
  (`feat(web): …`, `fix(api): …`).
