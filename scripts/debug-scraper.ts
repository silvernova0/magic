import { scrapeCommanderDetails } from '../src/lib/scrapers/edhrec';

async function main() {
    const commanderUrl = "https://edhrec.com/commanders/godo-bandit-warlord";
    console.log(`🔍 Debugging scraper for: ${commanderUrl}`);

    try {
        const details = await scrapeCommanderDetails(commanderUrl);
        console.log("✅ Scrape Result:");
        console.log(JSON.stringify(details, null, 2));

        if (details.combos && details.combos.length > 0) {
            console.log(`🎉 Found ${details.combos.length} combos!`);
        } else {
            console.log("⚠️ No combos found. Check selectors.");
        }
    } catch (error) {
        console.error("❌ Error scraping:", error);
    }
}

main();
