// Quick test script to verify Gemini API connectivity
require('dotenv').config();
const { GoogleGenerativeAI } = require('@google/generative-ai');

async function testGemini() {
  console.log('Testing Gemini API...');
  console.log('API Key present:', !!process.env.GEMINI_API_KEY);
  console.log('API Key starts with:', process.env.GEMINI_API_KEY?.substring(0, 10) + '...');
  
  try {
    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
    const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });
    
    console.log('\nSending test request...');
    const result = await model.generateContent({
      contents: [{ role: 'user', parts: [{ text: 'Say "Hello, MTG deck builder!" in JSON format with a "message" field.' }] }],
      generationConfig: {
        temperature: 1,
        maxOutputTokens: 100,
        responseMimeType: 'application/json',
      },
    });
    
    const response = result.response;
    console.log('\n✅ SUCCESS! Gemini API is working.');
    console.log('Response:', response.text());
  } catch (error) {
    console.error('\n❌ ERROR:', error.message);
    if (error.status === 404) {
      console.log('\n💡 The model name might be incorrect. Let\'s try listing available models...');
      console.log('Visit: https://ai.google.dev/gemini-api/docs/models/gemini');
    } else if (error.status === 403) {
      console.log('\n💡 API Key issue - check if the key is valid and has the right permissions');
    }
  }
}

testGemini();
