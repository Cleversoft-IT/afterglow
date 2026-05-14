export default function CustomersIndex() {
  return (
    <div className="px-5 py-8 sm:px-8 sm:py-10">
      <h1 className="text-2xl font-semibold tracking-tight text-ui-ink">Customers</h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ui-subtle">
        Customer profiles populate from completed calls. Open a call detail to
        jump into a customer profile.
      </p>
      <div className="mt-8 rounded-2xl border border-ui-line bg-ui-surface p-10 text-center shadow-soft sm:p-12">
        <p className="mx-auto max-w-md text-sm leading-relaxed text-ui-subtle">
          Day 2 build target: list customers + cross-call memory chunks.
        </p>
      </div>
    </div>
  );
}
