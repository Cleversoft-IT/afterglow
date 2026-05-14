import Link from "next/link";

const NAV = [
  { href: "/dashboard/calls", label: "Calls" },
  { href: "/dashboard/customers", label: "Customers" },
  { href: "/dashboard/templates", label: "Templates" },
  { href: "/dashboard/templates/wizard", label: "Template wizard" },
  { href: "/dashboard/audit", label: "Audit log" },
  { href: "/dashboard/settings/privacy", label: "Privacy" },
  { href: "/dashboard/business", label: "Business" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh grid grid-cols-[220px_1fr] bg-ui-canvas text-ui-ink">
      <aside className="flex flex-col border-r border-ui-line bg-ui-surface px-4 py-7 shadow-soft">
        <Link
          href="/"
          className="mb-8 flex items-center gap-2.5 rounded-xl px-1 py-1 transition-colors hover:bg-ui-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-surface"
        >
          <div className="grid h-8 w-8 place-items-center rounded-xl bg-ui-accent text-xs font-semibold text-ui-surface shadow-soft">
            A
          </div>
          <span className="text-[15px] font-medium tracking-tight text-ui-ink">Afterglow</span>
        </Link>
        <nav className="flex flex-1 flex-col gap-0.5 text-sm" aria-label="Dashboard">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="block rounded-xl px-3 py-2 font-medium text-ui-subtle outline-none transition-colors hover:bg-ui-muted hover:text-ui-ink focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-surface"
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-ui-line pt-5 text-xs text-ui-subtle">
          <Link
            href="/dialer/incoming/demo-restaurant-known"
            className="font-medium text-ui-subtle transition-colors hover:text-ui-mint focus-visible:rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ui-mint/35 focus-visible:ring-offset-2 focus-visible:ring-offset-ui-surface"
          >
            Phone preview →
          </Link>
        </div>
      </aside>
      <main className="min-h-dvh bg-ui-canvas">{children}</main>
    </div>
  );
}
