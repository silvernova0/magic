'use client'

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Lock } from "lucide-react";

function ResetPasswordContent() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token");
    const router = useRouter();

    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            setStatus('error');
            setMessage("Passwords do not match");
            return;
        }

        if (password.length < 6) {
            setStatus('error');
            setMessage("Password must be at least 6 characters");
            return;
        }

        setStatus('loading');
        setMessage("");

        try {
            const res = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password }),
            });

            const data = await res.json();

            if (res.ok) {
                setStatus('success');
                setMessage("Password reset successfully! Redirecting to login...");
                setTimeout(() => {
                    router.push('/login?reset=true');
                }, 3000);
            } else {
                setStatus('error');
                setMessage(data.error || "Failed to reset password.");
            }
        } catch (error) {
            setStatus('error');
            setMessage("An unexpected error occurred.");
        }
    };

    if (!token) {
        return (
            <Card className="w-full max-w-md">
                <CardContent className="p-6 text-center text-red-500">
                    Invalid or missing reset token.
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="w-full max-w-md">
            <CardHeader className="space-y-1">
                <CardTitle className="text-2xl font-bold text-center">
                    Reset Password
                </CardTitle>
                <CardDescription className="text-center">
                    Enter your new password below.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {status === 'success' ? (
                    <div className="text-center space-y-4">
                        <div className="flex justify-center">
                            <Lock className="h-12 w-12 text-green-500" />
                        </div>
                        <p className="text-green-600">{message}</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="password">New Password</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="At least 6 characters"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                disabled={status === 'loading'}
                                minLength={6}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirmPassword">Confirm New Password</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                placeholder="Confirm new password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                disabled={status === 'loading'}
                                minLength={6}
                            />
                        </div>

                        {status === 'error' && (
                            <div className="text-sm text-red-500 text-center">{message}</div>
                        )}

                        <Button type="submit" className="w-full" disabled={status === 'loading'}>
                            {status === 'loading' ? "Resetting..." : "Reset Password"}
                        </Button>
                    </form>
                )}
            </CardContent>
        </Card>
    );
}

export default function ResetPasswordPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 p-4">
            <Suspense fallback={<div className="text-white">Loading...</div>}>
                <ResetPasswordContent />
            </Suspense>
        </div>
    );
}
