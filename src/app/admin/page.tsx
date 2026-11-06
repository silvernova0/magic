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
import ScraperQuickBar from "@/components/ScraperQuickBar";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  try {
    await requireAdmin();
  } catch {
    redirect("/");
  }

  const [users, recentJobs] = await Promise.all([
    prisma.user.findMany({
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
    }),
    prisma.scrapeJob.findMany({
      orderBy: { startedAt: "desc" },
      take: 15,
    }),
  ]);

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
    <div className="container mx-auto max-w-7xl space-y-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold text-white">
            Scrapers &amp; Admin Control Center
          </h1>
          <p className="text-slate-400 mt-1">
            Manage automated Scryfall/EDHREC/MTGTop8/Moxfield scrapers, email settings, and user roles
          </p>
        </div>
        <Button asChild variant="outline" className="border-slate-700 bg-slate-900">
          <a href="/admin/email">Configure SMTP Email</a>
        </Button>
      </div>

      {/* Live Scraper Trigger Bar */}
      <ScraperQuickBar />

      {/* Recent Scrape Job History */}
      <Card className="bg-slate-900/60 border-slate-800/80">
        <CardHeader>
          <CardTitle className="text-white">Recent Scraper Job History</CardTitle>
          <CardDescription>
            Last {recentJobs.length} automated and manual sync runs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recentJobs.length === 0 ? (
            <p className="text-sm text-slate-400">
              No scrape jobs recorded yet. Click &quot;Sync Now&quot; on any source above to run one immediately.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Source</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Items Synced</th>
                    <th className="py-2.5 px-3">Duration</th>
                    <th className="py-2.5 px-3">Started At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {recentJobs.map((job) => (
                    <tr key={job.id} className="text-slate-300">
                      <td className="py-2.5 px-3 font-semibold uppercase text-purple-300">
                        {job.jobType}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            job.status === "completed"
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-500/30"
                              : job.status === "running"
                              ? "bg-blue-950 text-blue-300 border border-blue-500/30"
                              : "bg-red-950 text-red-300 border border-red-500/30"
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{job.itemsScraped.toLocaleString()}</td>
                      <td className="py-2.5 px-3">
                        {job.duration ? `${(job.duration / 1000).toFixed(1)}s` : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {new Date(job.startedAt).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* User Management */}
      <Card className="bg-slate-900/60 border-slate-800/80">
        <CardHeader>
          <CardTitle className="text-white">User Management</CardTitle>
          <CardDescription>{users.length} registered users</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {users.map((user) => (
              <div
                key={user.id}
                className="flex items-center justify-between p-4 border border-slate-800 rounded-xl bg-slate-950/40"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white">
                      {user.name || "No name"}
                    </h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        user.role === "ADMIN"
                          ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                      }`}
                    >
                      {user.role}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">{user.email}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {user._count.cards} cards • {user._count.decks} decks • Joined{" "}
                    {new Date(user.createdAt).toLocaleDateString()}
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
    </div>
  );
}
