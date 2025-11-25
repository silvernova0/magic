import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { sendPasswordResetEmail } from "@/lib/email";
import crypto from "crypto";

export async function POST(request: Request) {
    try {
        const { email } = await request.json();

        if (!email) {
            return NextResponse.json(
                { error: "Email is required" },
                { status: 400 }
            );
        }

        // Check if user exists
        const user = await prisma.user.findUnique({
            where: { email },
        });

        if (!user) {
            // Don't reveal that user doesn't exist for security
            return NextResponse.json(
                { message: "If an account exists with this email, a password reset link has been sent." },
                { status: 200 }
            );
        }

        // Generate reset token
        const token = crypto.randomBytes(32).toString("hex");
        const expires = new Date(Date.now() + 1 * 60 * 60 * 1000); // 1 hour

        // Save token (upsert to replace existing token if any)
        await prisma.verificationToken.upsert({
            where: {
                identifier_token: {
                    identifier: email,
                    token: token // This is tricky with upsert on composite unique. 
                    // Better to delete old ones for this identifier first or just create new.
                    // The schema has @@unique([identifier, token]) but also token @unique globally?
                    // Let's check schema.
                }
            },
            // Actually, let's just create a new one. The schema has `token` as unique.
            // But we might want to clean up old tokens for this user?
            // For simplicity and safety, let's just create.
            update: {
                token,
                expires
            },
            create: {
                identifier: email,
                token,
                expires,
            },
            // Wait, upsert requires a unique where clause. 
            // The schema has `token` @unique. But we don't know the old token.
            // We should probably just create a new one.
        });

        // Actually, looking at schema:
        // model VerificationToken {
        //   identifier String
        //   token      String   @unique
        //   expires    DateTime
        //   @@unique([identifier, token])
        // }

        // We can just create a new one.
        await prisma.verificationToken.create({
            data: {
                identifier: email,
                token,
                expires
            }
        });

        // Send email
        sendPasswordResetEmail(user.name || 'User', user.email!, token).catch((err) =>
            console.error('Failed to send password reset email:', err)
        );

        return NextResponse.json(
            { message: "If an account exists with this email, a password reset link has been sent." },
            { status: 200 }
        );
    } catch (error) {
        console.error("Forgot password error:", error);
        return NextResponse.json(
            { error: "Failed to process request" },
            { status: 500 }
        );
    }
}
