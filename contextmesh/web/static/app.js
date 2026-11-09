/**
 * ContextMesh Web Dashboard Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  loadStats();
  loadRecentEvents();

  // Search
  document.getElementById("search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = document.getElementById("query-input").value.trim();
    const source = document.getElementById("source-filter").value;
    if (!query) {
      loadRecentEvents();
      return;
    }

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, source: source || null, limit: 15 })
      });
      const results = await res.json();
      document.getElementById("timeline-title").innerText = `Search Results for "${query}"`;
      renderEvents(results);
    } catch (err) {
      console.error("Search error:", err);
    }
  });

  // Quick Collectors
  document.getElementById("btn-sync-git").addEventListener("click", async () => {
    await fetch("/api/collect/git", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: "." })
    });
    loadStats();
    loadRecentEvents();
  });

  document.getElementById("btn-sync-notes").addEventListener("click", async () => {
    await fetch("/api/collect/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: "." })
    });
    loadStats();
    loadRecentEvents();
  });
});

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    document.getElementById("stat-total").innerText = data.total_events;
    document.getElementById("stat-git").innerText = data.sources_breakdown["git"] || 0;
    document.getElementById("stat-term").innerText = data.sources_breakdown["terminal"] || 0;
    document.getElementById("stat-redacted").innerText = data.redacted_events_count || 0;
  } catch (err) {
    console.error("Stats error:", err);
  }
}

async function loadRecentEvents() {
  try {
    const res = await fetch("/api/events?limit=20");
    const events = await res.json();
    document.getElementById("timeline-title").innerText = "Chronological Context Timeline";
    renderEvents(events);
  } catch (err) {
    console.error("Events error:", err);
  }
}

function renderEvents(events) {
  const container = document.getElementById("events-feed");
  document.getElementById("events-count").innerText = `${events.length} events`;
  container.innerHTML = "";

  if (events.length === 0) {
    container.innerHTML = `
      <div class="p-6 text-center text-xs text-gray-500 bg-gray-900/40 rounded-xl border border-gray-800">
        No context events found. Use the collectors above to index Git repos or notes!
      </div>
    `;
    return;
  }

  events.forEach(e => {
    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-gray-900/70 border border-gray-800/80 hover:border-gray-700 transition space-y-2 text-xs";

    let icon = "file-text";
    let badgeColor = "bg-violet-500/15 text-violet-300 border-violet-500/30";
    if (e.source === "git") {
      icon = "git-branch";
      badgeColor = "bg-cyan-500/15 text-cyan-300 border-cyan-500/30";
    } else if (e.source === "terminal") {
      icon = "terminal";
      badgeColor = "bg-amber-500/15 text-amber-300 border-amber-500/30";
    }

    const timeStr = new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateStr = new Date(e.timestamp).toLocaleDateString();

    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${badgeColor}">${e.source}</span>
          <span class="font-bold text-white">${e.title}</span>
        </div>
        <span class="text-[11px] text-gray-500 font-mono">${dateStr} ${timeStr}</span>
      </div>
      <div class="p-2.5 rounded-lg bg-black/50 border border-gray-800/60 font-mono text-[11px] text-gray-300 whitespace-pre-wrap">${e.snippet}</div>
    `;
    container.appendChild(card);
  });

  lucide.createIcons();
}
