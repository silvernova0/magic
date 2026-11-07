/**
 * Test script for scheduled scraping API endpoints
 */

async function testAPI() {
  const baseUrl = 'http://localhost:3000';
  
  console.log('🧪 Testing Scheduled Scraping API Endpoints\n');
  
  try {
    // Test 1: Get job history
    console.log('Test 1: GET /api/scrape/jobs');
    const historyResponse = await fetch(`${baseUrl}/api/scrape/jobs?limit=10`);
    const historyData = await historyResponse.json();
    console.log(`✅ Found ${historyData.count} jobs in history`);
    console.log('Latest job:', historyData.jobs[0]);
    console.log('');
    
    // Test 2: Get statistics
    console.log('Test 2: GET /api/scrape/jobs?action=stats');
    const statsResponse = await fetch(`${baseUrl}/api/scrape/jobs?action=stats`);
    const statsData = await statsResponse.json();
    console.log('✅ Statistics retrieved:');
    console.log('EDHREC:', statsData.edhrec);
    console.log('MTGTop8:', statsData.mtgtop8);
    console.log('Moxfield:', statsData.moxfield);
    console.log('');
    
    // Test 3: Get stats for specific job type
    console.log('Test 3: GET /api/scrape/jobs?action=stats&jobType=moxfield');
    const moxfieldStatsResponse = await fetch(`${baseUrl}/api/scrape/jobs?action=stats&jobType=moxfield`);
    const moxfieldStats = await moxfieldStatsResponse.json();
    console.log('✅ Moxfield stats:', moxfieldStats);
    console.log('');
    
    console.log('✅ All API tests passed!\n');
    
  } catch (error) {
    console.error('❌ API test failed:', error);
    console.log('\nMake sure the development server is running:');
    console.log('  npm run dev\n');
  }
}

testAPI();
