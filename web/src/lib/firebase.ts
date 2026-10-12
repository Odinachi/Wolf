import { initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

// Firebase web config is public by design; it identifies the project, it doesn't grant access.
const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

/** Whether sign-in is configured for this build (see web/.env.example). */
export const firebaseEnabled = Boolean(config.apiKey && config.authDomain && config.projectId);

let app: FirebaseApp | null = null;

export function firebaseAuth(): Auth | null {
  if (!firebaseEnabled) return null;
  app ??= initializeApp(config);
  return getAuth(app);
}

/** The signed-in user's ID token for the backend, refreshed by the SDK when it nears expiry. */
export async function idToken(): Promise<string | null> {
  return (await firebaseAuth()?.currentUser?.getIdToken()) ?? null;
}
