import { createNode, newId } from './tree';
import { SCHEMA_VERSION, type AppSchema, type Screen, type Theme } from './types';

export const DEFAULT_THEME: Theme = {
  brightness: 'light',
  primary: '#6750A4',
  secondary: '#625B71',
  background: '#FFFBFE',
  surface: '#FFFFFF',
  text: '#1C1B1F',
  mutedText: '#49454F',
  radius: 12,
  fontFamily: 'Inter',
};

/** Canvas spacing between screen frames. */
export const FRAME_GAP = 120;
export const FRAME_WIDTH = 390;
export const FRAME_HEIGHT = 844;

export function createScreen(name: string, index = 0): Screen {
  return {
    id: newId(),
    name,
    root: createNode('Column', { name: 'Screen', style: { padding: 16, gap: 12 } }),
    frame: { x: index * (FRAME_WIDTH + FRAME_GAP), y: 0 },
  };
}

function slug(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '') || 'app';
}

export function createBlankSchema(name: string, description = ''): AppSchema {
  const home = createScreen('Home');
  return {
    version: SCHEMA_VERSION,
    name,
    description,
    theme: DEFAULT_THEME,
    screens: [home],
    dataModels: [],
    navigation: { type: 'stack', initialScreenId: home.id, tabs: [] },
    backend: { provider: 'none' },
    build: {
      appName: name,
      bundleId: `com.wolf.${slug(name)}`,
      version: '1.0.0',
      buildNumber: 1,
      platforms: ['android', 'ios', 'web'],
    },
  };
}
