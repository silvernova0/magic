
import https from 'https';

const query = "(set:tla OR set:tle)"; // Searching for Avatar: The Last Airbender sets
// Or just search for a known card if I knew one. Let's try a broad search.

function searchScryfall(q: string) {
    const url = `https://api.scryfall.com/cards/search?q=${encodeURIComponent(q)}`;
    console.log(`Searching: ${url}`);

    https.get(url, { headers: { 'User-Agent': 'MagicApp/1.0' } }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
            try {
                const json = JSON.parse(data);
                if (json.object === 'error') {
                    console.log(`❌ Error: ${json.details}`);
                } else {
                    console.log(`✅ Found ${json.total_cards} cards!`);
                    if (json.data && json.data.length > 0) {
                        console.log('Examples:');
                        json.data.slice(0, 3).forEach((c: any) => console.log(`- ${c.name} (${c.set_name})`));
                    }
                }
            } catch (e) {
                console.error("Parse error", e);
            }
        });
    });
}

// Try searching for TLA/TLE sets
searchScryfall("(set:tla OR set:tle)"); 
