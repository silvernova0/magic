/**
 * API endpoint for managing scheduled scraping jobs
 * GET /api/scrape/jobs - Get job history
 * POST /api/scrape/jobs - Trigger a job manually
 * GET /api/scrape/jobs/stats - Get statistics for all job types
 */

import { NextRequest, NextResponse } from 'next/server';
import { getJobHistory, getJobStats, runJobNow } from '@/lib/scheduled-scraper';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const action = searchParams.get('action');
    const jobType = searchParams.get('jobType');
    
    // Get statistics for a specific job type or all
    if (action === 'stats') {
      if (jobType) {
        const stats = await getJobStats(jobType);
        return NextResponse.json(stats);
      }
      
      // Get stats for all job types
      const allStats = await Promise.all([
        getJobStats('edhrec'),
        getJobStats('mtgtop8'),
        getJobStats('moxfield'),
      ]);
      
      return NextResponse.json({
        edhrec: allStats[0],
        mtgtop8: allStats[1],
        moxfield: allStats[2],
      });
    }
    
    // Get job history
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
        error: error instanceof Error ? error.message : 'Failed to fetch job history' 
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { jobType } = body;
    
    if (!jobType || !['edhrec', 'mtgtop8', 'moxfield'].includes(jobType)) {
      return NextResponse.json(
        { success: false, error: 'Invalid job type. Must be: edhrec, mtgtop8, or moxfield' },
        { status: 400 }
      );
    }
    
    // Run job immediately
    console.log(`🚀 Manually triggering ${jobType} scraping job...`);
    await runJobNow(jobType as 'edhrec' | 'mtgtop8' | 'moxfield');
    
    return NextResponse.json({
      success: true,
      message: `${jobType} scraping job completed successfully`,
    });
  } catch (error) {
    console.error('Error running scrape job:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to run scrape job' 
      },
      { status: 500 }
    );
  }
}
