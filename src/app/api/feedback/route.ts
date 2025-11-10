import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    const body = await request.json();

    const { type, message, email, page } = body;

    // Validate required fields
    if (!message || !type) {
      return NextResponse.json(
        { error: 'Message and type are required' },
        { status: 400 }
      );
    }

    // Validate type enum
    const validTypes = ['BUG', 'FEATURE_REQUEST', 'GENERAL', 'DECK_ISSUE'];
    if (!validTypes.includes(type)) {
      return NextResponse.json(
        { error: 'Invalid feedback type' },
        { status: 400 }
      );
    }

    // Create feedback
    const feedback = await prisma.feedback.create({
      data: {
        type,
        message: message.trim(),
        email: email?.trim() || null,
        page: page || null,
        userId: session?.user?.id || null,
      },
    });

    console.log('[Feedback] New submission:', {
      id: feedback.id,
      type: feedback.type,
      page: feedback.page,
      hasEmail: !!feedback.email,
      userId: feedback.userId || 'anonymous',
    });

    return NextResponse.json({ success: true, id: feedback.id });
  } catch (error) {
    console.error('[Feedback API] Error:', error);
    return NextResponse.json(
      { error: 'Failed to submit feedback' },
      { status: 500 }
    );
  }
}

// GET endpoint for admins to view feedback
export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    // Only admins can view feedback
    if (!session?.user || session.user.role !== 'ADMIN') {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const feedback = await prisma.feedback.findMany({
      include: {
        user: {
          select: {
            email: true,
            name: true,
          },
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    return NextResponse.json({ feedback });
  } catch (error) {
    console.error('[Feedback API GET] Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch feedback' },
      { status: 500 }
    );
  }
}
