const CLIENT_KEY = "brainmed_client_key_v1";
const DISPLAY_NAME_KEY = "brainmed_display_name_v1";

export function getClientKey(): string {
  let key = localStorage.getItem(CLIENT_KEY);
  if (!key) {
    key =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `ck_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(CLIENT_KEY, key);
  }
  return key;
}

export function getDisplayName(): string {
  return localStorage.getItem(DISPLAY_NAME_KEY) || "Sharjeel Ahmed";
}

export function setDisplayName(name: string) {
  localStorage.setItem(DISPLAY_NAME_KEY, name.trim() || "Sharjeel Ahmed");
}
