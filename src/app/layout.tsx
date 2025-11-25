import type { Metadata } from "next";
import { Geist, Geist_Mono, Cinzel } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import { Sidebar } from "@/components/layout/Sidebar";
import { FeedbackButton } from "@/components/FeedbackButton";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const cinzel = Cinzel({
  variable: "--font-cinzel",
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
      <body className={`${geistSans.variable} ${geistMono.variable} ${cinzel.variable} antialiased dark`}>
        <AuthProvider>
          <div className="min-h-screen flex bg-background text-foreground selection:bg-primary/30 selection:text-primary-foreground">
            <Sidebar />

            <main className="flex-1 p-6 overflow-x-hidden">
              {children}
            </main>
          </div>
          <FeedbackButton />
        </AuthProvider>
      </body>
    </html>
  );
}
