import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import SidebarNav from "@/components/SidebarNav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JankBuild - MTG Commander Deck Builder",
  description: "Local AI-powered Commander/EDH deck builder with 31,483-card database and automated meta scrapers",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased dark bg-slate-950 text-slate-100 selection:bg-purple-500/30 selection:text-purple-200`}
      >
        <AuthProvider>
          <div className="min-h-screen flex bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-purple-950/25 via-slate-950 to-slate-950">
            <SidebarNav />
            <main className="flex-1 p-6 md:p-8 pt-20 md:pt-8 overflow-x-hidden">
              {children}
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
