import { getApp, getApps, initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const firebaseConfigured = Object.values(firebaseConfig).every(Boolean);

export const firebaseAuth = firebaseConfigured
  ? getAuth(
      getApps().length > 0
        ? getApp()
        : initializeApp(firebaseConfig),
    )
  : null;

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";
