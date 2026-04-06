#!/usr/bin/env node
/**
 * Sniff Yahoo Fantasy network calls to find the projection data endpoint.
 * Usage: npx playwright test --config=false scripts/sniff_projections.mjs
 *    OR: node scripts/sniff_projections.mjs
 */
import { chromium } from "playwright";
import { writeFileSync } from "fs";

const LEAGUE_ID = "34948";
const TEAM_ID = "16";
const DATE = "2026-04-01";

// URLs to visit — team roster with projected stats, and free agents with 7D projected
const URLS = [
  `https://hockey.fantasysports.yahoo.com/hockey/${LEAGUE_ID}/${TEAM_ID}/team?&date=${DATE}&stat1=P&stat2=P`,
  `https://hockey.fantasysports.yahoo.com/hockey/${LEAGUE_ID}/players?&pos=P&sort=PTS&sdir=1&status=A&eteam=ALL&fteam=NONE&stat1=S_PS7&jsenabled=1`,
];

const captured = [];

async function main() {
  console.log("Launching browser — please log in to Yahoo if prompted...\n");

  // Use persistent context so login state is preserved across runs
  const userDataDir = "/tmp/yahoo-playwright-profile";
  const browser = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    viewport: { width: 1400, height: 900 },
  });

  const page = browser.pages()[0] || (await browser.newPage());

  // Capture all network responses
  page.on("response", async (response) => {
    const url = response.url();
    const status = response.status();
    const contentType = response.headers()["content-type"] || "";

    // Capture JSON/API calls and anything with fantasy/stats in the URL
    const isInteresting =
      contentType.includes("json") ||
      url.includes("fantasy") ||
      url.includes("stats") ||
      url.includes("project") ||
      url.includes("player");

    if (isInteresting && status === 200) {
      try {
        const body = await response.text();
        // Only capture if it looks like it has player/stat data
        if (
          body.includes("player") ||
          body.includes("projected") ||
          body.includes("stat")
        ) {
          captured.push({
            url: url.substring(0, 200),
            contentType,
            bodyLength: body.length,
            bodyPreview: body.substring(0, 500),
          });
          console.log(`[CAPTURED] ${url.substring(0, 120)}`);
          console.log(`  Content-Type: ${contentType}, Size: ${body.length}`);
          console.log(`  Preview: ${body.substring(0, 150)}...\n`);
        }
      } catch {
        // Response body not available
      }
    }
  });

  // Navigate to first URL (team page with projections)
  console.log(`Navigating to: ${URLS[0]}\n`);
  await page.goto(URLS[0], { waitUntil: "networkidle", timeout: 60000 });

  // Wait for user to log in if needed
  if (page.url().includes("login.yahoo.com")) {
    console.log(">>> Login required. Please log in to Yahoo in the browser.");
    console.log(">>> Waiting for redirect back to fantasy page...\n");
    await page.waitForURL("**/hockey/**", { timeout: 120000 });
    // Wait for page to fully load
    await page.waitForLoadState("networkidle");
  }

  console.log("Page loaded. Waiting 3s for any lazy-loaded data...\n");
  await page.waitForTimeout(3000);

  // Now visit the free agents page
  console.log(`\nNavigating to: ${URLS[1]}\n`);
  await page.goto(URLS[1], { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(3000);

  // Save all captured requests
  const outFile = "/tmp/yahoo_captured_requests.json";
  writeFileSync(outFile, JSON.stringify(captured, null, 2));
  console.log(`\n=== Done. Captured ${captured.length} requests ===`);
  console.log(`Saved to: ${outFile}`);

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
