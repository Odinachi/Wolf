/**
 * The Wolf app schema.
 *
 * This is the contract between the web app (rendering and editing), the API (the AI agent edits
 * it) and the Flutter compiler (packages/flutter-codegen). Every component type and style field
 * here must map to Flutter; if you add one, add it to the compiler too.
 */

export const SCHEMA_VERSION = 1;

export type ComponentType =
  // Layout
  | 'Column'
  | 'Row'
  | 'Stack'
  | 'Container'
  | 'Card'
  | 'ListView'
  | 'Grid'
  | 'Spacer'
  | 'Divider'
  // Content
  | 'Text'
  | 'Image'
  | 'Icon'
  | 'Avatar'
  | 'Chip'
  | 'ListTile'
  | 'ProgressBar'
  // Input
  | 'Button'
  | 'IconButton'
  | 'TextField'
  | 'Switch'
  | 'Checkbox'
  | 'Slider'
  // Chrome
  | 'AppBar';

export type MainAxisAlignment = 'start' | 'center' | 'end' | 'spaceBetween' | 'spaceAround' | 'spaceEvenly';
export type CrossAxisAlignment = 'start' | 'center' | 'end' | 'stretch';

/** Visual properties. Numbers are logical pixels (Flutter dp). Colors are #RRGGBB or #AARRGGBB. */
export interface NodeStyle {
  padding?: number | [number, number, number, number]; // all, or [top, right, bottom, left]
  margin?: number | [number, number, number, number];
  width?: number | 'fill';
  height?: number;
  backgroundColor?: string;
  color?: string; // text / icon color
  fontSize?: number;
  fontWeight?: 400 | 500 | 600 | 700 | 800;
  textAlign?: 'left' | 'center' | 'right';
  borderRadius?: number;
  borderColor?: string;
  borderWidth?: number;
  elevation?: number;
  gap?: number; // space between children of Row / Column / Grid / ListView
  mainAxisAlignment?: MainAxisAlignment;
  crossAxisAlignment?: CrossAxisAlignment;
  /** Expand to fill remaining space in the parent Row / Column (Flutter Expanded). */
  expand?: boolean;
}

export type Action =
  | { type: 'navigate'; screenId: string }
  | { type: 'back' }
  | { type: 'openUrl'; url: string }
  | { type: 'snackbar'; message: string };

export interface Node {
  id: string;
  type: ComponentType;
  name?: string;
  props: Record<string, unknown>;
  style: NodeStyle;
  children: Node[];
  onTap?: Action;
}

export interface Screen {
  id: string;
  name: string;
  /** Root of the screen body: always a Column. */
  root: Node;
  backgroundColor?: string;
  /** Position of the frame on the design canvas. */
  frame: { x: number; y: number };
}

export type FieldType = 'string' | 'int' | 'double' | 'bool' | 'datetime' | 'image' | 'reference';

export interface DataField {
  id: string;
  name: string;
  type: FieldType;
  required: boolean;
  referenceModelId?: string;
}

export interface DataModel {
  id: string;
  name: string;
  fields: DataField[];
}

export interface Theme {
  brightness: 'light' | 'dark';
  primary: string;
  secondary: string;
  background: string;
  surface: string;
  text: string;
  mutedText: string;
  radius: number;
  fontFamily: string;
}

export interface NavigationTab {
  screenId: string;
  label: string;
  icon: string; // Material icon name, e.g. "home"
}

export interface Navigation {
  /** 'stack': screens push onto each other. 'tabs': a bottom navigation bar switches between tabs. */
  type: 'stack' | 'tabs';
  initialScreenId: string;
  tabs: NavigationTab[];
}

export type BackendProvider = 'none' | 'supabase' | 'firebase' | 'rest';

export interface BackendConfig {
  provider: BackendProvider;
  /** Supabase project URL, or REST base URL. */
  url?: string;
  /** Supabase anon key (public by design). Never put service-role keys or secrets here. */
  anonKey?: string;
  /** Firebase project id. */
  projectId?: string;
}

/** Wolf targets mobile apps. */
export type BuildPlatform = 'android' | 'ios';

export interface BuildConfig {
  appName: string;
  /** Reverse-DNS application id, e.g. com.example.myapp */
  bundleId: string;
  version: string;
  buildNumber: number;
  platforms: BuildPlatform[];
}

export interface AppSchema {
  version: typeof SCHEMA_VERSION;
  name: string;
  description: string;
  theme: Theme;
  screens: Screen[];
  dataModels: DataModel[];
  navigation: Navigation;
  backend: BackendConfig;
  build: BuildConfig;
}
