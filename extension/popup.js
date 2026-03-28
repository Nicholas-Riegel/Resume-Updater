// Controls the popup UI.
//
// On load: asks the content script on the active tab for the job description.
// On button click: POSTs to the backend and downloads the returned DOCX.

const textarea   = document.getElementById("jobDescription");
const generateBtn = document.getElementById("generateBtn");
const statusDiv  = document.getElementById("status");

// ---------------------------------------------------------------------------
// On popup open — ask the content script for the job description
// ---------------------------------------------------------------------------

// Get the active tab so we know where to send the message
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    chrome.tabs.sendMessage(tab.id, { type: "getJobDescription" }, (response) => {
        if (chrome.runtime.lastError || !response?.jobDescription) {
            // Content script may not have loaded yet (e.g. on chrome:// pages)
            textarea.value = "";
            textarea.placeholder = "Could not scrape this page. Paste the job description manually.";
            generateBtn.disabled = false;
            return;
        }

        textarea.value = response.jobDescription;
        generateBtn.disabled = false;
        setStatus("Job description loaded. Review and click Generate.");
    });
});

// ---------------------------------------------------------------------------
// On button click — send to backend, download the result
// ---------------------------------------------------------------------------

generateBtn.addEventListener("click", async () => {

    const jobDescription = textarea.value.trim();

    if (!jobDescription) {
        setStatus("Please paste a job description first.", true);
        return;
    }

    generateBtn.disabled = true;

    setStatus("Generating resume… this takes about 10 seconds.");

    try {
        // Send the job description as form data — matches what the backend expects
        const formData = new FormData();
        formData.append("job_description", jobDescription);

        const response = await fetch("http://localhost:8000/generate", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Server error ${response.status}: ${text}`);
        }

        // The response body is the DOCX file.
        // We convert it to a blob, create a temporary download URL,
        // and trigger a browser download — same as clicking a download link.
        const blob = await response.blob();
        const url  = URL.createObjectURL(blob);

        // Extract the filename from the Content-Disposition header if present,
        // otherwise fall back to a date-stamped default.
        const disposition = response.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : `resume_${new Date().toISOString().slice(0, 10)}.docx`;

        // Create a hidden <a> tag, click it, then clean up
        const a = document.createElement("a");
        a.href     = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

        setStatus("Download started!");
        
    } catch (err) {
        setStatus(`Error: ${err.message}`, true);
    } finally {
        generateBtn.disabled = false;
    }
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function setStatus(msg, isError = false) {
    statusDiv.textContent = msg;
    statusDiv.className = isError ? "error" : "";
}