export type WorkspaceSession = {
  token: string;
  mode: 'authenticated' | 'demo';
  user_id?: string;
};

export type StoredAuth = {
  session: WorkspaceSession;
  user: {
    id: string;
    name: string;
    email: string;
    created_at?: string;
  };
};

const AUTH_STORAGE_KEY = 'rag.auth';

export function readStoredAuth(): StoredAuth | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

export function writeStoredAuth(auth: StoredAuth) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

export function clearStoredAuth() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}
