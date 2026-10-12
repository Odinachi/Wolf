/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The backend's URL, e.g. https://wolf-api.up.railway.app. Empty in development (Vite proxies /api). */
  readonly API_URL?: string;
  /** "true" shows sign-in (Log in / Get started); anything else shows the waitlist. */
  readonly ALLOW_AUTH?: string;
  readonly FIREBASE_API_KEY?: string;
  readonly FIREBASE_AUTH_DOMAIN?: string;
  readonly FIREBASE_PROJECT_ID?: string;
  readonly FIREBASE_APP_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
