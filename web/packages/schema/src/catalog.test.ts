import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { COMPONENTS } from './catalog';

// The backend's AI agent reads this catalog as JSON, so it is exported into the backend folder
// (which stays deployable on its own). Regenerate with: UPDATE_CATALOG=1 npm test (in web/)
const path = fileURLToPath(new URL('../../../../backend/src/wolf_api/agent/catalog.json', import.meta.url));
const expected = JSON.stringify(COMPONENTS, null, 2) + '\n';

describe('catalog.json', () => {
  it('is up to date with catalog.ts', () => {
    if (process.env.UPDATE_CATALOG) writeFileSync(path, expected);
    expect(readFileSync(path, 'utf8')).toBe(expected);
  });
});
