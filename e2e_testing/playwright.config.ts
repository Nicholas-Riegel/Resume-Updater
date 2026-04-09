// Central configuration for all Playwright tests.
// Playwright reads this file automatically when you run `npx playwright test`.

import { defineConfig } from '@playwright/test';

export default defineConfig({
    
    // Where to look for test files
    testDir: './tests',

    // Run tests one at a time, not in parallel.
    // This keeps output readable and avoids conflicts if tests share any state.
    fullyParallel: false,

    // How long a single test can run before it's considered failed.
    // 15 seconds is generous — our tests are pure UI with no real network calls.
    timeout: 15000,

    use: {
        // Chromium is the engine behind Chrome.
        // We're not using a real Chrome extension context here — just a Chromium
        // browser that can open popup.html as a regular page.
        browserName: 'chromium',
        launchOptions: { slowMo: 1000 },
    },
});
