// Stage 1: popup opens          → "Scrape Job Description" button only
// Stage 2: scraping             → scrapeBtn disabled briefly
// Stage 3: job description shown → editable textarea + "Generate Summary" + Cancel(→1)
// Stage 4: generating summary   → generateSummaryBtn disabled + Cancel(abort→3)
// Stage 5: summary ready        → both textareas + "Create Document" + Cancel(→3)
// Stage 6: creating document    → createDocBtn disabled + Cancel(→5)

// ---------------------------------------------------------------------------
// Elements
// ---------------------------------------------------------------------------
const jobSection         = document.getElementById("jobSection");
const jobTextarea        = document.getElementById("jobTextarea");
const summarySection     = document.getElementById("summarySection");
const summaryTextarea    = document.getElementById("summaryTextarea");
const scrapeBtn          = document.getElementById("scrapeBtn");
const generateSummaryBtn = document.getElementById("generateSummaryBtn");
const createDocBtn       = document.getElementById("createDocBtn");
const cancelBtn          = document.getElementById("cancelBtn");
const statusDiv          = document.getElementById("status");

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentStage = 0;             // tracks which stage we're in
let activeAbortController = null; // used to cancel an in-flight /preview fetch
let elapsedTimer = null;          // setInterval handle for the elapsed-time counter

// ---------------------------------------------------------------------------
// On popup open — go straight to Stage 1
// ---------------------------------------------------------------------------
// Nothing happens automatically. The user explicitly clicks "Scrape Job Description"
// so they know exactly what text the AI will receive, and can edit it before
// the (slower) AI call is made.
setStage(1);

// ---------------------------------------------------------------------------
// Stage machine
// ---------------------------------------------------------------------------
// All UI transitions go through here. Each button handler just calls setStage()
// rather than scattering .hidden and .disabled changes throughout the file.
function setStage(stage) {
    currentStage = stage;

    // Reset everything to a clean slate first — all hidden, all enabled.
    // Each stage block below only needs to turn things ON.
    scrapeBtn.hidden            = true;
    scrapeBtn.disabled          = false;
    jobSection.hidden           = true;
    summarySection.hidden       = true;
    generateSummaryBtn.hidden   = true;
    generateSummaryBtn.disabled = false;
    createDocBtn.hidden         = true;
    createDocBtn.disabled       = false;
    cancelBtn.hidden            = true;

    if (stage === 1) {
        // Stage 1: clean slate — just the Scrape button
        scrapeBtn.hidden = false;

    } else if (stage === 2) {
        // Stage 2: scraping in progress — keep Scrape button visible but disabled
        scrapeBtn.hidden   = false;
        scrapeBtn.disabled = true;

    } else if (stage === 3) {
        // Stage 3: job description ready — user can read and edit before
        // triggering the (slower) AI call
        jobSection.hidden         = false;
        generateSummaryBtn.hidden = false;
        cancelBtn.hidden          = false;

    } else if (stage === 4) {
        // Stage 4: AI generating — job description still visible, button
        // disabled, Cancel aborts the fetch
        jobSection.hidden           = false;
        generateSummaryBtn.hidden   = false;
        generateSummaryBtn.disabled = true;
        cancelBtn.hidden            = false;

    } else if (stage === 5) {
        // Stage 5: summary ready — both panels visible so the user can
        // compare the job description against the AI output
        jobSection.hidden     = false;
        summarySection.hidden = false;
        createDocBtn.hidden   = false;
        cancelBtn.hidden      = false;

    } else if (stage === 6) {
        // Stage 6: building the DOCX — same as Stage 5 but Create Document
        // is disabled to prevent double-submission
        jobSection.hidden         = false;
        summarySection.hidden     = false;
        createDocBtn.hidden       = false;
        createDocBtn.disabled     = true;
        cancelBtn.hidden          = false;
    }
}

// ---------------------------------------------------------------------------
// Scrape button
// ---------------------------------------------------------------------------
scrapeBtn.addEventListener("click", () => {
    setStage(2);
    setStatus("Scraping…");

    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
        chrome.tabs.sendMessage(tab.id, { type: "getJobDescription" }, (response) => {
            if (chrome.runtime.lastError || !response?.jobDescription) {
                setStatus("Could not scrape this page. Try reloading the tab and clicking Scrape again.", true);
                setStage(1);
                return;
            }
            jobTextarea.value = response.jobDescription;
            setStage(3);
            setStatus("Review the job description, edit if needed, then click Generate Summary.");
        });
    });
});

// ---------------------------------------------------------------------------
// Generate Summary button
// ---------------------------------------------------------------------------
generateSummaryBtn.addEventListener("click", async () => {
    // Use the textarea value — the user may have trimmed or edited the scraped text.
    const jobDescription = jobTextarea.value.trim();
    if (!jobDescription) {
        setStatus("Job description is empty.", true);
        return;
    }

    setStage(4);

    // Show an elapsed-time counter while the AI is thinking.
    // The user can see the app is still working and get a feel for
    // how long to expect next time. setInterval fires every 1000ms.
    let elapsed = 0;
    setStatus(`Generating summary… 0s`);
    elapsedTimer = setInterval(() => {
        elapsed++;
        setStatus(`Generating summary… ${elapsed}s`);
    }, 1000);

    // AbortController lets us cancel this fetch if the user clicks Cancel.
    // We store it in activeAbortController so the Cancel handler can call .abort().
    activeAbortController = new AbortController();

    try {
        const formData = new FormData();
        formData.append("job_description", jobDescription);

        const response = await fetch("http://localhost:8000/preview", {
            method: "POST",
            body: formData,
            signal: activeAbortController.signal,
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server error ${response.status}: ${text}`);
        }

        const data = await response.json();     // {"summary": "..."}
        summaryTextarea.value = data.summary;
        setStage(5);
        setStatus("Review the summary, edit if needed, then click Create Document.");

    } catch (err) {
        if (err.name === "AbortError") {
            // User cancelled — return to Stage 3 (job description still in textarea)
            setStage(3);
            setStatus("");
        } else {
            setStatus(`Error: ${err.message}`, true);
            setStage(3);
        }
    } finally {
        // Always stop the timer, whether we succeeded, failed, or were cancelled
        clearInterval(elapsedTimer);
        elapsedTimer = null;
        activeAbortController = null;
    }
});

// ---------------------------------------------------------------------------
// Cancel button
// ---------------------------------------------------------------------------
cancelBtn.addEventListener("click", () => {
    if (currentStage === 4) {
        // Cancel during AI generation — abort the fetch.
        // The AbortError is caught above, which calls setStage(3).
        activeAbortController?.abort();
    } else if (currentStage === 5 || currentStage === 6) {
        // Cancel from the summary / document stage — clear the summary and
        // return to Stage 3 so they can re-generate with an edited job description
        summaryTextarea.value = "";
        setStage(3);
        setStatus("");
    } else {
        // Cancel from Stage 3 — clear everything and return to Stage 1
        jobTextarea.value = "";
        summaryTextarea.value = "";
        setStage(1);
        setStatus("");
    }
});

// ---------------------------------------------------------------------------
// Create Document button
// ---------------------------------------------------------------------------
createDocBtn.addEventListener("click", async () => {
    const summary = summaryTextarea.value.trim();
    if (!summary) {
        setStatus("Summary is empty — please generate one first.", true);
        return;
    }

    setStage(6);
    setStatus("Building document…");

    try {
        const formData = new FormData();
        // Use the (possibly edited) job description from the textarea
        formData.append("job_description", jobTextarea.value.trim());
        formData.append("summary", summary);   // confirmed summary — AI will be bypassed

        const response = await fetch("http://localhost:8000/generate", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server error ${response.status}: ${text}`);
        }

        // Convert the DOCX response to a blob and trigger a download
        const blob = await response.blob();
        const url  = URL.createObjectURL(blob);

        const disposition = response.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : `resume_${new Date().toISOString().slice(0, 10)}.docx`;

        const a = document.createElement("a");
        a.href     = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

        setStatus("Download started!");
        setStage(5);   // stay on Stage 5 — user can edit and re-create if needed

    } catch (err) {
        setStatus(`Error: ${err.message}`, true);
        setStage(5);   // return to Stage 5 so they can try again without re-generating
    }
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------
function setStatus(msg, isError = false) {
    statusDiv.textContent = msg;
    statusDiv.className   = isError ? "error" : "";
}