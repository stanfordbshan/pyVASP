const modeLabel = document.getElementById("mode-label");
const resultEl = document.getElementById("result");
const form = document.getElementById("summary-form");

async function loadConfig() {
  try {
    const response = await fetch("/ui/config");
    const config = await response.json();
    modeLabel.textContent = `Execution mode: ${config.mode} | API base: ${config.api_base_url}`;
  } catch (_error) {
    modeLabel.textContent = "Execution mode: unavailable";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    outcar_path: document.getElementById("outcar_path").value,
    include_history: document.getElementById("include_history").checked,
  };

  resultEl.textContent = "Running...";

  try {
    const response = await fetch("/ui/summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      resultEl.textContent = JSON.stringify({ error: data.detail ?? data }, null, 2);
      return;
    }

    resultEl.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    resultEl.textContent = JSON.stringify({ error: String(error) }, null, 2);
  }
});

loadConfig();
