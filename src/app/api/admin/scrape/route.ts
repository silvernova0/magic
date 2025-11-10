import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getScrapedData, getCacheStatus, clearCache } from '@/lib/scrapers';

/**
 * GET /api/admin/scrape
 * Get scraper cache status
 */
export async function GET(request: NextRequest) {
  try {
    // Check authentication
    const session = await getServerSession(authOptions);
    if (!session || session.user.role !== 'ADMIN') {
      return NextResponse.json(
        { error: 'Unauthorized. Admin access required.' },
        { status: 401 }
      );
    }

    const status = await getCacheStatus();
    
    return NextResponse.json({
      success: true,
      cache: {
        ...status,
        ageMinutes: status.age ? Math.round(status.age / 1000 / 60) : undefined,
      },
    });
  } catch (error: any) {
    console.error('Error getting scraper status:', error);
    return NextResponse.json(
      { error: 'Failed to get scraper status', details: error.message },
      { status: 500 }
    );
  }
}

/**
 * POST /api/admin/scrape
 * Trigger manual scraping (force refresh)
 */
export async function POST(request: NextRequest) {
  try {
    // Check authentication
    const session = await getServerSession(authOptions);
    if (!session || session.user.role !== 'ADMIN') {
      return NextResponse.json(
        { error: 'Unauthorized. Admin access required.' },
        { status: 401 }
      );
    }

    const { action } = await request.json();

    if (action === 'clear') {
      await clearCache();
      return NextResponse.json({
        success: true,
        message: 'Cache cleared successfully',
      });
    }

    // Force refresh
    console.log('Admin triggered manual scraping...');
    const startTime = Date.now();
    
    const data = await getScrapedData(true); // Force refresh
    
    const duration = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      message: 'Scraping completed successfully',
      duration: `${(duration / 1000).toFixed(2)}s`,
      data: {
        edhrec: {
          commanders: data.edhrec?.topCommanders.length || 0,
          themes: data.edhrec?.themes.length || 0,
        },
        mtgtop8: {
          decks: data.mtgtop8?.recentDecks.length || 0,
          topCommanders: data.mtgtop8?.topCommanders.length || 0,
        },
        moxfield: {
          totalDecks: Object.values(data.moxfield?.topDecksByBracket || {})
            .reduce((sum, decks) => sum + decks.length, 0),
          commanders: data.moxfield?.popularCommanders.length || 0,
        },
        timestamp: data.timestamp,
      },
    });
  } catch (error: any) {
    console.error('Error during manual scraping:', error);
    return NextResponse.json(
      { error: 'Scraping failed', details: error.message },
      { status: 500 }
    );
  }
}
