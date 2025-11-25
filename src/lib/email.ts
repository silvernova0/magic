import nodemailer from 'nodemailer';
import { prisma } from '@/lib/prisma';

// Email configuration interface
interface EmailConfig {
  host: string;
  port: number;
  secure: boolean;
  auth: {
    user: string;
    pass: string;
  };
  from?: string;
}

// Fetch settings from DB or fallback to Env
async function getEmailConfig(): Promise<EmailConfig | null> {
  try {
    const settings = await prisma.systemSetting.findMany({
      where: {
        key: {
          in: ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_SECURE', 'EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_FROM']
        }
      }
    });

    const dbConfig: Record<string, string> = {};
    settings.forEach(s => dbConfig[s.key] = s.value);

    const host = dbConfig.EMAIL_HOST || process.env.EMAIL_HOST || 'smtp.gmail.com';
    const port = parseInt(dbConfig.EMAIL_PORT || process.env.EMAIL_PORT || '587');
    const secure = dbConfig.EMAIL_SECURE === 'true' || process.env.EMAIL_SECURE === 'true';
    const user = dbConfig.EMAIL_USER || process.env.EMAIL_USER;
    const pass = dbConfig.EMAIL_PASSWORD || process.env.EMAIL_PASSWORD;
    const from = dbConfig.EMAIL_FROM || process.env.EMAIL_FROM;

    if (!user || !pass) {
      return null;
    }

    return {
      host,
      port,
      secure,
      auth: { user, pass },
      from
    };
  } catch (error) {
    console.error('Error fetching email settings:', error);
    // Fallback to env if DB fails
    if (!process.env.EMAIL_USER || !process.env.EMAIL_PASSWORD) return null;
    return {
      host: process.env.EMAIL_HOST || 'smtp.gmail.com',
      port: parseInt(process.env.EMAIL_PORT || '587'),
      secure: process.env.EMAIL_SECURE === 'true',
      auth: {
        user: process.env.EMAIL_USER,
        pass: process.env.EMAIL_PASSWORD,
      },
      from: process.env.EMAIL_FROM
    };
  }
}

// Create transporter dynamically
async function getTransporter() {
  const config = await getEmailConfig();
  if (!config) {
    console.warn('Email credentials not configured. Emails will not be sent.');
    return null;
  }
  return nodemailer.createTransport(config);
}

// Email templates
export const emailTemplates = {
  welcome: (userName: string, userEmail: string) => ({
    subject: 'Welcome to Magic Deck Builder!',
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #5B21B6;">Welcome to Magic Deck Builder!</h1>
        <p>Hi ${userName},</p>
        <p>Thank you for joining our Magic: The Gathering deck building community!</p>
        <p>You can now:</p>
        <ul>
          <li>Build and manage your card collection</li>
          <li>Create commander decks with AI assistance</li>
          <li>Import cards from CSV or decklists</li>
          <li>Search for commander synergies</li>
        </ul>
        <p>Get started by logging in at: <a href="${process.env.NEXTAUTH_URL || 'http://localhost:3000'}">${process.env.NEXTAUTH_URL || 'http://localhost:3000'}</a></p>
        <p>Happy deck building!</p>
        <hr style="border: 1px solid #E5E7EB; margin: 20px 0;" />
        <p style="color: #6B7280; font-size: 12px;">This email was sent to ${userEmail}</p>
      </div>
    `,
  }),

  emailVerification: (userName: string, verificationUrl: string) => ({
    subject: 'Verify your email address',
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #5B21B6;">Verify Your Email</h1>
        <p>Hi ${userName},</p>
        <p>Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="${verificationUrl}" 
             style="background-color: #5B21B6; color: white; padding: 12px 30px; 
                    text-decoration: none; border-radius: 5px; display: inline-block;">
            Verify Email
          </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #5B21B6;">${verificationUrl}</p>
        <p style="color: #6B7280; font-size: 14px;">This link will expire in 24 hours.</p>
      </div>
    `,
  }),

  passwordReset: (userName: string, resetUrl: string) => ({
    subject: 'Reset your password',
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #5B21B6;">Password Reset Request</h1>
        <p>Hi ${userName},</p>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="${resetUrl}" 
             style="background-color: #5B21B6; color: white; padding: 12px 30px; 
                    text-decoration: none; border-radius: 5px; display: inline-block;">
            Reset Password
          </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #5B21B6;">${resetUrl}</p>
        <p style="color: #6B7280; font-size: 14px;">This link will expire in 1 hour.</p>
        <p style="color: #6B7280; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
      </div>
    `,
  }),

  adminNotification: (subject: string, message: string) => ({
    subject: `[Admin] ${subject}`,
    html: `
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #5B21B6;">Admin Notification</h1>
        <p>${message}</p>
        <hr style="border: 1px solid #E5E7EB; margin: 20px 0;" />
        <p style="color: #6B7280; font-size: 12px;">This is an automated admin notification.</p>
      </div>
    `,
  }),
};

// Send email function
export async function sendEmail(
  to: string,
  subject: string,
  html: string,
  from?: string
): Promise<boolean> {
  const transport = await getTransporter();

  if (!transport) {
    console.log('Email not sent (not configured):', { to, subject });
    return false;
  }

  try {
    // Get config again to check for 'from' override if not provided
    const config = await getEmailConfig();
    const defaultFrom = config?.from || process.env.EMAIL_FROM || config?.auth.user;

    const info = await transport.sendMail({
      from: from || defaultFrom,
      to,
      subject,
      html,
    });

    console.log('Email sent:', info.messageId);
    return true;
  } catch (error) {
    console.error('Error sending email:', error);
    return false;
  }
}

// Helper functions for common email types
export async function sendWelcomeEmail(userName: string, userEmail: string) {
  const template = emailTemplates.welcome(userName, userEmail);
  return sendEmail(userEmail, template.subject, template.html);
}

export async function sendVerificationEmail(
  userName: string,
  userEmail: string,
  verificationToken: string
) {
  const verificationUrl = `${process.env.NEXTAUTH_URL || 'http://localhost:3000'}/verify-email?token=${verificationToken}`;
  const template = emailTemplates.emailVerification(userName, verificationUrl);
  return sendEmail(userEmail, template.subject, template.html);
}

export async function sendPasswordResetEmail(
  userName: string,
  userEmail: string,
  resetToken: string
) {
  const resetUrl = `${process.env.NEXTAUTH_URL || 'http://localhost:3000'}/reset-password?token=${resetToken}`;
  const template = emailTemplates.passwordReset(userName, resetUrl);
  return sendEmail(userEmail, template.subject, template.html);
}

export async function sendAdminNotification(subject: string, message: string) {
  const adminEmail = process.env.ADMIN_EMAIL;
  if (!adminEmail) {
    console.log('Admin email not configured');
    return false;
  }
  const template = emailTemplates.adminNotification(subject, message);
  return sendEmail(adminEmail, template.subject, template.html);
}

// Test email configuration
export async function testEmailConfig(): Promise<{ success: boolean; message: string }> {
  const transport = await getTransporter();

  if (!transport) {
    return {
      success: false,
      message: 'Email not configured. Please set settings in Admin Panel or .env',
    };
  }

  try {
    await transport.verify();
    return {
      success: true,
      message: 'Email configuration is valid and ready to send emails.',
    };
  } catch (error: any) {
    return {
      success: false,
      message: `Email configuration error: ${error.message}`,
    };
  }
}
