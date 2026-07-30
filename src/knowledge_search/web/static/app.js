const apiPrefix = document.body.dataset.apiPrefix;
const uploadForm = document.querySelector("#upload-form");
const fileInput = document.querySelector("#document-file");
const fileLabel = document.querySelector("#file-label");
const uploadMessage = document.querySelector("#upload-message");
const searchForm = document.querySelector("#search-form");
const searchQuery = document.querySelector("#search-query");
const searchMode = document.querySelector("#search-mode");
const answerButton = document.querySelector("#answer-button");
const answerPanel = document.querySelector("#answer-panel");
const answerText = document.querySelector("#answer-text");
const generationStatus = document.querySelector("#generation-status");
const resultsMeta = document.querySelector("#results-meta");
const resultsContainer = document.querySelector("#results");
const resultTemplate = document.querySelector("#result-template");
const documentList = document.querySelector("#document-list");
const documentTemplate = document.querySelector("#document-template");
const documentCount = document.querySelector("#document-count");
const refreshDocuments = document.querySelector("#refresh-documents");
const systemState = document.querySelector("#system-state");

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files[0]?.name || "Choose a source file";
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  setMessage(uploadMessage, "Uploading…");
  const body = new FormData();
  body.append("document", file);
  try {
    const response = await fetch(`${apiPrefix}/documents`, {
      method: "POST",
      body,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(problemMessage(payload));
    setMessage(uploadMessage, "Queued for indexing.");
    fileInput.value = "";
    fileLabel.textContent = "Choose a source file";
    await loadDocuments();
    pollIngestion(payload.ingestion_job.id);
  } catch (error) {
    setMessage(uploadMessage, error.message, true);
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  answerPanel.hidden = true;
  await runSearch();
});

answerButton.addEventListener("click", async () => {
  const question = searchQuery.value.trim();
  if (!question) {
    searchQuery.focus();
    return;
  }
  resultsMeta.textContent = "Retrieving evidence and preparing an answer…";
  try {
    const response = await fetch(`${apiPrefix}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        mode: searchMode.value,
        limit: 5,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(problemMessage(payload));
    renderResults(payload.sources);
    resultsMeta.textContent = `${payload.sources.length} supporting passage${plural(payload.sources.length)}`;
    answerPanel.hidden = false;
    generationStatus.textContent = payload.generation_status.replaceAll("_", " ");
    answerText.textContent =
      payload.answer ||
      "Answer generation is disabled. The retrieved evidence remains available below.";
  } catch (error) {
    resultsMeta.textContent = error.message;
  }
});

refreshDocuments.addEventListener("click", loadDocuments);

async function runSearch() {
  const query = searchQuery.value.trim();
  if (!query) return;
  resultsMeta.textContent = "Searching the corpus…";
  resultsContainer.replaceChildren();
  const parameters = new URLSearchParams({
    q: query,
    mode: searchMode.value,
    limit: "10",
  });
  try {
    const response = await fetch(`${apiPrefix}/search?${parameters}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(problemMessage(payload));
    renderResults(payload.items);
    resultsMeta.textContent = `${payload.items.length} passage${plural(payload.items.length)} · ${payload.mode} retrieval`;
  } catch (error) {
    resultsMeta.textContent = error.message;
  }
}

function renderResults(results) {
  resultsContainer.replaceChildren();
  results.forEach((result, index) => {
    const card = resultTemplate.content.cloneNode(true);
    card.querySelector(".result-position").textContent = `Result ${index + 1}`;
    card.querySelector(".result-score").textContent = result.score.toFixed(4);
    card.querySelector(".result-file").textContent = result.citation.original_filename;
    card.querySelector(".result-location").textContent = locationLabel(result.citation);
    card.querySelector(".result-excerpt").textContent = result.citation.excerpt;
    const ranks = [];
    if (result.keyword_rank) ranks.push(`keyword #${result.keyword_rank}`);
    if (result.vector_rank) ranks.push(`vector #${result.vector_rank}`);
    card.querySelector(".rank-details").textContent = ranks.join(" · ");
    resultsContainer.append(card);
  });
  if (results.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No ready document passages matched this query.";
    resultsContainer.append(empty);
  }
}

async function loadDocuments() {
  try {
    const response = await fetch(`${apiPrefix}/documents?limit=100`);
    const payload = await response.json();
    if (!response.ok) throw new Error(problemMessage(payload));
    documentList.replaceChildren();
    const readyCount = payload.items.filter((item) => item.status === "ready").length;
    documentCount.textContent = `${readyCount} ready document${plural(readyCount)}`;
    payload.items.forEach((item) => documentList.append(documentRow(item)));
    if (payload.items.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No documents have been uploaded yet.";
      documentList.append(empty);
    }
  } catch (error) {
    documentList.textContent = error.message;
  }
}

function documentRow(item) {
  const row = documentTemplate.content.cloneNode(true);
  row.querySelector(".document-name").textContent = item.original_filename;
  row.querySelector(".document-meta").textContent =
    `${formatBytes(item.size_bytes)} · ${item.media_type}`;
  const status = row.querySelector(".document-status");
  status.textContent = item.status;
  status.classList.add(item.status);
  const deleteButton = row.querySelector(".delete-button");
  deleteButton.disabled = !["ready", "failed"].includes(item.status);
  deleteButton.addEventListener("click", () => deleteDocument(item));
  return row;
}

async function deleteDocument(item) {
  if (!window.confirm(`Delete ${item.original_filename}?`)) return;
  const response = await fetch(`${apiPrefix}/documents/${item.id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const payload = await response.json();
    window.alert(problemMessage(payload));
    return;
  }
  await loadDocuments();
}

async function pollIngestion(jobId) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
    const response = await fetch(`${apiPrefix}/ingestion-jobs/${jobId}`);
    if (!response.ok) return;
    const job = await response.json();
    await loadDocuments();
    if (job.status === "succeeded") {
      setMessage(uploadMessage, "Document is ready to search.");
      return;
    }
    if (job.status === "failed") {
      setMessage(uploadMessage, `Indexing failed: ${job.failure_code}.`, true);
      return;
    }
  }
  setMessage(uploadMessage, "Indexing is still in progress. Refresh the corpus to check.");
}

async function checkReadiness() {
  try {
    const response = await fetch("/health/ready");
    if (!response.ok) throw new Error();
    systemState.classList.add("ready");
    systemState.lastChild.textContent = " Services ready";
  } catch {
    systemState.classList.remove("ready");
    systemState.lastChild.textContent = " Services unavailable";
  }
}

function locationLabel(citation) {
  const parts = [...citation.section_path];
  if (citation.page_number) parts.push(`page ${citation.page_number}`);
  return parts.join(" › ") || "Source location unavailable";
}

function problemMessage(payload) {
  return payload.detail || "The request could not be completed.";
}

function setMessage(element, message, failed = false) {
  element.textContent = message;
  element.classList.toggle("failed", failed);
}

function formatBytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function plural(count) {
  return count === 1 ? "" : "s";
}

checkReadiness();
loadDocuments();
