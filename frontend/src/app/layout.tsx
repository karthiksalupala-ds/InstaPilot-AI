import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "InstaPilot AI — Multi-Account Instagram AI Agent",
  description: "Centralized multi-account Instagram AI Agent platform",
  icons: {
    icon: "/logo.jpg",
    apple: "/logo.jpg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f8f9fb] text-zinc-950 antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
