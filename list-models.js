// List all available Gemini models for your API key
require('dotenv').config();

async function listModels() {
  const apiKey = process.env.GEMINI_API_KEY;
  
  console.log('Fetching available models...\n');
  
  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    console.log('✅ Available Models:\n');
    data.models.forEach(model => {
      console.log(`📌 ${model.name}`);
      console.log(`   Display Name: ${model.displayName}`);
      console.log(`   Supports: ${model.supportedGenerationMethods.join(', ')}`);
      console.log(`   Input Token Limit: ${model.inputTokenLimit}`);
      console.log(`   Output Token Limit: ${model.outputTokenLimit}`);
      console.log('');
    });
    
    // Find models that support generateContent
    const generateModels = data.models
      .filter(m => m.supportedGenerationMethods.includes('generateContent'))
      .map(m => m.name.replace('models/', ''));
    
    console.log('\n🎯 Models that support generateContent:');
    generateModels.forEach(name => console.log(`   - ${name}`));
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

listModels();
