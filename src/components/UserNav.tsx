"use client";

import { signOut, useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function UserNav() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <div className="text-sm text-muted-foreground animate-pulse">Loading...</div>;
  }

  if (!session) {
    return (
      <Link href="/login" className="w-full">
        <Button variant="outline" className="w-full border-primary/50 hover:bg-primary/20 hover:text-primary">
          Sign In
        </Button>
      </Link>
    );
  }

  const isAdmin = session.user?.role === "ADMIN";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 p-2 rounded-lg bg-white/5 border border-white/5">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-xs font-bold text-white">
          {session.user?.name?.[0]?.toUpperCase() || "U"}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate text-foreground">
            {session.user?.name || "User"}
          </p>
          <p className="text-xs text-muted-foreground truncate">
            {session.user?.email}
          </p>
        </div>
      </div>

      {isAdmin && (
        <Link href="/admin" className="block">
          <Button variant="ghost" size="sm" className="w-full justify-start text-purple-400 hover:text-purple-300 hover:bg-purple-500/10">
            🛡️ Admin Panel
          </Button>
        </Link>
      )}

      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10"
        onClick={() => signOut({ callbackUrl: "/login" })}
      >
        🚪 Sign Out
      </Button>
    </div>
  );
}
