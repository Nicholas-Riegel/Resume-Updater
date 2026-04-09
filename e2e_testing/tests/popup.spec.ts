// Playwright tests for the Resume Tailor extension popup.
//
// What we're testing:
//   The popup has a six-stage state machine driven by setStage(n) in popup.js.
//   Each test drives the popup to a particular stage and checks that the right
//   elements are shown and the right ones are hidden or disabled.
//
// What we're NOT testing:
//   Real Chrome extension loading, or real network calls to the backend.
//   Both are mocked — this suite is purely about UI behaviour.

import { test, expect, Page } from '@playwright/test';
import path from 'path';

// __dirname is available here because Playwright runs TypeScript files in CommonJS
// mode internally — unlike plain JS ES modules, we don't need any workaround.

// Absolute file:// URL to popup.html — Playwright will open this like a web page
const popupUrl = `file://${path.resolve(__dirname, '../../extension/popup.html')}`;

// ---------------------------------------------------------------------------
// Helper: inject Chrome API mocks
// ---------------------------------------------------------------------------
// popup.js calls chrome.tabs.query() to get the active tab ID, then calls
// chrome.tabs.sendMessage() with { type: "getJobDescription" } to ask the
// content script for the scraped text.
//
// Those APIs don't exist outside a real extension context. page.addInitScript()
// runs our code in the browser BEFORE popup.js executes, so the popup finds
// a ready-made mock chrome object waiting for it.
//
// The `scrapeResult` parameter controls what text the fake content script returns.
async function injectChromeMocks(page: Page, { scrapeResult = 'Test job description.' } = {}) {
    await page.addInitScript((jobDescription) => {
        // Cast window to any — the chrome API doesn't exist on the standard
        // Window type, but we're deliberately faking it for the test context.
        (window as any).chrome = {
            tabs: {
                // Returns a fake active tab — popup.js only needs the `id` property
                query: (_opts: any, callback: any) => callback([{ id: 1, url: 'https://example.com/jobs/123' }]),

                // Simulates the content script returning a scraped job description.
                // popup.js checks response?.jobDescription, so the shape must match.
                sendMessage: (_tabId: any, _message: any, callback: any) => callback({ jobDescription }),
            },
            runtime: {
                // popup.js checks chrome.runtime.lastError after sendMessage.
                // null means "no error" — the scrape succeeded.
                lastError: null,
            },
        };
    }, scrapeResult);
}

// ---------------------------------------------------------------------------
// Helper: mock backend fetch routes
// ---------------------------------------------------------------------------
// page.route() intercepts outgoing fetch calls matching the given URL.
// The handler immediately returns a fake response — no real server needed.
//
// The `summary` parameter controls what the fake /preview endpoint returns.
async function mockBackendRoutes(page: Page, { summary = 'A mocked AI-generated summary.' } = {}) {
    
    // Mock POST /preview — the AI summary endpoint
    await page.route('http://localhost:8000/preview', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ summary }),
        })
    );

    // Mock POST /generate — the document generation endpoint.
    // The popup only checks that the response is ok, then triggers a download,
    // so a small fake body with the correct Content-Type is all we need.
    await page.route('http://localhost:8000/generate', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            body: 'fake-docx-content',
        })
    );
}

// ===========================================================================
// Tests
// ===========================================================================

test('Stage 1 — only the Scrape button is visible on popup open', async ({ page }) => {
    await injectChromeMocks(page);
    await page.goto(popupUrl);

    await expect(page.locator('h2')).toHaveText('Resume Tailor');
    
    // The Scrape button should be the only interactive element visible
    await expect(page.locator('#scrapeBtn')).toBeVisible();
    // await expect(page.locator('#scrapeBtn')).toBeHidden();
    await expect(page.locator('#scrapeBtn')).toBeEnabled();

    // Everything else starts hidden
    await expect(page.locator('#jobSection')).toBeHidden();
    await expect(page.locator('#summarySection')).toBeHidden();
    await expect(page.locator('#generateSummaryBtn')).toBeHidden();
    await expect(page.locator('#createDocBtn')).toBeHidden();
    await expect(page.locator('#cancelBtn')).toBeHidden();
});

test('Stage 3 — job description textarea appears after scraping', async ({ page }) => {

    await injectChromeMocks(page, { scrapeResult: 'We are hiring a Python engineer.' });
    await page.goto(popupUrl);

    await page.locator('#scrapeBtn').click();

    // Stage 3: job description section + two buttons visible
    await expect(page.locator('#jobSection')).toBeVisible();
    await expect(page.locator('#generateSummaryBtn')).toBeVisible();
    await expect(page.locator('#cancelBtn')).toBeVisible();

    // The textarea should contain the text the mock content script returned
    await expect(page.locator('#jobTextarea')).toHaveValue('We are hiring a Python engineer.');

    // Scrape button and summary section should be gone
    await expect(page.locator('#scrapeBtn')).toBeHidden();
    await expect(page.locator('#summarySection')).toBeHidden();
});

test('Stage 4 — Generate Summary button is disabled while AI is generating', async ({ page }) => {
    
    await injectChromeMocks(page);

    // Route /preview to never resolve — keeps the popup in Stage 4 indefinitely.
    // A timed delay (e.g. 500ms) causes a race condition: the route fulfils before
    // Playwright can assert the disabled state, and the popup moves to Stage 5.
    // Hanging guarantees we stay in Stage 4 for as long as the assertion needs.
    await page.route('http://localhost:8000/preview', () => { /* hang indefinitely */ });

    await page.goto(popupUrl);
    await page.locator('#scrapeBtn').click();
    await page.locator('#generateSummaryBtn').click();

    // During Stage 4 the button must be disabled so the user can't double-submit
    await expect(page.locator('#generateSummaryBtn')).toBeDisabled();
});

test('Stage 5 — both textareas visible and pre-filled after AI responds', async ({ page }) => {

    await injectChromeMocks(page, { scrapeResult: 'Hiring a backend engineer with Python skills.' });
    await mockBackendRoutes(page, { summary: 'A mocked AI-generated summary.' });
    await page.goto(popupUrl);

    await page.locator('#scrapeBtn').click();
    await page.locator('#generateSummaryBtn').click();

    // Wait for the summary section to appear (signals the /preview response arrived)
    await expect(page.locator('#summarySection')).toBeVisible();

    // Summary textarea should contain exactly what the mock returned
    await expect(page.locator('#summaryTextarea')).toHaveValue('A mocked AI-generated summary.');

    // Create Document button should now be visible
    await expect(page.locator('#createDocBtn')).toBeVisible();

    // Both textareas must be editable — the user can adjust either before creating the doc
    await expect(page.locator('#jobTextarea')).toBeEditable();
    await expect(page.locator('#summaryTextarea')).toBeEditable();
});

test('Stage 6 — Create Document button is disabled while building the DOCX', async ({ page }) => {

    await injectChromeMocks(page);
    await page.route('http://localhost:8000/preview', (route) =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ summary: 'Mock summary.' }),
        })
    );

    // Route /generate to never resolve — same reasoning as Stage 4 above.
    await page.route('http://localhost:8000/generate', () => { /* hang indefinitely */ });

    await page.goto(popupUrl);
    await page.locator('#scrapeBtn').click();
    await page.locator('#generateSummaryBtn').click();
    await expect(page.locator('#summarySection')).toBeVisible();
    await page.locator('#createDocBtn').click();

    // During Stage 6 the button should be disabled to prevent double-submission
    await expect(page.locator('#createDocBtn')).toBeDisabled();
});

test('Cancel during Stage 4 — aborts the AI call and returns to Stage 3', async ({ page }) => {

    await injectChromeMocks(page, { scrapeResult: 'Hiring a Python engineer.' });

    // Route /preview to never resolve — simulates a long-running AI call
    await page.route('http://localhost:8000/preview', () => { /* hang indefinitely */ });

    await page.goto(popupUrl);
    await page.locator('#scrapeBtn').click();
    await page.locator('#generateSummaryBtn').click();

    // We're in Stage 4 — click Cancel to abort
    await page.locator('#cancelBtn').click();

    // Should be back at Stage 3: job description still in textarea, summary gone
    await expect(page.locator('#jobSection')).toBeVisible();
    await expect(page.locator('#jobTextarea')).toHaveValue('Hiring a Python engineer.');
    await expect(page.locator('#summarySection')).toBeHidden();
    await expect(page.locator('#generateSummaryBtn')).toBeVisible();
    await expect(page.locator('#generateSummaryBtn')).toBeEnabled();
});

test('Cancel during Stage 3 — clears everything and returns to Stage 1', async ({ page }) => {
    await injectChromeMocks(page);
    await page.goto(popupUrl);

    await page.locator('#scrapeBtn').click();

    // We're in Stage 3 — click Cancel
    await page.locator('#cancelBtn').click();

    // Should be back at Stage 1: only the Scrape button visible
    await expect(page.locator('#scrapeBtn')).toBeVisible();
    await expect(page.locator('#jobSection')).toBeHidden();
    await expect(page.locator('#summarySection')).toBeHidden();
});

