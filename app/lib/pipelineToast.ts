// Tiny pub/sub for the "Analysis in progress" toast shown on the Calls tab
// right after the dialer fires a call submit. The dialer screen unmounts as
// soon as the user hangs up; the Calls screen subscribes on mount and reads
// the latest banner state. No persistence — when both screens are gone the
// toast is gone too.

export type PipelineToast = {
  callId: string | null;
  phoneE164: string;
  startedAt: number;
};

let current: PipelineToast | null = null;
const listeners = new Set<(t: PipelineToast | null) => void>();

export function setPipelineToast(next: PipelineToast | null): void {
  current = next;
  for (const fn of listeners) fn(current);
}

export function getPipelineToast(): PipelineToast | null {
  return current;
}

export function subscribePipelineToast(fn: (t: PipelineToast | null) => void): () => void {
  listeners.add(fn);
  fn(current);
  return () => {
    listeners.delete(fn);
  };
}
