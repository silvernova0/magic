'use client'

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import Link from "next/link";

function VerifyEmailContent() {
    const searchParams = useSearchParams();
    const token = searchParams.get("token");
    const router = useRouter();
    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState("Verifying your email...");

    useEffect(() => {
        if (!token) {
            setStatus('error');
            setMessage("No verification token found.");
            return;
        }

        const verify = async () => {
            try {
                const res = await fetch('/api/auth/verify-email', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token }),
                });

                const data = await res.json();

                if (res.ok) {
                    setStatus('success');
                    setMessage("Email verified successfully! Redirecting to login...");
                    setTimeout(() => {
                        router.push('/login?verified=true');
                    }, 3000);
                } else {
                    setStatus('error');
                    setMessage(data.error || "Verification failed.");
                }
            } catch (error) {
                setStatus('error');
                setMessage("An unexpected error occurred.");
            }
        };

        verify();
    }, [token, router]);

    return (
        <Card className="w-full max-w-md">
            <CardHeader className="text-center">
                <CardTitle>Email Verification</CardTitle>
                <CardDescription>
                    {status === 'loading' && "Please wait while we verify your email address."}
                    {status === 'success' && "Your email has been verified!"}
                    {status === 'error' && "There was a problem verifying your email."}
                </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center p-6 space-y-4">
                {status === 'loading' && (
                    <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
                )}

                {status === 'success' && (
                    <>
                        <CheckCircle className="h-12 w-12 text-green-500" />
                        <p className="text-center text-sm text-muted-foreground">{message}</p>
                        <Button asChild className="mt-4">
                            <Link href="/login">Go to Login</Link>
                        </Button>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <XCircle className="h-12 w-12 text-red-500" />
                        <p className="text-center text-sm text-red-600">{message}</p>
                        <Button asChild variant="secondary" className="mt-4">
                            <Link href="/login">Back to Login</Link>
                        </Button>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

export default function VerifyEmailPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 p-4">
            <Suspense fallback={<div className="text-white">Loading...</div>}>
                <VerifyEmailContent />
            </Suspense>
        </div>
    );
}
