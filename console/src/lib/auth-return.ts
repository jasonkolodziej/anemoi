/**
 * Where to send someone after they sign in: the page that sent them to
 * `/auth/login?next=...` (e.g. the storm they were about to run a cycle
 * on), else `/profile`. Only a same-site path is honoured -- anything
 * else (`//evil.example`, `https://...`, `/\evil`) would make the login
 * page an open redirect.
 */
export const DEFAULT_AFTER_LOGIN = "/profile";

export function safeNext(raw: string | null | undefined): string {
  if (
    !raw ||
    !raw.startsWith("/") ||
    raw.startsWith("//") ||
    raw.startsWith("/\\")
  ) {
    return DEFAULT_AFTER_LOGIN;
  }
  return raw;
}

export function loginHref(next: string): string {
  return `/auth/login?next=${encodeURIComponent(next)}`;
}
