/**
 * Debug EDHREC HTML Structure
 * Saves the HTML to a file so we can inspect the actual class names and structure
 */

import * as fs from 'fs';
import * as path from 'path';

async function debugEDHREC() {
  const url = 'https://edhrec.com/commanders/atraxa-praetors-voice';
  
  console.log(`Fetching: ${url}\n`);

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const html = await response.text();
    
    // Save to file
    const outputPath = path.join(process.cwd(), 'edhrec-debug.html');
    fs.writeFileSync(outputPath, html, 'utf-8');
    
    console.log(`✓ Saved HTML to: ${outputPath}`);
    console.log(`✓ File size: ${(html.length / 1024).toFixed(2)} KB`);
    console.log(`\nYou can now open this file and inspect the actual HTML structure.`);
    
    // Show some preview of class names found
    const classMatches = html.match(/class="([^"]+)"/g);
    if (classMatches) {
      const uniqueClasses = new Set<string>();
      classMatches.slice(0, 100).forEach(match => {
        const className = match.match(/class="([^"]+)"/)?.[1];
        if (className && (className.includes('Card') || className.includes('card') || 
                         className.includes('Combo') || className.includes('combo') ||
                         className.includes('container') || className.includes('Container'))) {
          uniqueClasses.add(className);
        }
      });
      
      console.log(`\nSample relevant class names found:`);
      Array.from(uniqueClasses).slice(0, 20).forEach(cls => {
        console.log(`  - ${cls}`);
      });
    }

  } catch (error) {
    console.error('❌ Error:', error);
  }
}

debugEDHREC();
