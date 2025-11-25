'use server'

import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/admin";
import { revalidatePath } from "next/cache";
import { testEmailConfig, sendEmail } from "@/lib/email";

export async function getEmailSettings() {
    await requireAdmin();

    const settings = await prisma.systemSetting.findMany({
        where: {
            key: {
                in: ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_SECURE', 'EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_FROM']
            }
        }
    });

    const config: Record<string, string> = {};
    settings.forEach(s => config[s.key] = s.value);

    // Mask password
    if (config.EMAIL_PASSWORD) {
        config.EMAIL_PASSWORD = '********';
    }

    return config;
}

export async function saveEmailSettings(formData: FormData) {
    await requireAdmin();

    const settings = {
        EMAIL_HOST: formData.get('host') as string,
        EMAIL_PORT: formData.get('port') as string,
        EMAIL_SECURE: formData.get('secure') === 'on' ? 'true' : 'false',
        EMAIL_USER: formData.get('user') as string,
        EMAIL_FROM: formData.get('from') as string,
    };

    const password = formData.get('password') as string;

    // Only update password if it's not masked
    if (password && password !== '********') {
        await prisma.systemSetting.upsert({
            where: { key: 'EMAIL_PASSWORD' },
            update: { value: password },
            create: { key: 'EMAIL_PASSWORD', value: password }
        });
    }

    for (const [key, value] of Object.entries(settings)) {
        if (value !== null && value !== undefined) {
            await prisma.systemSetting.upsert({
                where: { key },
                update: { value },
                create: { key, value }
            });
        }
    }

    revalidatePath('/admin/email');
    return { success: true };
}

export async function sendTestEmailAction(to: string) {
    await requireAdmin();

    // First verify config
    const configResult = await testEmailConfig();
    if (!configResult.success) {
        return configResult;
    }

    // Then try to send actual email
    const sent = await sendEmail(
        to,
        'Test Email from Magic Deck Builder',
        `
      <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: #5b21b6;">Test Email</h2>
        <p>This is a test email to verify your SMTP settings.</p>
        <p>If you are reading this, your email configuration is working correctly!</p>
        <p style="color: #6b7280; font-size: 12px; margin-top: 20px;">Sent from Magic Deck Builder Admin Panel</p>
      </div>
    `
    );

    if (sent) {
        return { success: true, message: 'Test email sent successfully!' };
    } else {
        return { success: false, message: 'Failed to send test email. Check server logs for details.' };
    }
}
