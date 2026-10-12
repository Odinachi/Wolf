import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { COMPONENTS } from './catalog';

// catalog.json lets non-TypeScript consumers (the Python API's AI agent) share this catalog.
// Regenerate with: UPDATE_CATALOG=1 npm test -w @wolf/schema
const path = fileURLToPath(new URL('../catalog.json', import.meta.url));
const expected = JSON.stringify(COMPONENTS, null, 2) + '\n';

describe('catalog.json', () => {
  it('is up to date with catalog.ts', () => {
    if (process.env.UPDATE_CATALOG) writeFileSync(path, expected);
    expect(readFileSync(path, 'utf8')).toBe(expected);
  });
});
