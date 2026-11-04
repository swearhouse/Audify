const logEntries = document.querySelector("#log-entries");
const logStatus = document.querySelector("#log-status");
const clearLogButton = document.querySelector("#clear-log");
const refreshLogButton = document.querySelector("#refresh-log");

function renderEntry(entry) {
  const item = document.createElement("li");
  item.classList.add("log-entry");

  const header = document.createElement("div");
  header.classList.add("log-entry-header");
  const title = document.createElement("span");
  title.classList.add("log-entry-title");
  title.textContent = entry.title || "Unknown song";
  const time = document.createElement("time");
  const date = new Date(entry.timestamp);
  time.dateTime = entry.timestamp;
  time.textContent = Number.isNaN(date.getTime())
    ? entry.timestamp
    : date.toLocaleString();
  header.append(title, time);

  const reason = document.createElement("span");
  reason.classList.add("log-entry-reason");
  reason.textContent = entry.reason;
  item.append(header, reason);

  if (entry.detail) {
    const detail = document.createElement("pre");
    detail.classList.add("log-entry-detail");
    detail.textContent = entry.detail;
    item.append(detail);
  }

  const meta = document.createElement("div");
  meta.classList.add("log-entry-meta");
  if (entry.playlist) {
    meta.append(`Playlist: ${entry.playlist} · `);
  }
  const link = document.createElement("a");
  link.href = entry.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = entry.url;
  meta.append(link);
  item.append(meta);
  return item;
}

async function loadLog() {
  logStatus.textContent = "Loading…";
  try {
    const response = await fetch("/api/log");
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Could not load the log.");
    }
    logEntries.replaceChildren(...result.entries.map(renderEntry));
    clearLogButton.disabled = result.entries.length === 0;
    logStatus.textContent = result.entries.length
      ? `${result.entries.length} unresolved song(s), newest first.`
      : "Nothing logged. Songs that cannot be resolved will show up here.";
  } catch (error) {
    logStatus.textContent = error.message;
  }
}

async function clearLog() {
  if (!window.confirm("Clear the whole log?")) {
    return;
  }
  try {
    const response = await fetch("/api/log", { method: "DELETE" });
    if (!response.ok) {
      throw new Error("Could not clear the log.");
    }
    await loadLog();
  } catch (error) {
    logStatus.textContent = error.message;
  }
}

refreshLogButton.addEventListener("click", loadLog);
clearLogButton.addEventListener("click", clearLog);
loadLog();
