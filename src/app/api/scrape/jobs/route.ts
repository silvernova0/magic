import { NextRequest, NextResponse } from 'next/server';
import { getJobHistory, getJobStats, runJobNow } from '@/lib/scheduled-scraper';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const action = searchParams.get('action');
    const jobType = searchParams.get('jobType');

    if (action === 'stats') {
      if (jobType) {
        const stats = await getJobStats(jobType);
        return NextResponse.json(stats);
      }

      const allStats = await Promise.all([
        getJobStats('scryfall'),
        getJobStats('edhrec'),
        getJobStats('mtgtop8'),
        getJobStats('moxfield'),
      ]);

      return NextResponse.json({
        scryfall: allStats[0],
        edhrec: allStats[1],
        mtgtop8: allStats[2],
        moxfield: allStats[3],
      });
    }

    const limit = parseInt(searchParams.get('limit') || '50');
    const history = await getJobHistory(limit);

    return NextResponse.json({
      success: true,
      count: history.length,
      jobs: history,
    });
  } catch (error) {
    console.error('Error fetching job history:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch job history',
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { jobType } = body;

    if (!jobType || !['scryfall', 'edhrec', 'mtgtop8', 'moxfield'].includes(jobType)) {
      return NextResponse.json(
        { success: false, error: 'Invalid job type. Must be: scryfall, edhrec, mtgtop8, or moxfield' },
        { status: 400 }
      );
    }

    console.log(`🚀 Manually triggering ${jobType} scraping job...`);
    await runJobNow(jobType as 'scryfall' | 'edhrec' | 'mtgtop8' | 'moxfield');

    return NextResponse.json({
      success: true,
      message: `${jobType.toUpperCase()} sync completed successfully`,
    });
  } catch (error) {
    console.error('Error running scrape job:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to run scrape job',
      },
      { status: 500 }
    );
  }
}
