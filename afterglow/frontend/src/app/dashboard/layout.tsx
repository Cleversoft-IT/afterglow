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
    <div className="min-h-screen grid grid-cols-[220px_1fr]">
      <aside className="border-r bg-white py-6 px-4">
        <Link href="/" className="flex items-center gap-2 mb-8">
          <div className="w-7 h-7 rounded-full bg-afterglow-700 grid place-items-center text-white text-xs font-bold">
            A
          </div>
          <span className="font-semibold tracking-tight">Afterglow</span>
        </Link>
        <nav className="space-y-1 text-sm">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="block px-3 py-2 rounded text-zinc-700 hover:bg-zinc-100 hover:text-afterglow-700"
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="mt-10 text-xs text-zinc-500">
          <Link href="/dialer/incoming/demo-restaurant-known" className="text-afterglow-700 hover:underline">
            Phone preview →
          </Link>
        </div>
      </aside>
      <main className="bg-zinc-50">{children}</main>
    </div>
  );
}
