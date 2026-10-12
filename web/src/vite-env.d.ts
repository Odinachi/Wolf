/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The backend's URL, e.g. https://wolf-api.up.railway.app. Empty in development (Vite proxies /api). */
  readonly VITE_API_URL?: string;
  /** "true" shows sign-in (Log in / Get started); anything else shows the waitlist. */
  readonly VITE_ALLOW_AUTH?: string;
  readonly VITE_FIREBASE_API_KEY?: string;
  readonly VITE_FIREBASE_AUTH_DOMAIN?: string;
  readonly VITE_FIREBASE_PROJECT_ID?: string;
  readonly VITE_FIREBASE_APP_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
