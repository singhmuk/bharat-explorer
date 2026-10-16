
export type Dest = {
  id: number;
  slug: string;
  name: string;
  state: string;
  region: string;
  summary: string;
  description: string;
  best_season: string;
  lat: number;
  lng: number;
  tags: string[];
  popularity: number;
  affiliate_url?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  guide_md?: string | null;
  image_url?: string | null;
  image_alt?: string | null;
  updated_at?: string | null;
};


export type Rec = {
  slug: string;
  name: string;
  state: string;
  summary: string;
  tags: string[];
  reason: string;
};

export const auth = {
  get token() { return localStorage.getItem("token"); },
  set(t: string) { localStorage.setItem("token", t); },
  clear() { localStorage.removeItem("token"); },
};

export async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "bharat-web", // checked by BotShield
      ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Something went wrong. Try again");
  }
  return res.json();
}
