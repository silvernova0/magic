import { requireAdmin } from "@/lib/admin";
import { getEmailSettings } from "./actions";
import EmailSettingsForm from "./EmailSettingsForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Email Settings | Admin",
  description: "Configure SMTP settings for the application.",
};

export default async function EmailSettingsPage() {
  await requireAdmin();
  const settings = await getEmailSettings();

  return (
    <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Email Settings</h1>
        <p className="text-muted-foreground mt-2">
          Configure SMTP settings for system emails (Welcome, Password Reset, etc.)
        </p>
      </div>

      <div className="max-w-4xl">
        <EmailSettingsForm initialSettings={settings} />
      </div>
    </div>
  );
}
