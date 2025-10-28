/**
 * Export card database to training format (Node.js version)
 * Run with: node scripts/export-card-knowledge.js
 */
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

const prisma = new PrismaClient();

async function exportCardKnowledge() {
  console.log('Fetching cards from database...');
  
  const cards = await prisma.card.findMany({
    where: {
      oracleText: { not: null }
    },
    orderBy: { edhrecRank: 'asc' }
  });
  
  console.log(`Found ${cards.length} cards`);
  
  const trainingData = [];
  
  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    
    if ((i + 1) % 1000 === 0) {
      console.log(`Processed ${i + 1}/${cards.length} cards...`);
    }
    
    // Parse JSON fields
    let colorIdentity = [];
    try {
      colorIdentity = card.colorIdentity ? JSON.parse(card.colorIdentity) : [];
    } catch (e) {
      // If not JSON, try splitting string
      colorIdentity = card.colorIdentity ? card.colorIdentity.split(',').map(c => c.trim()) : [];
    }
    
    // Format 1: Card description
    if (card.oracleText) {
      const colorIdentityStr = colorIdentity.length > 0 ? colorIdentity.join(', ') : 'colorless';
      
      trainingData.push({
        instruction: `Describe the Magic: The Gathering card '${card.name}'.`,
        output: `${card.name} is a ${card.typeLine} with mana cost ${card.manaCost || 'N/A'}. ` +
               `${card.oracleText} ` +
               `Its color identity is ${colorIdentityStr}.`,
        type: 'card_description',
        metadata: {
          cardName: card.name,
          powerLevel: card.powerLevel,
          edhrecRank: card.edhrecRank
        }
      });
    }
    
    // Format 2: Commander eligibility
    if (card.isCommander) {
      const colorIdentityStr = colorIdentity.length > 0 ? colorIdentity.join(', ') : 'colorless';
      
      trainingData.push({
        instruction: `Can ${card.name} be a Commander?`,
        output: `Yes, ${card.name} can be a Commander. It is a ${card.typeLine} with color identity ${colorIdentityStr}.`,
        type: 'commander_check',
        metadata: {
          cardName: card.name,
          isCommander: true,
          colorIdentity: colorIdentity
        }
      });
    }
    
    // Format 3: Power level assessment
    if (card.powerLevel) {
      const powerDesc = card.powerLevel < 4 ? 'casual' : 
                       card.powerLevel < 6 ? 'focused' : 
                       card.powerLevel < 8 ? 'optimized' : 'cEDH';
      
      trainingData.push({
        instruction: `What power level is ${card.name} in Commander?`,
        output: `${card.name} has a power level of ${card.powerLevel}/10, making it a ${powerDesc} card. ` +
               `EDHREC rank: ${card.edhrecRank || 'Not ranked'}.`,
        type: 'power_assessment',
        metadata: {
          cardName: card.name,
          powerLevel: card.powerLevel,
          edhrecRank: card.edhrecRank
        }
      });
    }
    
    // Format 4: Color identity
    const colorIdentityStr2 = colorIdentity.length > 0 ? colorIdentity.join(', ') : 'colorless';
    
    trainingData.push({
      instruction: `What is the color identity of ${card.name}?`,
      output: `The color identity of ${card.name} is ${colorIdentityStr2}. ` +
             `This means it can only be used in Commander decks with commanders that include these colors.`,
      type: 'color_identity',
      metadata: {
        cardName: card.name,
        colorIdentity: colorIdentity
      }
    });
    
    // Format 5: Saltiness (if applicable)
    if (card.saltiness && card.saltiness > 0) {
      const saltDesc = card.saltiness >= 2 ? 'extremely salty' :
                      card.saltiness >= 1 ? 'high salt' :
                      card.saltiness >= 0.5 ? 'moderate salt' : 'low salt';
      
      trainingData.push({
        instruction: `How salty is ${card.name} in Commander?`,
        output: `${card.name} has a saltiness score of ${card.saltiness}, making it a ${saltDesc} card. ` +
               `This means some players may find it unfun to play against.`,
        type: 'saltiness_assessment',
        metadata: {
          cardName: card.name,
          saltiness: card.saltiness
        }
      });
    }
  }
  
  // Save to JSONL file
  const outputDir = path.join(__dirname, '..', 'data', 'training');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const outputFile = path.join(outputDir, 'card_knowledge.jsonl');
  
  const jsonlContent = trainingData.map(entry => JSON.stringify(entry)).join('\n');
  fs.writeFileSync(outputFile, jsonlContent, 'utf-8');
  
  const fileSizeMB = fs.statSync(outputFile).size / 1024 / 1024;
  
  console.log(`\n✓ Exported ${trainingData.length} training entries`);
  console.log(`✓ Saved to: ${outputFile}`);
  console.log(`✓ File size: ${fileSizeMB.toFixed(2)} MB`);
  
  await prisma.$disconnect();
}

exportCardKnowledge()
  .catch((error) => {
    console.error('Error exporting card knowledge:', error);
    process.exit(1);
  });
