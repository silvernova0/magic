'use client'

import { useState } from "react";
import { restartServer } from "./actions";
import { Button } from "@/components/ui/button";
import { Loader2, RefreshCw } from "lucide-react";

export default function RestartButton() {
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    async function handleRestart() {
        if (!confirm("Are you sure you want to restart the web server? The site will be briefly unavailable.")) {
            return;
        }

        setLoading(true);
        setMessage(null);

        try {
            const result = await restartServer();
            if (result.success) {
                setMessage({ type: 'success', text: result.message });
                // Refresh the page after a short delay to check if server is back
                setTimeout(() => {
                    window.location.reload();
                }, 5000);
            } else {
                setMessage({ type: 'error', text: result.message });
                setLoading(false);
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'An unexpected error occurred.' });
            setLoading(false);
        }
    }

    return (
        <div className="space-y-2">
            <Button
                onClick={handleRestart}
                disabled={loading}
                variant="destructive"
                className="w-full sm:w-auto"
            >
                {loading ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Restarting...
                    </>
                ) : (
                    <>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Restart Server
                    </>
                )}
            </Button>

            {message && (
                <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                    {message.text}
                </p>
            )}
        </div>
    );
}
