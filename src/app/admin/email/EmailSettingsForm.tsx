'use client'

import { useState } from "react";
import { saveEmailSettings, sendTestEmailAction } from "./actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function EmailSettingsForm({ initialSettings }: { initialSettings: Record<string, string> }) {
    const [loading, setLoading] = useState(false);
    const [testLoading, setTestLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [testEmail, setTestEmail] = useState("");

    async function handleSubmit(formData: FormData) {
        setLoading(true);
        setMessage(null);
        try {
            await saveEmailSettings(formData);
            setMessage({ type: 'success', text: 'Settings saved successfully!' });
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to save settings.' });
        } finally {
            setLoading(false);
        }
    }

    async function handleTestEmail() {
        if (!testEmail) return;
        setTestLoading(true);
        setMessage(null);
        try {
            const result = await sendTestEmailAction(testEmail);
            setMessage({ type: result.success ? 'success' : 'error', text: result.message });
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to send test email.' });
        } finally {
            setTestLoading(false);
        }
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>SMTP Configuration</CardTitle>
                    <CardDescription>Configure your email server settings.</CardDescription>
                </CardHeader>
                <CardContent>
                    <form action={handleSubmit} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="host">SMTP Host</Label>
                                <Input id="host" name="host" defaultValue={initialSettings.EMAIL_HOST} placeholder="smtp.gmail.com" required />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="port">SMTP Port</Label>
                                <Input id="port" name="port" defaultValue={initialSettings.EMAIL_PORT} placeholder="587" required />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="user">SMTP User</Label>
                                <Input id="user" name="user" defaultValue={initialSettings.EMAIL_USER} placeholder="user@example.com" required />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="password">SMTP Password</Label>
                                <Input id="password" name="password" type="password" defaultValue={initialSettings.EMAIL_PASSWORD} placeholder="********" />
                                <p className="text-xs text-muted-foreground">Leave blank to keep existing password</p>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="from">From Email Address</Label>
                            <Input id="from" name="from" defaultValue={initialSettings.EMAIL_FROM} placeholder="noreply@example.com" />
                        </div>

                        <div className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                id="secure"
                                name="secure"
                                defaultChecked={initialSettings.EMAIL_SECURE === 'true'}
                                className="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                            />
                            <Label htmlFor="secure">Use Secure Connection (SSL/TLS)</Label>
                        </div>

                        <Button type="submit" disabled={loading}>
                            {loading ? "Saving..." : "Save Settings"}
                        </Button>
                    </form>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Test Configuration</CardTitle>
                    <CardDescription>Send a test email to verify your settings.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-4 items-end">
                        <div className="space-y-2 flex-1">
                            <Label htmlFor="testEmail">Recipient Email</Label>
                            <Input
                                id="testEmail"
                                value={testEmail}
                                onChange={(e) => setTestEmail(e.target.value)}
                                placeholder="your@email.com"
                            />
                        </div>
                        <Button onClick={handleTestEmail} disabled={testLoading || !testEmail} variant="secondary">
                            {testLoading ? "Sending..." : "Send Test Email"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {message && (
                <div className={`p-4 rounded-md ${message.type === 'success' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'}`}>
                    {message.text}
                </div>
            )}
        </div>
    );
}
