const form = document.getElementById("question-form");
const questionInput = document.getElementById("question");
const askButton = document.getElementById("ask-button");
const charCount = document.getElementById("char-count");

const welcome = document.getElementById("welcome");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const answerArea = document.getElementById("answer-area");
const answerSummary = document.getElementById("answer-summary");
const resultsContainer = document.getElementById("results");
const resultCount = document.getElementById("result-count");

questionInput.addEventListener("input", () => {
    charCount.textContent = `${questionInput.value.length} / 1000`;
});

document.querySelectorAll(".suggestion").forEach(button => {
    button.addEventListener("click", () => {
        questionInput.value = button.dataset.question || "";
        charCount.textContent = `${questionInput.value.length} / 1000`;
        questionInput.focus();
    });
});

function show(element) {
    element.classList.remove("hidden");
}

function hide(element) {
    element.classList.add("hidden");
}

function addText(parent, tag, text, className) {
    const element = document.createElement(tag);
    element.textContent = text || "";

    if (className) {
        element.className = className;
    }

    parent.appendChild(element);
    return element;
}

function renderResults(items) {
    resultsContainer.replaceChildren();

    items.forEach(item => {
        const card = document.createElement("article");
        card.className = "result-card";

        const top = document.createElement("div");
        top.className = "result-top";

        addText(top, "h3", item.title || "Untitled document");
        addText(top, "span", item.kind || "Document", "type-pill");
        card.appendChild(top);

        const metadata = [
            item.part_name,
            `Similarity score: ${Number(item.score).toFixed(4)}`
        ].filter(Boolean).join(" · ");

        addText(card, "div", metadata, "result-meta");
        addText(card, "p", item.snippet || "No excerpt available.");

        // Only allow secure HTTP(S) source links.
        if (item.url) {
            try {
                const url = new URL(item.url);

                if (url.protocol === "https:" || url.protocol === "http:") {
                    const link = document.createElement("a");
                    link.className = "source-link";
                    link.href = url.href;
                    link.target = "_blank";
                    link.rel = "noopener noreferrer";
                    link.textContent = "Open source ↗";
                    card.appendChild(link);
                }
            } catch (_) {
                // Skip invalid URLs.
            }
        }

        resultsContainer.appendChild(card);
    });
}

form.addEventListener("submit", async event => {
    event.preventDefault();

    const question = questionInput.value.trim();

    if (!question) {
        questionInput.focus();
        return;
    }

    hide(welcome);
    hide(errorBox);
    hide(answerArea);
    show(loading);

    askButton.disabled = true;

    try {
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "The search request failed.");
        }

        answerSummary.textContent = data.answer ||
            "Search completed. Review the retrieved sources below.";

        renderResults(data.results || []);

        resultCount.textContent =
            `${(data.results || []).length} results`;

        show(answerArea);
    } catch (error) {
        errorBox.textContent =
            `${error.message} Check that the Python server is running.`;
        show(errorBox);
    } finally {
        hide(loading);
        askButton.disabled = false;
    }
});