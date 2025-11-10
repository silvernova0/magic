#!/usr/bin/env node

// Test feedback API endpoint

const testFeedback = async () => {
  const testData = {
    type: 'BUG',
    message: 'Test feedback submission from test script',
    email: 'test@example.com',
    page: '/test'
  };

  console.log('Testing feedback API...');
  console.log('POST /api/feedback with:', testData);

  try {
    const response = await fetch('http://localhost:3000/api/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testData),
    });

    const result = await response.json();
    
    if (response.ok) {
      console.log('✅ Success!', result);
    } else {
      console.log('❌ Error:', result);
    }
  } catch (error) {
    console.error('❌ Request failed:', error);
  }
};

testFeedback();
