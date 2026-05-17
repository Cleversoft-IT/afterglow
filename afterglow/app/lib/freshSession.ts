// One-shot flag set by the root layout the FIRST time it discovers the
// active template is empty (fresh visit or post-reset) and redirects to
// /(drawer)/templates. Templates screen consumes it after a successful
// `activate(...)` to surface the "head over to calls?" dialog. Cleared
// immediately on consumption so subsequent activations don't repeat it.
//
// We pair an in-memory flag with sessionStorage so the redirect survives
// across React renders without leaking across full page reloads / tab
// closes — exactly the scope a "fresh session" needs.

const KEY = 'afterglow.fresh_session';
let memoryFlag = false;

function readStorage(): boolean {
  try {
    if (typeof sessionStorage === 'undefined') return false;
    return sessionStorage.getItem(KEY) === '1';
  } catch {
    return false;
  }
}

function writeStorage(value: boolean): void {
  try {
    if (typeof sessionStorage === 'undefined') return;
    if (value) sessionStorage.setItem(KEY, '1');
    else sessionStorage.removeItem(KEY);
  } catch {
    /* private mode / SSR — ignore */
  }
}

export function markFreshSession(): void {
  memoryFlag = true;
  writeStorage(true);
}

export function consumeFreshSession(): boolean {
  const value = memoryFlag || readStorage();
  memoryFlag = false;
  writeStorage(false);
  return value;
}
