export default function PrivacySettings() {
  return (
    <div className="px-8 py-10 max-w-2xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Privacy</h1>
        <p className="text-sm text-zinc-600">
          Afterglow is privacy-aware by design. AI mode is opt-in (the blue
          button), sensitive fields are flagged, every executed action is
          revertible and logged.
        </p>
      </header>

      <section className="rounded-xl border bg-white p-5 space-y-3">
        <Toggle label="Show PII (phone numbers, names) in dashboards" defaultChecked />
        <Toggle label="Retain raw audio after extraction" />
        <Toggle label="Retain raw transcript after summary" defaultChecked />
      </section>

      <section className="rounded-xl border bg-white p-5">
        <h2 className="text-sm font-semibold mb-2">Retention</h2>
        <p className="text-xs text-zinc-500">
          Day 4 build target: retention slider with 7/30/90/180 day options + customer
          export/delete.
        </p>
      </section>
    </div>
  );
}

function Toggle({
  label,
  defaultChecked,
}: {
  label: string;
  defaultChecked?: boolean;
}) {
  return (
    <label className="flex items-center justify-between text-sm">
      <span className="text-zinc-800">{label}</span>
      <input type="checkbox" defaultChecked={defaultChecked} className="h-4 w-4" />
    </label>
  );
}
