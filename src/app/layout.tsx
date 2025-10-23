import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import UserNav from "@/components/UserNav";

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
  description: "AI-powered Commander/EDH deck builder with card collection management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased dark`}>
        <AuthProvider>
          <div className="min-h-screen flex">
            <aside className="w-64 bg-muted p-4 border-r hidden md:block">
              <div className="mb-6">
                <h2 className="text-xl font-semibold">🎴 JankBuild</h2>
                <p className="text-sm text-muted-foreground">AI-Powered Commander Deck Builder</p>
              </div>
              <nav>
                <ul className="space-y-2">
                  <li>
                    <Link href="/" className="block px-3 py-2 rounded hover:bg-white/5">Home</Link>
                  </li>
                  <li>
                    <Link href="/collection" className="block px-3 py-2 rounded hover:bg-white/5">Collection</Link>
                  </li>
                  <li>
                    <Link href="/deckbuilder" className="block px-3 py-2 rounded hover:bg-white/5">Deck Builder</Link>
                  </li>
                  <li>
                    <Link href="/decks" className="block px-3 py-2 rounded hover:bg-white/5">My Decks</Link>
                  </li>
                  <li>
                    <Link href="/import" className="block px-3 py-2 rounded hover:bg-white/5">Import / Export</Link>
                  </li>
                  <li>
                    <Link href="/commander" className="block px-3 py-2 rounded hover:bg-white/5">Commander Search</Link>
                  </li>
                </ul>
              </nav>
              <div className="mt-auto pt-6 border-t">
                <UserNav />
              </div>
            </aside>

            <main className="flex-1 p-6">
              {children}
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
