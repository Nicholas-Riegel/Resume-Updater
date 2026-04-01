// This script is injected into every tab the user visits.
// It listens for a "getJobDescription" message from the popup,
// then replies with the best candidate text it can find on the page.

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type !== "getJobDescription") return;

    const text = extractJobDescription();
    sendResponse({ jobDescription: text });

    // Return true to signal that we'll call sendResponse asynchronously
    // (required by Chrome even when we respond synchronously)
    return true;
});


function extractJobDescription() {
    // Site-specific selectors — tried first because they target the job
    // description container directly, which is far more reliable than guessing.
    const siteSelectors = [
        // LinkedIn
        ".jobs-description__content",
        ".jobs-box__html-content",
        // Indeed
        "#jobDescriptionText",
        // Greenhouse (common ATS)
        "#content",
        ".job-post-description",
        // Lever (common ATS)
        ".posting-content",
        // Workday (common ATS)
        "[data-automation-id='jobPostingDescription']",
        // Ashby
        ".ashby-job-posting-brief-description",
        // SmartRecruiters
        ".job-overview",
        // Workable
        ".job-description",
        // Jobvite
        ".jv-body",
        // BambooHR
        "#BambooHR-ATS",
    ];

    for (const selector of siteSelectors) {
        const el = document.querySelector(selector);
        if (el?.innerText?.trim().length > 100) {
            return el.innerText.trim();
        }
    }

    // Heuristic fallback: find the element with the most text on the page,
    // but skip obvious page-level containers. The tell for a layout wrapper
    // is having many direct block-level children (nav bars, sidebars, footers
    // all live inside them). A real job description section has mostly text
    // nodes and inline elements, not a forest of <div> and <section> children.
    //
    // We allow up to 8 direct block children before skipping — erring on the
    // side of grabbing more rather than less.
    const BLOCK_TAGS = new Set(["DIV", "SECTION", "ARTICLE", "HEADER", "FOOTER", "MAIN", "ASIDE", "NAV"]);

    const candidates = Array.from(
        document.querySelectorAll("p, div, section, article, li")
    );

    let best = { text: "", length: 0 };

    for (const el of candidates) {
        // innerText gives rendered text (excluding hidden elements and script content)
        const text = el.innerText?.trim() ?? "";
        if (text.length <= best.length) continue;

        // Count direct block-level children to detect layout containers.
        let blockChildren = 0;
        for (const child of el.children) {
            if (BLOCK_TAGS.has(child.tagName)) blockChildren++;
        }
        if (blockChildren > 8) continue;

        best = { text, length: text.length };
    }

    // If nothing useful was found, fall back to the full page body text
    return best.length > 100
        ? best.text
        : document.body.innerText?.trim() ?? "";
}