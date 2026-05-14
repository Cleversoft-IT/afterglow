export default function PrivacySettings() {
  return (
    <div className="max-w-2xl space-y-8 px-5 py-8 sm:px-8 sm:py-10">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Privacy</h1>
        <p className="mt-1 text-sm leading-relaxed text-ui-subtle">
          Afterglow is privacy-aware by design. AI mode is opt-in (the blue
          button), sensitive fields are flagged, every executed action is
          revertible and logged.
        </p>
      </header>

      <section className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft space-y-5">
        <Toggle label="Show PII (phone numbers, names) in dashboards" defaultChecked />
        <Toggle label="Retain raw audio after extraction" />
        <Toggle label="Retain raw transcript after summary" defaultChecked />
      </section>

      <section className="rounded-2xl border border-ui-line bg-ui-surface p-6 shadow-soft">
        <h2 className="text-sm font-semibold text-ui-ink">Retention</h2>
        <p className="mt-2 text-xs leading-relaxed text-ui-subtle">
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
    <label className="flex cursor-pointer items-center justify-between gap-4 text-sm text-ui-ink">
      <span className="leading-snug">{label}</span>
      <input
        type="checkbox"
        defaultChecked={defaultChecked}
        className="h-4 w-4 shrink-0 rounded border-ui-line text-ui-mint accent-ui-mint focus:ring-2 focus:ring-ui-mint/35 focus:ring-offset-2 focus:ring-offset-ui-surface"
      />
    </label>
  );
}
