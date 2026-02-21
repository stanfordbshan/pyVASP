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
  const outcarPath = document.getElementById("outcar_path").value;
  const includeHistory = document.getElementById("include_history").checked;

  let endpoint = "/ui/summary";
  let payload = { outcar_path: outcarPath, include_history: includeHistory };

  if (operation === "diagnostics") {
    endpoint = "/ui/diagnostics";
    payload = {
      outcar_path: outcarPath,
      energy_tolerance_ev: Number(document.getElementById("energy_tol").value),
      force_tolerance_ev_per_a: Number(document.getElementById("force_tol").value),
    };
  } else if (operation === "convergence_profile") {
    endpoint = "/ui/convergence-profile";
    payload = { outcar_path: outcarPath };
  } else if (operation === "electronic_metadata") {
    endpoint = "/ui/electronic-metadata";
    payload = {
      eigenval_path: document.getElementById("eigenval_path").value || null,
      doscar_path: document.getElementById("doscar_path").value || null,
    };
  } else if (operation === "generate_relax_input") {
    endpoint = "/ui/generate-relax-input";

    let structure;
    try {
      structure = JSON.parse(document.getElementById("structure_json").value);
    } catch (error) {
      resultEl.textContent = JSON.stringify({ error: `Invalid structure JSON: ${error}` }, null, 2);
      return;
    }

    payload = {
      structure,
      kmesh: [
        Number(document.getElementById("kmesh_x").value),
        Number(document.getElementById("kmesh_y").value),
        Number(document.getElementById("kmesh_z").value),
      ],
      gamma_centered: document.getElementById("gamma_centered").checked,
    };
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
