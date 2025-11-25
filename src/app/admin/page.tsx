import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/admin";
import { redirect } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import RestartButton from "./system/RestartButton";

export default async function AdminPage() {
  try {
    await requireAdmin();
  } catch {
    redirect("/");
  }

  const users = await prisma.user.findMany({
    select: {
      id: true,
      name: true,
      email: true,
      role: true,
      createdAt: true,
      _count: {
        select: {
          cards: true,
          decks: true,
        },
      },
    },
    orderBy: {
      createdAt: "desc",
    },
  });

  const feedback = await prisma.feedback.findMany({
    include: {
      user: {
        select: {
          name: true,
          email: true,
        },
      },
    },
    orderBy: {
      createdAt: "desc",
    },
    take: 50,
  });

  const totalDecks = await prisma.deck.count();

  async function promoteToAdmin(formData: FormData) {
    "use server";
    await requireAdmin();
    const userId = formData.get("userId") as string;
    await prisma.user.update({
      where: { id: userId },
      data: { role: "ADMIN" },
    });
  }

  async function demoteToUser(formData: FormData) {
    "use server";
    await requireAdmin();
    const userId = formData.get("userId") as string;
    await prisma.user.update({
      where: { id: userId },
      data: { role: "USER" },
    });
  }

  return (
    <main className="container mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Manage users and their roles
        </p>
      </div>

      {/* Admin Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Email Settings</CardTitle>
            <CardDescription>
              Configure SMTP and test email delivery
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <a href="/admin/email">Manage Email</a>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>User Feedback</CardTitle>
            <CardDescription>
              {feedback.length} feedback submissions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              View user-submitted feedback below
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>System Management</CardTitle>
            <CardDescription>
              Manage server status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RestartButton />
          </CardContent>
        </Card>
      </div>

      {/* Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Decks Generated</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDecks}</div>
            <p className="text-xs text-muted-foreground">
              Across all users
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Management</CardTitle>
          <CardDescription>
            {users.length} registered users
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {users.map((user) => (
              <div
                key={user.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{user.name || "No name"}</h3>
                    <span
                      className={`text-xs px-2 py-1 rounded ${user.role === "ADMIN"
                        ? "bg-purple-500/20 text-purple-300"
                        : "bg-blue-500/20 text-blue-300"
                        }`}
                    >
                      {user.role}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {user._count.cards} cards • {user._count.decks} decks •
                    Joined {new Date(user.createdAt).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  {user.role === "USER" ? (
                    <form action={promoteToAdmin}>
                      <input type="hidden" name="userId" value={user.id} />
                      <Button type="submit" variant="outline" size="sm">
                        Promote to Admin
                      </Button>
                    </form>
                  ) : (
                    <form action={demoteToUser}>
                      <input type="hidden" name="userId" value={user.id} />
                      <Button type="submit" variant="outline" size="sm">
                        Demote to User
                      </Button>
                    </form>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Feedback Section */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>User Feedback</CardTitle>
          <CardDescription>
            Recent feedback submissions from users
          </CardDescription>
        </CardHeader>
        <CardContent>
          {feedback.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No feedback yet</p>
          ) : (
            <div className="space-y-4">
              {feedback.map((item) => (
                <div
                  key={item.id}
                  className="p-4 border rounded-lg space-y-2"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2 py-1 rounded ${item.type === "BUG"
                          ? "bg-red-500/20 text-red-300"
                          : item.type === "FEATURE_REQUEST"
                            ? "bg-blue-500/20 text-blue-300"
                            : item.type === "DECK_ISSUE"
                              ? "bg-yellow-500/20 text-yellow-300"
                              : "bg-gray-500/20 text-gray-300"
                          }`}
                      >
                        {item.type === "BUG"
                          ? "🐛 Bug"
                          : item.type === "FEATURE_REQUEST"
                            ? "💡 Feature"
                            : item.type === "DECK_ISSUE"
                              ? "🎴 Deck Issue"
                              : "💬 General"}
                      </span>
                      {item.page && (
                        <span className="text-xs text-muted-foreground">
                          from {item.page}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {new Date(item.createdAt).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-sm">{item.message}</p>

                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    {item.user ? (
                      <span>👤 {item.user.name || item.user.email}</span>
                    ) : item.email ? (
                      <span>📧 {item.email}</span>
                    ) : (
                      <span>👤 Anonymous</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
