import "../styles/globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Afterglow — What remains after the call",
  description:
    "Human-first AI dialer. Turns booking phone calls into structured data, customer memory and autonomously executed actions.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Afterglow",
  },
};

export const viewport: Viewport = {
  themeColor: "#F7F7F4",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh bg-ui-canvas text-ui-ink antialiased selection:bg-ui-mint/20 selection:text-ui-ink">
        {children}
      </body>
    </html>
  );
}
