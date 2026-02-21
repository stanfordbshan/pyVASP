const modeLabel = document.getElementById("mode-label");
const resultEl = document.getElementById("result");
const form = document.getElementById("run-form");

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

  const operation = document.getElementById("operation").value;
  const payload = {
    outcar_path: document.getElementById("outcar_path").value,
  };

  let endpoint = "/ui/summary";
  if (operation === "summary") {
    payload.include_history = document.getElementById("include_history").checked;
  } else {
    endpoint = "/ui/diagnostics";
    payload.energy_tolerance_ev = Number(document.getElementById("energy_tol").value);
    payload.force_tolerance_ev_per_a = Number(document.getElementById("force_tol").value);
  }

  resultEl.textContent = "Running...";

  try {
    const response = await fetch(endpoint, {
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
