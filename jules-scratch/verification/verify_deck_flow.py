from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()

    # 1. Go to home page and verify it's empty
    page.goto("http://localhost:3000")
    expect(page.get_by_text("No decks found.").first).to_be_visible()
    page.screenshot(path="jules-scratch/verification/01_initial_home.png")

    # 2. Go to deck builder
    page.get_by_role("link", name="Build a New Deck").click()
    expect(page).to_have_url("http://localhost:3000/deckbuilder")

    # 3. Fill out form and generate a deck
    page.get_by_label("Your Card Collection").fill("1 Sol Ring\n1 Command Tower")
    page.get_by_label("Deck Theme").fill("Artifacts")
    page.select_option('select#power-level', 'Casual')
    page.get_by_role("button", name="Build Deck").click()

    # 4. Wait for deck to be generated and verify it's there
    expect(page.get_by_text("New Artifacts Deck")).to_be_visible(timeout=60000) # Increased timeout for AI generation
    expect(page.get_by_text("Total Cards:")).to_be_visible()

    # 5. Save the deck
    deck_name = "My Awesome Artifact Deck"
    page.get_by_placeholder("Enter deck name to save").fill(deck_name)
    page.get_by_role("button", name="Save Deck").click()

    # 6. Verify it's saved
    expect(page.get_by_text(deck_name)).to_be_visible()
    expect(page.get_by_text("Saved")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/02_deck_saved.png")

    # 7. Go back to home page
    page.get_by_role("link", name="Back to Library").click()
    expect(page).to_have_url("http://localhost:3000/")

    # 8. Verify the new deck is in the "Saved Decks" list
    expect(page.get_by_text(deck_name)).to_be_visible()
    expect(page.locator("div:has-text('Saved Decks')").locator(f"div:has-text('{deck_name}')")).to_be_visible()
    page.screenshot(path="jules-scratch/verification/03_final_home.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)