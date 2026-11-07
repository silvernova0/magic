"use client";

import { signOut, useSession } from "next-auth/react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function UserNav() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <div className="text-sm">Loading...</div>;
  }

  if (!session) {
    return (
      <Link href="/login">
        <Button variant="outline">Sign In</Button>
      </Link>
    );
  }

  const isAdmin = session.user?.role === "ADMIN";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {session.user?.name || "User"}
          </p>
          <p className="text-xs text-muted-foreground truncate">
            {session.user?.email}
          </p>
          {isAdmin && (
            <span className="inline-block text-xs px-2 py-0.5 mt-1 rounded bg-purple-500/20 text-purple-300">
              Admin
            </span>
          )}
        </div>
      </div>
      {isAdmin && (
        <Link href="/admin" className="block">
          <Button variant="outline" size="sm" className="w-full">
            Admin Panel
          </Button>
        </Link>
      )}
      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={() => signOut({ callbackUrl: "/login" })}
      >
        Sign Out
      </Button>
    </div>
  );
}
