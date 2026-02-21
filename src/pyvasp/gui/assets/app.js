const modeLabel = document.getElementById("mode-label");
const outputDirInput = document.getElementById("output_dir");
const batchOutputDirsInput = document.getElementById("batch_output_dirs");
const batchRootDirInput = document.getElementById("batch_root_dir");
const pickOutputDirButton = document.getElementById("pick_output_dir");
const pickBatchRootDirButton = document.getElementById("pick_batch_root_dir");
const addBatchOutputDirButton = document.getElementById("add_batch_output_dir");
const clearBatchOutputDirsButton = document.getElementById("clear_batch_output_dirs");

const includeHistoryInput = document.getElementById("include_history");
const reportIncludeElectronicInput = document.getElementById("report_include_electronic");
const energyToleranceInput = document.getElementById("energy_tol");
const forceToleranceInput = document.getElementById("force_tol");
const batchFailFastInput = document.getElementById("batch_fail_fast");
const batchRecursiveInput = document.getElementById("batch_recursive");
const batchMaxRunsInput = document.getElementById("batch_max_runs");
const batchTopNInput = document.getElementById("batch_top_n");

const parseEigenvalInput = document.getElementById("parse_eigenval");
const parseDoscarInput = document.getElementById("parse_doscar");
const dosWindowInput = document.getElementById("dos_window_ev");
const dosMaxPointsInput = document.getElementById("dos_max_points");
const exportDatasetInput = document.getElementById("export_dataset");
const exportDelimiterInput = document.getElementById("export_delimiter");

const structureJsonInput = document.getElementById("structure_json");
const kmeshXInput = document.getElementById("kmesh_x");
const kmeshYInput = document.getElementById("kmesh_y");
const kmeshZInput = document.getElementById("kmesh_z");
const gammaCenteredInput = document.getElementById("gamma_centered");

const resultStatusEl = document.getElementById("result-status");
const resultRenderedEl = document.getElementById("result_rendered");
const resultRawEl = document.getElementById("result_raw");
const viewRenderedButton = document.getElementById("view_rendered");
const viewRawButton = document.getElementById("view_raw");

const tabButtons = Array.from(document.querySelectorAll(".tab"));
const taskPages = Array.from(document.querySelectorAll(".task-page"));
const actionButtons = Array.from(document.querySelectorAll("[data-action]"));

const STORAGE_KEYS = {
  outputDir: "pyvasp.ui.outputDir",
  batchDirs: "pyvasp.ui.batchDirs",
  batchRootDir: "pyvasp.ui.batchRootDir",
  activePage: "pyvasp.ui.activePage",
};

const ACTION_LABELS = {
  run_report: "Run Report",
  summary: "Summary",
  diagnostics: "Diagnostics",
  convergence_profile: "Convergence Profile",
  ionic_series: "Ionic Series",
  batch_summary: "Batch Summary",
  batch_diagnostics: "Batch Diagnostics",
  batch_insights: "Batch Insights",
  discover_runs: "Discover Runs",
  electronic_metadata: "Electronic Metadata",
  dos_profile: "DOS Profile",
  export_tabular: "Export Tabular",
  generate_relax_input: "Generate Relax Input",
};

const state = {
  activeView: "rendered",
  busy: false,
  busyButton: null,
};

class UiInputError extends Error {
  constructor(message) {
    super(message);
    this.name = "UiInputError";
  }
}

class UiApiError extends Error {
  constructor(payload, statusCode) {
    super(`Request failed with status ${statusCode}`);
    this.name = "UiApiError";
    this.payload = payload;
    this.statusCode = statusCode;
  }
}

bootstrap().catch((error) => {
  const normalized = normalizeError(error);
  renderError("initialization", normalized);
  setStatus(`Initialization failed: ${normalized.message}`, "error");
});

async function bootstrap() {
  bindEvents();
  restorePersistedState();
  setResultView("rendered");
  await loadConfig();
}

function bindEvents() {
  for (const tabButton of tabButtons) {
    tabButton.addEventListener("click", () => {
      activatePage(tabButton.dataset.pageTarget || "");
    });
  }

  viewRenderedButton.addEventListener("click", () => setResultView("rendered"));
  viewRawButton.addEventListener("click", () => setResultView("raw"));

  pickOutputDirButton.addEventListener("click", async () => {
    const picked = await tryPickFolder();
    if (!picked) {
      return;
    }
    outputDirInput.value = picked;
    safeStorageSet(STORAGE_KEYS.outputDir, picked);
  });

  pickBatchRootDirButton.addEventListener("click", async () => {
    const picked = await tryPickFolder();
    if (!picked) {
      return;
    }
    batchRootDirInput.value = picked;
    safeStorageSet(STORAGE_KEYS.batchRootDir, picked);
  });

  addBatchOutputDirButton.addEventListener("click", async () => {
    const picked = await tryPickFolder();
    if (!picked) {
      return;
    }

    const current = parseBatchDirectories(batchOutputDirsInput.value);
    if (!current.includes(picked)) {
      current.push(picked);
      batchOutputDirsInput.value = current.join("\n");
      safeStorageSet(STORAGE_KEYS.batchDirs, batchOutputDirsInput.value);
    }
  });

  clearBatchOutputDirsButton.addEventListener("click", () => {
    batchOutputDirsInput.value = "";
    safeStorageSet(STORAGE_KEYS.batchDirs, "");
  });

  outputDirInput.addEventListener("change", () => {
    safeStorageSet(STORAGE_KEYS.outputDir, outputDirInput.value.trim());
  });

  batchOutputDirsInput.addEventListener("change", () => {
    safeStorageSet(STORAGE_KEYS.batchDirs, batchOutputDirsInput.value);
  });

  batchRootDirInput.addEventListener("change", () => {
    safeStorageSet(STORAGE_KEYS.batchRootDir, batchRootDirInput.value.trim());
  });

  for (const button of actionButtons) {
    button.addEventListener("click", async () => {
      const action = button.dataset.action || "";
      await runAction(action, button);
    });
  }
}

function restorePersistedState() {
  const outputDir = safeStorageGet(STORAGE_KEYS.outputDir);
  if (outputDir) {
    outputDirInput.value = outputDir;
  }

  const batchDirs = safeStorageGet(STORAGE_KEYS.batchDirs);
  if (batchDirs) {
    batchOutputDirsInput.value = batchDirs;
  }

  const batchRootDir = safeStorageGet(STORAGE_KEYS.batchRootDir);
  if (batchRootDir) {
    batchRootDirInput.value = batchRootDir;
  }

  const activePage = safeStorageGet(STORAGE_KEYS.activePage);
  if (activePage && document.getElementById(activePage)) {
    activatePage(activePage);
  }
}

function activatePage(pageId) {
  if (!pageId) {
    return;
  }

  for (const page of taskPages) {
    const isActive = page.id === pageId;
    page.classList.toggle("active", isActive);
  }

  for (const tabButton of tabButtons) {
    const isActive = tabButton.dataset.pageTarget === pageId;
    tabButton.classList.toggle("active", isActive);
    tabButton.setAttribute("aria-selected", isActive ? "true" : "false");
  }

  safeStorageSet(STORAGE_KEYS.activePage, pageId);
}

function setResultView(view) {
  const resolved = view === "raw" ? "raw" : "rendered";
  state.activeView = resolved;

  const renderedActive = resolved === "rendered";
  resultRenderedEl.classList.toggle("hidden", !renderedActive);
  resultRawEl.classList.toggle("hidden", renderedActive);

  viewRenderedButton.classList.toggle("active", renderedActive);
  viewRawButton.classList.toggle("active", !renderedActive);
}

async function runAction(action, triggerButton) {
  if (!action) {
    return;
  }

  const label = ACTION_LABELS[action] || action;
  setBusy(true, triggerButton);
  setStatus(`Running ${label}...`, "running");

  try {
    const operation = buildOperationRequest(action);
    const response = await postJson(operation.endpoint, operation.payload);
    if (action === "discover_runs") {
      applyDiscoveredRunsToBatchList(response);
    }
    renderResult(action, response);
    setStatus(`${label} completed successfully.`, "success");
  } catch (error) {
    const normalized = normalizeError(error);
    renderError(action, normalized);
    setStatus(`${label} failed: ${normalized.message}`, "error");
  } finally {
    setBusy(false);
  }
}

function setBusy(isBusy, busyButton = null) {
  state.busy = isBusy;

  if (!isBusy && state.busyButton) {
    state.busyButton.classList.remove("is-loading");
    state.busyButton = null;
  }

  for (const button of actionButtons) {
    button.disabled = isBusy;
  }

  if (isBusy && busyButton) {
    state.busyButton = busyButton;
    state.busyButton.classList.add("is-loading");
  }
}

async function loadConfig() {
  try {
    const response = await fetch("/ui/config");
    const config = await readJsonSafely(response);

    if (!response.ok) {
      modeLabel.textContent = "Execution mode: unavailable";
      return;
    }

    modeLabel.textContent = `Execution mode: ${config.mode} | API base: ${config.api_base_url}`;
  } catch (_error) {
    modeLabel.textContent = "Execution mode: unavailable";
  }
}

function buildOperationRequest(action) {
  const outputDir = outputDirInput.value.trim();

  if (action === "run_report") {
    return {
      endpoint: "/ui/run-report",
      payload: {
        run_dir: resolveRunDirectory(outputDir),
        energy_tolerance_ev: readPositiveNumber(energyToleranceInput, "Energy tolerance"),
        force_tolerance_ev_per_a: readPositiveNumber(forceToleranceInput, "Force tolerance"),
        include_electronic: reportIncludeElectronicInput.checked,
      },
    };
  }

  if (action === "summary") {
    return {
      endpoint: "/ui/summary",
      payload: {
        outcar_path: resolvePrimaryFilePath(outputDir, "OUTCAR"),
        include_history: includeHistoryInput.checked,
      },
    };
  }

  if (action === "diagnostics") {
    return {
      endpoint: "/ui/diagnostics",
      payload: {
        outcar_path: resolvePrimaryFilePath(outputDir, "OUTCAR"),
        energy_tolerance_ev: readPositiveNumber(energyToleranceInput, "Energy tolerance"),
        force_tolerance_ev_per_a: readPositiveNumber(forceToleranceInput, "Force tolerance"),
      },
    };
  }

  if (action === "convergence_profile") {
    return {
      endpoint: "/ui/convergence-profile",
      payload: {
        outcar_path: resolvePrimaryFilePath(outputDir, "OUTCAR"),
      },
    };
  }

  if (action === "ionic_series") {
    return {
      endpoint: "/ui/ionic-series",
      payload: {
        outcar_path: resolvePrimaryFilePath(outputDir, "OUTCAR"),
      },
    };
  }

  if (action === "batch_summary") {
    const outcarPaths = parseBatchOutcarPaths(batchOutputDirsInput.value);
    return {
      endpoint: "/ui/batch-summary",
      payload: {
        outcar_paths: outcarPaths,
        fail_fast: batchFailFastInput.checked,
      },
    };
  }

  if (action === "discover_runs") {
    const rootDir = batchRootDirInput.value.trim();
    if (!rootDir) {
      throw new UiInputError("Batch root folder is required for discovery.");
    }
    return {
      endpoint: "/ui/discover-runs",
      payload: {
        root_dir: rootDir,
        recursive: batchRecursiveInput.checked,
        max_runs: readPositiveInteger(batchMaxRunsInput, "Max discovered runs"),
      },
    };
  }

  if (action === "batch_diagnostics") {
    const outcarPaths = parseBatchOutcarPaths(batchOutputDirsInput.value);
    return {
      endpoint: "/ui/batch-diagnostics",
      payload: {
        outcar_paths: outcarPaths,
        energy_tolerance_ev: readPositiveNumber(energyToleranceInput, "Energy tolerance"),
        force_tolerance_ev_per_a: readPositiveNumber(forceToleranceInput, "Force tolerance"),
        fail_fast: batchFailFastInput.checked,
      },
    };
  }

  if (action === "batch_insights") {
    const outcarPaths = parseBatchOutcarPaths(batchOutputDirsInput.value);
    return {
      endpoint: "/ui/batch-insights",
      payload: {
        outcar_paths: outcarPaths,
        energy_tolerance_ev: readPositiveNumber(energyToleranceInput, "Energy tolerance"),
        force_tolerance_ev_per_a: readPositiveNumber(forceToleranceInput, "Force tolerance"),
        top_n: readPositiveInteger(batchTopNInput, "Top ranked runs"),
        fail_fast: batchFailFastInput.checked,
      },
    };
  }

  if (action === "electronic_metadata") {
    if (!parseEigenvalInput.checked && !parseDoscarInput.checked) {
      throw new UiInputError("Select at least one source file: EIGENVAL or DOSCAR.");
    }

    return {
      endpoint: "/ui/electronic-metadata",
      payload: {
        eigenval_path: parseEigenvalInput.checked ? resolvePrimaryFilePath(outputDir, "EIGENVAL") : null,
        doscar_path: parseDoscarInput.checked ? resolvePrimaryFilePath(outputDir, "DOSCAR") : null,
      },
    };
  }

  if (action === "dos_profile") {
    return {
      endpoint: "/ui/dos-profile",
      payload: {
        doscar_path: resolvePrimaryFilePath(outputDir, "DOSCAR"),
        energy_window_ev: readPositiveNumber(dosWindowInput, "DOS window"),
        max_points: readPositiveInteger(dosMaxPointsInput, "Max DOS points"),
      },
    };
  }

  if (action === "export_tabular") {
    return {
      endpoint: "/ui/export-tabular",
      payload: {
        outcar_path: resolvePrimaryFilePath(outputDir, "OUTCAR"),
        dataset: exportDatasetInput.value,
        delimiter: normalizeDelimiter(exportDelimiterInput.value),
      },
    };
  }

  if (action === "generate_relax_input") {
    return {
      endpoint: "/ui/generate-relax-input",
      payload: {
        structure: parseStructureJson(structureJsonInput.value),
        kmesh: [
          readPositiveInteger(kmeshXInput, "KX"),
          readPositiveInteger(kmeshYInput, "KY"),
          readPositiveInteger(kmeshZInput, "KZ"),
        ],
        gamma_centered: gammaCenteredInput.checked,
      },
    };
  }

  throw new UiInputError(`Unsupported action: ${action}`);
}

function resolvePrimaryFilePath(outputDir, fileName) {
  const normalized = String(outputDir || "").trim();
  if (!normalized) {
    throw new UiInputError("Primary run folder is required.");
  }

  const isAlreadyFile = new RegExp(`(^|[\\\\/])${fileName}$`, "i").test(normalized);
  if (isAlreadyFile) {
    return normalized;
  }

  return joinPath(normalized, fileName);
}

function resolveRunDirectory(outputDir) {
  const normalized = String(outputDir || "").trim();
  if (!normalized) {
    throw new UiInputError("Primary run folder is required.");
  }

  if (/(^|[\\/])(OUTCAR|EIGENVAL|DOSCAR)$/i.test(normalized)) {
    return normalized.replace(/[\\/][^\\/]+$/, "");
  }

  return normalized;
}

function parseBatchOutcarPaths(raw) {
  const directories = parseBatchDirectories(raw);
  if (directories.length === 0) {
    throw new UiInputError("Add at least one VASP output folder for batch screening.");
  }

  return directories.map((token) => {
    const isOutcar = /(^|[\\/])OUTCAR$/i.test(token);
    return isOutcar ? token : joinPath(token, "OUTCAR");
  });
}

function parseBatchDirectories(raw) {
  return String(raw || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function applyDiscoveredRunsToBatchList(response) {
  if (!response || typeof response !== "object") {
    return;
  }

  const runDirs = Array.isArray(response.run_dirs)
    ? response.run_dirs
    : (Array.isArray(response.outcar_paths)
        ? response.outcar_paths.map((path) => String(path).replace(/[\\/]+OUTCAR$/i, ""))
        : []);

  const normalized = runDirs
    .map((token) => String(token || "").trim())
    .filter((token) => token.length > 0);

  batchOutputDirsInput.value = normalized.join("\n");
  safeStorageSet(STORAGE_KEYS.batchDirs, batchOutputDirsInput.value);
}

function parseStructureJson(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new UiInputError("Structure JSON must be an object payload.");
    }
    return parsed;
  } catch (error) {
    if (error instanceof UiInputError) {
      throw error;
    }
    throw new UiInputError(`Invalid structure JSON: ${String(error)}`);
  }
}

function readPositiveNumber(input, label) {
  const value = Number(String(input.value || "").trim());
  if (!Number.isFinite(value) || value <= 0) {
    throw new UiInputError(`${label} must be a positive number.`);
  }
  return value;
}

function readPositiveInteger(input, label) {
  const value = Number(String(input.value || "").trim());
  if (!Number.isInteger(value) || value <= 0) {
    throw new UiInputError(`${label} must be a positive integer.`);
  }
  return value;
}

function normalizeDelimiter(rawValue) {
  if (rawValue === "\\t") {
    return "\t";
  }
  return rawValue;
}

function joinPath(basePath, fileName) {
  const base = String(basePath || "").trim();
  if (!base) {
    return fileName;
  }
  if (base.endsWith("/") || base.endsWith("\\")) {
    return `${base}${fileName}`;
  }
  return `${base}/${fileName}`;
}

async function tryPickFolder() {
  try {
    const response = await fetch("/ui/pick-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });

    const payload = await readJsonSafely(response);
    if (!response.ok) {
      throw new UiApiError(payload, response.status);
    }

    if (!payload.selected || !payload.folder_path) {
      return null;
    }

    return payload.folder_path;
  } catch (error) {
    const normalized = normalizeError(error);
    renderError("folder_picker", normalized);
    setStatus(`Folder picker error: ${normalized.message}`, "error");
    return null;
  }
}

async function postJson(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await readJsonSafely(response);
  if (!response.ok) {
    throw new UiApiError(data, response.status);
  }

  return data;
}

async function readJsonSafely(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch (_error) {
    return { raw: text };
  }
}

function normalizeError(error) {
  if (error instanceof UiInputError) {
    return {
      code: "INPUT_ERROR",
      message: error.message,
      details: null,
    };
  }

  if (error instanceof UiApiError) {
    return parseApiErrorPayload(error.payload, error.statusCode);
  }

  if (error instanceof Error) {
    return {
      code: "UNEXPECTED_ERROR",
      message: error.message,
      details: null,
    };
  }

  return {
    code: "UNEXPECTED_ERROR",
    message: String(error),
    details: null,
  };
}

function parseApiErrorPayload(payload, statusCode) {
  const detail = payload && payload.detail !== undefined ? payload.detail : payload;

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    if (typeof detail.code === "string" || typeof detail.message === "string") {
      return {
        code: String(detail.code || `HTTP_${statusCode}`),
        message: String(detail.message || `HTTP ${statusCode}`),
        details: detail.details || null,
      };
    }
  }

  if (typeof detail === "string") {
    return {
      code: `HTTP_${statusCode}`,
      message: detail,
      details: null,
    };
  }

  return {
    code: `HTTP_${statusCode}`,
    message: `HTTP ${statusCode} request failed`,
    details: detail || null,
  };
}

function renderResult(action, payload) {
  resultRawEl.textContent = JSON.stringify(payload, null, 2);
  resultRenderedEl.replaceChildren(buildRenderedResult(action, payload));
  setResultView("rendered");
}

function renderError(action, error) {
  resultRawEl.textContent = JSON.stringify({ action, error }, null, 2);

  const panel = createElement("section", "result-section error");
  panel.appendChild(createElement("h3", "section-title", `${ACTION_LABELS[action] || action} failed`));

  const badges = createElement("div", "badge-row");
  badges.appendChild(createBadge(error.code || "ERROR", "danger"));
  panel.appendChild(badges);

  panel.appendChild(createElement("p", "error-text", error.message || "Unexpected error."));

  if (error.details) {
    panel.appendChild(createCodeBlock(JSON.stringify(error.details, null, 2)));
  }

  resultRenderedEl.replaceChildren(panel);
  setResultView("rendered");
}

function buildRenderedResult(action, payload) {
  if (action === "run_report") {
    return renderRunReport(payload);
  }

  if (action === "summary") {
    return renderSummary(payload);
  }

  if (action === "diagnostics") {
    return renderDiagnostics(payload);
  }

  if (action === "convergence_profile") {
    return renderConvergenceProfile(payload);
  }

  if (action === "ionic_series") {
    return renderIonicSeries(payload);
  }

  if (action === "batch_summary") {
    return renderBatchSummary(payload);
  }

  if (action === "discover_runs") {
    return renderDiscoverRuns(payload);
  }

  if (action === "batch_diagnostics") {
    return renderBatchDiagnostics(payload);
  }

  if (action === "batch_insights") {
    return renderBatchInsights(payload);
  }

  if (action === "electronic_metadata") {
    return renderElectronicMetadata(payload);
  }

  if (action === "dos_profile") {
    return renderDosProfile(payload);
  }

  if (action === "export_tabular") {
    return renderExportTabular(payload);
  }

  if (action === "generate_relax_input") {
    return renderGeneratedInput(payload);
  }

  return renderGenericPayload(payload);
}

function renderRunReport(data) {
  const stack = createElement("div", "result-stack");

  const overview = createSection("Run Report", data.run_dir || "");
  overview.appendChild(
    createMetricGrid([
      { label: "Status", value: data.recommended_status },
      { label: "Converged", value: data.is_converged },
      { label: "OUTCAR", value: data.outcar_path || "-" },
      { label: "EIGENVAL", value: data.eigenval_path || "not found" },
      { label: "DOSCAR", value: data.doscar_path || "not found" },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  const actions = Array.isArray(data.suggested_actions) ? data.suggested_actions : [];
  if (actions.length > 0) {
    const actionSection = createSection("Suggested Actions");
    const list = createElement("ul", "warning-list");
    for (const action of actions) {
      list.appendChild(createElement("li", "", String(action)));
    }
    actionSection.appendChild(list);
    stack.appendChild(actionSection);
  }

  if (data.summary) {
    stack.appendChild(renderSummary(data.summary));
  }

  if (data.diagnostics) {
    stack.appendChild(renderDiagnostics(data.diagnostics));
  }

  if (data.electronic_metadata) {
    stack.appendChild(renderElectronicMetadata(data.electronic_metadata));
  }

  return stack;
}

function renderSummary(data) {
  const stack = createElement("div", "result-stack");

  const summary = createSection("Run Summary", data.source_path || "");
  summary.appendChild(
    createMetricGrid([
      { label: "System", value: data.system_name },
      { label: "Ionic Steps", value: data.ionic_steps },
      { label: "Electronic Iterations", value: data.electronic_iterations },
      { label: "Final Total Energy (eV)", value: data.final_total_energy_ev },
      { label: "Final Fermi Energy (eV)", value: data.final_fermi_energy_ev },
      { label: "Max Force (eV/Ang)", value: data.max_force_ev_per_a },
    ])
  );
  appendWarnings(summary, data.warnings);
  stack.appendChild(summary);

  const historyValues = Array.isArray(data.energy_history) ? data.energy_history : [];
  if (historyValues.length > 0) {
    const history = createSection("Energy History", "Full TOTEN history from ionic optimization steps.");
    const rows = historyValues.map((energy, index) => {
      const previous = index > 0 ? historyValues[index - 1] : null;
      return {
        step: index + 1,
        total_energy_ev: energy,
        delta_energy_ev: previous === null ? null : energy - previous,
      };
    });

    history.appendChild(
      createTable(
        [
          { label: "Step", value: (row) => row.step },
          { label: "Total Energy (eV)", value: (row) => formatValue(row.total_energy_ev) },
          { label: "Delta Energy (eV)", value: (row) => formatValue(row.delta_energy_ev) },
        ],
        rows
      )
    );
    stack.appendChild(history);
  }

  return stack;
}

function renderDiagnostics(data) {
  const stack = createElement("div", "result-stack");

  const overview = createSection("Diagnostics Overview", data.source_path || "");
  overview.appendChild(
    createMetricGrid([
      { label: "System", value: data.system_name },
      { label: "Final Total Energy (eV)", value: data.final_total_energy_ev },
      { label: "Max Force (eV/Ang)", value: data.max_force_ev_per_a },
      { label: "External Pressure (kB)", value: data.external_pressure_kb },
      { label: "Final Fermi Energy (eV)", value: data.final_fermi_energy_ev },
      { label: "Ionic Steps", value: data.ionic_steps },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  const convergence = data.convergence || {};
  const convergenceSection = createSection("Convergence", "Energy and force checks against configured tolerances.");
  const badges = createElement("div", "badge-row");
  badges.appendChild(createBadge(convergence.is_converged ? "Converged" : "Not converged", convergence.is_converged ? "success" : "danger"));
  badges.appendChild(createBadge(convergence.is_energy_converged ? "Energy OK" : "Energy not converged", convergence.is_energy_converged ? "success" : "warn"));
  badges.appendChild(createBadge(convergence.is_force_converged ? "Force OK" : "Force not converged", convergence.is_force_converged ? "success" : "warn"));
  convergenceSection.appendChild(badges);
  convergenceSection.appendChild(
    createMetricGrid([
      { label: "Energy Tolerance (eV)", value: convergence.energy_tolerance_ev },
      { label: "Force Tolerance (eV/Ang)", value: convergence.force_tolerance_ev_per_a },
      { label: "Final Energy Change (eV)", value: convergence.final_energy_change_ev },
    ])
  );
  stack.appendChild(convergenceSection);

  if (data.stress_tensor_kb) {
    const stress = createSection("Stress Tensor (kB)");
    const stressRows = [
      {
        component: "X",
        xx: data.stress_tensor_kb.xx_kb,
        xy: data.stress_tensor_kb.xy_kb,
        xz: data.stress_tensor_kb.zx_kb,
      },
      {
        component: "Y",
        xx: data.stress_tensor_kb.xy_kb,
        xy: data.stress_tensor_kb.yy_kb,
        xz: data.stress_tensor_kb.yz_kb,
      },
      {
        component: "Z",
        xx: data.stress_tensor_kb.zx_kb,
        xy: data.stress_tensor_kb.yz_kb,
        xz: data.stress_tensor_kb.zz_kb,
      },
    ];

    stress.appendChild(
      createTable(
        [
          { label: "Axis", value: (row) => row.component },
          { label: "X", value: (row) => formatValue(row.xx) },
          { label: "Y", value: (row) => formatValue(row.xy) },
          { label: "Z", value: (row) => formatValue(row.xz) },
        ],
        stressRows
      )
    );
    stack.appendChild(stress);
  }

  if (data.magnetization) {
    const mag = createSection("Magnetization");
    mag.appendChild(
      createMetricGrid([
        { label: "Axis", value: data.magnetization.axis },
        { label: "Total Moment (mu_B)", value: data.magnetization.total_moment_mu_b },
      ])
    );

    const siteMoments = Array.isArray(data.magnetization.site_moments_mu_b) ? data.magnetization.site_moments_mu_b : [];
    if (siteMoments.length > 0) {
      const rows = siteMoments.map((moment, index) => ({
        site: index + 1,
        moment,
      }));
      mag.appendChild(
        createTable(
          [
            { label: "Site", value: (row) => row.site },
            { label: "Moment (mu_B)", value: (row) => formatValue(row.moment) },
          ],
          rows
        )
      );
    }

    stack.appendChild(mag);
  }

  return stack;
}

function renderConvergenceProfile(data) {
  const stack = createElement("div", "result-stack");
  const points = Array.isArray(data.points) ? data.points : [];

  const overview = createSection("Convergence Profile", data.source_path || "");
  overview.appendChild(
    createMetricGrid([
      { label: "Points", value: points.length },
      { label: "Final Total Energy (eV)", value: data.final_total_energy_ev },
      { label: "Max Force (eV/Ang)", value: data.max_force_ev_per_a },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  if (points.length > 0) {
    const tableSection = createSection("Point Table", "Use this view to inspect energy evolution by ionic step.");
    tableSection.appendChild(
      createTable(
        [
          { label: "Step", value: (row) => row.ionic_step },
          { label: "Total Energy (eV)", value: (row) => formatValue(row.total_energy_ev) },
          { label: "Delta Energy (eV)", value: (row) => formatValue(row.delta_energy_ev) },
          { label: "Relative Energy (eV)", value: (row) => formatValue(row.relative_energy_ev) },
        ],
        points
      )
    );
    stack.appendChild(tableSection);

    const bars = createSeriesBars(points, "relative_energy_ev", "Relative energy trend (lower is better)", true);
    if (bars) {
      stack.appendChild(bars);
    }
  }

  return stack;
}

function renderIonicSeries(data) {
  const stack = createElement("div", "result-stack");
  const points = Array.isArray(data.points) ? data.points : [];

  const overview = createSection("Ionic Series", data.source_path || "");
  overview.appendChild(
    createMetricGrid([
      { label: "Steps", value: data.n_steps },
      { label: "First Energy (eV)", value: points[0] ? points[0].total_energy_ev : null },
      { label: "Final Energy (eV)", value: points.length ? points[points.length - 1].total_energy_ev : null },
      { label: "Final Pressure (kB)", value: points.length ? points[points.length - 1].external_pressure_kb : null },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  if (points.length > 0) {
    const tableSection = createSection("Point Table");
    tableSection.appendChild(
      createTable(
        [
          { label: "Step", value: (row) => row.ionic_step },
          { label: "Total Energy (eV)", value: (row) => formatValue(row.total_energy_ev) },
          { label: "Delta Energy (eV)", value: (row) => formatValue(row.delta_energy_ev) },
          { label: "Max Force (eV/Ang)", value: (row) => formatValue(row.max_force_ev_per_a) },
          { label: "Pressure (kB)", value: (row) => formatValue(row.external_pressure_kb) },
          { label: "Fermi (eV)", value: (row) => formatValue(row.fermi_energy_ev) },
        ],
        points
      )
    );
    stack.appendChild(tableSection);

    const forceBars = createSeriesBars(points, "max_force_ev_per_a", "Max force trend (lower is better)", true);
    if (forceBars) {
      stack.appendChild(forceBars);
    }
  }

  return stack;
}

function renderBatchSummary(data) {
  const stack = createElement("div", "result-stack");
  const rows = Array.isArray(data.rows) ? data.rows : [];

  const overview = createSection("Batch Summary", "Multi-run status and key scalar outputs.");
  overview.appendChild(
    createMetricGrid([
      { label: "Total", value: data.total_count },
      { label: "Succeeded", value: data.success_count },
      { label: "Failed", value: data.error_count },
    ])
  );
  stack.appendChild(overview);

  if (rows.length > 0) {
    const tableSection = createSection("Batch Rows");
    tableSection.appendChild(
      createTable(
        [
          {
            label: "Status",
            value: (row) => createBadge(row.status === "ok" ? "OK" : "Error", row.status === "ok" ? "success" : "danger"),
          },
          { label: "Run", value: (row) => row.outcar_path },
          { label: "System", value: (row) => row.system_name || "-" },
          { label: "Final Energy (eV)", value: (row) => formatValue(row.final_total_energy_ev) },
          { label: "Max Force", value: (row) => formatValue(row.max_force_ev_per_a) },
          { label: "Error", value: (row) => (row.error && row.error.code ? row.error.code : "-") },
        ],
        rows
      )
    );
    stack.appendChild(tableSection);
  }

  return stack;
}

function renderDiscoverRuns(data) {
  const stack = createElement("div", "result-stack");
  const runDirs = Array.isArray(data.run_dirs) ? data.run_dirs : [];
  const outcarPaths = Array.isArray(data.outcar_paths) ? data.outcar_paths : [];

  const overview = createSection("Run Discovery", data.root_dir || "");
  overview.appendChild(
    createMetricGrid([
      { label: "Recursive", value: data.recursive ? "Yes" : "No" },
      { label: "Max Returned", value: data.max_runs },
      { label: "Total Discovered", value: data.total_discovered },
      { label: "Returned", value: data.returned_count },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  if (outcarPaths.length > 0) {
    const tableSection = createSection("Discovered Runs", "These folders are now loaded in Batch Output Folders.");
    const rows = outcarPaths.map((outcarPath, index) => ({
      idx: index + 1,
      run_dir: runDirs[index] || outcarPath,
      outcar_path: outcarPath,
    }));
    tableSection.appendChild(
      createTable(
        [
          { label: "#", value: (row) => row.idx },
          { label: "Run Directory", value: (row) => row.run_dir },
          { label: "OUTCAR Path", value: (row) => row.outcar_path },
        ],
        rows
      )
    );
    stack.appendChild(tableSection);
  } else {
    stack.appendChild(createSection("No Runs Found", "No OUTCAR files were discovered with current settings."));
  }

  return stack;
}

function renderBatchDiagnostics(data) {
  const stack = createElement("div", "result-stack");
  const rows = Array.isArray(data.rows) ? data.rows : [];

  const overview = createSection("Batch Diagnostics", "Convergence and stress outcomes across multiple runs.");
  overview.appendChild(
    createMetricGrid([
      { label: "Total", value: data.total_count },
      { label: "Succeeded", value: data.success_count },
      { label: "Failed", value: data.error_count },
    ])
  );
  stack.appendChild(overview);

  if (rows.length > 0) {
    const tableSection = createSection("Batch Rows");
    tableSection.appendChild(
      createTable(
        [
          {
            label: "Status",
            value: (row) => createBadge(row.status === "ok" ? "OK" : "Error", row.status === "ok" ? "success" : "danger"),
          },
          { label: "Run", value: (row) => row.outcar_path },
          { label: "Final Energy (eV)", value: (row) => formatValue(row.final_total_energy_ev) },
          { label: "Max Force", value: (row) => formatValue(row.max_force_ev_per_a) },
          { label: "Pressure (kB)", value: (row) => formatValue(row.external_pressure_kb) },
          {
            label: "Converged",
            value: (row) => {
              if (row.is_converged === null || row.is_converged === undefined) {
                return "-";
              }
              return row.is_converged ? "Yes" : "No";
            },
          },
          { label: "Error", value: (row) => (row.error && row.error.code ? row.error.code : "-") },
        ],
        rows
      )
    );
    stack.appendChild(tableSection);
  }

  return stack;
}

function renderBatchInsights(data) {
  const stack = createElement("div", "result-stack");
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const topRows = Array.isArray(data.top_lowest_energy) ? data.top_lowest_energy : [];

  const overview = createSection("Batch Insights", "Aggregate screening metrics with low-energy ranking.");
  overview.appendChild(
    createMetricGrid([
      { label: "Total", value: data.total_count },
      { label: "Succeeded", value: data.success_count },
      { label: "Failed", value: data.error_count },
      { label: "Converged", value: data.converged_count },
      { label: "Not Converged", value: data.not_converged_count },
      { label: "Unknown Convergence", value: data.unknown_convergence_count },
      { label: "Min Energy (eV)", value: data.energy_min_ev },
      { label: "Max Energy (eV)", value: data.energy_max_ev },
      { label: "Mean Energy (eV)", value: data.energy_mean_ev },
      { label: "Energy Span (eV)", value: data.energy_span_ev },
      { label: "Mean Max Force (eV/Ang)", value: data.mean_max_force_ev_per_a },
    ])
  );
  stack.appendChild(overview);

  if (topRows.length > 0) {
    const ranking = createSection("Top Lowest-Energy Runs");
    ranking.appendChild(
      createTable(
        [
          { label: "Rank", value: (row) => row.rank },
          { label: "Run", value: (row) => row.outcar_path },
          { label: "System", value: (row) => row.system_name || "-" },
          { label: "Final Energy (eV)", value: (row) => formatValue(row.final_total_energy_ev) },
          { label: "Max Force", value: (row) => formatValue(row.max_force_ev_per_a) },
          {
            label: "Converged",
            value: (row) => {
              if (row.is_converged === null || row.is_converged === undefined) {
                return "-";
              }
              return row.is_converged ? "Yes" : "No";
            },
          },
        ],
        topRows
      )
    );
    stack.appendChild(ranking);
  }

  if (rows.length > 0) {
    const detail = createSection("Per-Run Detail");
    detail.appendChild(
      createTable(
        [
          {
            label: "Status",
            value: (row) => createBadge(row.status === "ok" ? "OK" : "Error", row.status === "ok" ? "success" : "danger"),
          },
          { label: "Run", value: (row) => row.outcar_path },
          { label: "System", value: (row) => row.system_name || "-" },
          { label: "Final Energy (eV)", value: (row) => formatValue(row.final_total_energy_ev) },
          { label: "Max Force", value: (row) => formatValue(row.max_force_ev_per_a) },
          { label: "Pressure (kB)", value: (row) => formatValue(row.external_pressure_kb) },
          {
            label: "Converged",
            value: (row) => {
              if (row.is_converged === null || row.is_converged === undefined) {
                return "-";
              }
              return row.is_converged ? "Yes" : "No";
            },
          },
          { label: "Error", value: (row) => (row.error && row.error.code ? row.error.code : "-") },
        ],
        rows
      )
    );
    stack.appendChild(detail);
  }

  return stack;
}

function renderElectronicMetadata(data) {
  const stack = createElement("div", "result-stack");

  const files = createSection("Parsed Files");
  files.appendChild(
    createKeyValueList([
      ["EIGENVAL", data.eigenval_path || "not requested"],
      ["DOSCAR", data.doscar_path || "not requested"],
    ])
  );
  appendWarnings(files, data.warnings);
  stack.appendChild(files);

  if (data.band_gap) {
    const band = createSection("Band Gap Summary", "VASPKIT-like gap metadata from EIGENVAL.");
    band.appendChild(
      createMetricGrid([
        { label: "Metallic", value: data.band_gap.is_metal ? "Yes" : "No" },
        { label: "Fundamental Gap (eV)", value: data.band_gap.fundamental_gap_ev },
        { label: "VBM (eV)", value: data.band_gap.vbm_ev },
        { label: "CBM (eV)", value: data.band_gap.cbm_ev },
        { label: "Direct Gap", value: data.band_gap.is_direct ? "Yes" : "No" },
        { label: "Spin Polarized", value: data.band_gap.is_spin_polarized ? "Yes" : "No" },
      ])
    );

    if (Array.isArray(data.band_gap.channels) && data.band_gap.channels.length > 0) {
      band.appendChild(
        createTable(
          [
            { label: "Spin", value: (row) => row.spin },
            { label: "Gap (eV)", value: (row) => formatValue(row.gap_ev) },
            { label: "VBM", value: (row) => formatValue(row.vbm_ev) },
            { label: "CBM", value: (row) => formatValue(row.cbm_ev) },
            { label: "Direct", value: (row) => (row.is_direct ? "Yes" : "No") },
            { label: "Metal", value: (row) => (row.is_metal ? "Yes" : "No") },
          ],
          data.band_gap.channels
        )
      );
    }

    stack.appendChild(band);
  }

  if (data.dos_metadata) {
    const dos = createSection("DOS Metadata", "DOSCAR header and Fermi-level metadata.");
    dos.appendChild(
      createMetricGrid([
        { label: "Energy Min (eV)", value: data.dos_metadata.energy_min_ev },
        { label: "Energy Max (eV)", value: data.dos_metadata.energy_max_ev },
        { label: "NEDOS", value: data.dos_metadata.nedos },
        { label: "Efermi (eV)", value: data.dos_metadata.efermi_ev },
        { label: "Spin Polarized", value: data.dos_metadata.is_spin_polarized ? "Yes" : "No" },
        { label: "Integrated DOS", value: data.dos_metadata.has_integrated_dos ? "Yes" : "No" },
        { label: "Energy Step (eV)", value: data.dos_metadata.energy_step_ev },
        { label: "DOS at Efermi", value: data.dos_metadata.total_dos_at_fermi },
      ])
    );
    stack.appendChild(dos);
  }

  if (!data.band_gap && !data.dos_metadata) {
    const empty = createSection("No Metadata", "No electronic metadata was returned for the selected sources.");
    stack.appendChild(empty);
  }

  return stack;
}

function renderDosProfile(data) {
  const stack = createElement("div", "result-stack");
  const points = Array.isArray(data.points) ? data.points : [];

  const overview = createSection("DOS Profile", data.source_path || "");
  overview.appendChild(
    createMetricGrid([
      { label: "Efermi (eV)", value: data.efermi_ev },
      { label: "Window (eV)", value: data.energy_window_ev },
      { label: "Points", value: data.n_points },
      { label: "Min Relative Energy (eV)", value: points.length ? points[0].energy_relative_ev : null },
      {
        label: "Max Relative Energy (eV)",
        value: points.length ? points[points.length - 1].energy_relative_ev : null,
      },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  if (points.length > 0) {
    const chartSection = createSection("DOS Curve", "Total DOS versus relative energy around E-fermi.");
    chartSection.appendChild(createLineChart(points));
    stack.appendChild(chartSection);

    const tableSection = createSection("Point Table", "First 250 sampled points are shown for table readability.");
    tableSection.appendChild(
      createTable(
        [
          { label: "#", value: (row) => row.index },
          { label: "Energy (eV)", value: (row) => formatValue(row.energy_ev) },
          { label: "Relative Energy (eV)", value: (row) => formatValue(row.energy_relative_ev) },
          { label: "Total DOS", value: (row) => formatValue(row.dos_total) },
        ],
        points.slice(0, 250)
      )
    );
    stack.appendChild(tableSection);
  } else {
    stack.appendChild(createSection("No Points", "No DOS points were returned for the requested settings."));
  }

  return stack;
}

function renderExportTabular(data) {
  const stack = createElement("div", "result-stack");

  const overview = createSection("Tabular Export", data.source_path || "");
  overview.appendChild(
    createMetricGrid([
      { label: "Dataset", value: data.dataset },
      { label: "Format", value: data.format },
      { label: "Rows", value: data.n_rows },
      { label: "Delimiter", value: humanizeDelimiter(data.delimiter) },
      { label: "Suggested File", value: data.filename_hint },
    ])
  );
  appendWarnings(overview, data.warnings);

  const actions = createElement("div", "inline-actions");
  const copyButton = createElement("button", "secondary", "Copy CSV");
  copyButton.type = "button";
  copyButton.addEventListener("click", async () => {
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(String(data.content || ""));
      setStatus("CSV copied to clipboard.", "success");
    } catch (_error) {
      setStatus("Clipboard copy failed. Use Raw JSON view for manual copy.", "warn");
    }
  });

  const downloadLink = createElement("a", "button-link", "Download CSV");
  const blob = new Blob([String(data.content || "")], { type: "text/csv;charset=utf-8" });
  const blobUrl = URL.createObjectURL(blob);
  downloadLink.href = blobUrl;
  downloadLink.download = String(data.filename_hint || "pyvasp_export.csv");
  downloadLink.addEventListener(
    "click",
    () => {
      setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
    },
    { once: true }
  );

  actions.appendChild(copyButton);
  actions.appendChild(downloadLink);
  overview.appendChild(actions);
  stack.appendChild(overview);

  const preview = createSection("Preview", "First lines of exported CSV content.");
  const lines = String(data.content || "")
    .split(/\r?\n/)
    .slice(0, 18)
    .join("\n");
  preview.appendChild(createCodeBlock(lines || "No rows exported."));
  stack.appendChild(preview);

  return stack;
}

function renderGeneratedInput(data) {
  const stack = createElement("div", "result-stack");

  const overview = createSection("Generated Input Bundle");
  overview.appendChild(
    createMetricGrid([
      { label: "System", value: data.system_name },
      { label: "Atoms", value: data.n_atoms },
    ])
  );
  appendWarnings(overview, data.warnings);
  stack.appendChild(overview);

  stack.appendChild(createCodePanel("INCAR", data.incar_text));
  stack.appendChild(createCodePanel("KPOINTS", data.kpoints_text));
  stack.appendChild(createCodePanel("POSCAR", data.poscar_text));

  return stack;
}

function renderGenericPayload(payload) {
  const section = createSection("Result", "No custom renderer for this payload yet.");
  section.appendChild(createCodeBlock(JSON.stringify(payload, null, 2)));
  return section;
}

function createSection(title, subtitle = "") {
  const section = createElement("section", "result-section");
  if (title) {
    section.appendChild(createElement("h3", "section-title", title));
  }
  if (subtitle) {
    section.appendChild(createElement("p", "muted section-subtitle", subtitle));
  }
  return section;
}

function createMetricGrid(items) {
  const grid = createElement("div", "metrics-grid");

  for (const item of items) {
    const card = createElement("article", "metric-card");
    card.appendChild(createElement("span", "metric-label", item.label));
    card.appendChild(createElement("strong", "metric-value", formatValue(item.value)));
    grid.appendChild(card);
  }

  return grid;
}

function createTable(columns, rows) {
  const wrapper = createElement("div", "table-wrap");
  const table = createElement("table", "data-table");

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const column of columns) {
    const th = document.createElement("th");
    th.textContent = column.label;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const column of columns) {
      const td = document.createElement("td");
      const rawValue = column.value(row);

      if (rawValue instanceof Node) {
        td.appendChild(rawValue);
      } else {
        td.textContent = String(rawValue);
      }

      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }

  table.appendChild(tbody);
  wrapper.appendChild(table);
  return wrapper;
}

function createSeriesBars(points, field, title, lowerIsBetter = false) {
  const numericPoints = points
    .map((point) => ({
      step: point.ionic_step,
      value: point[field],
    }))
    .filter((item) => typeof item.value === "number" && Number.isFinite(item.value));

  if (numericPoints.length === 0) {
    return null;
  }

  const values = numericPoints.map((item) => item.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const span = maxValue - minValue || 1;

  const section = createSection(title);
  const bars = createElement("div", "series-bars");

  for (const point of numericPoints) {
    const row = createElement("div", "series-row");
    row.appendChild(createElement("span", "series-step", `Step ${point.step}`));
    row.appendChild(createElement("span", "series-value", formatValue(point.value)));

    const track = createElement("div", "series-track");
    const fill = createElement("div", "series-fill");
    const normalized = (point.value - minValue) / span;
    const score = lowerIsBetter ? 1 - normalized : normalized;
    fill.style.width = `${Math.max(0, Math.min(1, score)) * 100}%`;
    track.appendChild(fill);
    row.appendChild(track);

    bars.appendChild(row);
  }

  section.appendChild(bars);
  return section;
}

function createLineChart(points) {
  const values = points.filter(
    (point) =>
      typeof point.energy_relative_ev === "number" &&
      Number.isFinite(point.energy_relative_ev) &&
      typeof point.dos_total === "number" &&
      Number.isFinite(point.dos_total)
  );

  if (values.length < 2) {
    return createElement("p", "muted", "Not enough points to draw DOS curve.");
  }

  const width = 760;
  const height = 260;
  const padX = 40;
  const padY = 22;

  const minX = Math.min(...values.map((point) => point.energy_relative_ev));
  const maxX = Math.max(...values.map((point) => point.energy_relative_ev));
  const minY = Math.min(...values.map((point) => point.dos_total));
  const maxY = Math.max(...values.map((point) => point.dos_total));

  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;

  const polylinePoints = values
    .map((point) => {
      const x = padX + ((point.energy_relative_ev - minX) / spanX) * (width - 2 * padX);
      const y = height - padY - ((point.dos_total - minY) / spanY) * (height - 2 * padY);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  const xZero = padX + ((0 - minX) / spanX) * (width - 2 * padX);
  const yZero = height - padY - ((0 - minY) / spanY) * (height - 2 * padY);

  const svg = createSvgElement("svg", "line-chart");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "DOS profile line chart");

  const background = createSvgElement("rect", "line-chart-bg");
  background.setAttribute("x", "0");
  background.setAttribute("y", "0");
  background.setAttribute("width", String(width));
  background.setAttribute("height", String(height));
  svg.appendChild(background);

  const axisX = createSvgElement("line", "line-chart-axis");
  axisX.setAttribute("x1", String(padX));
  axisX.setAttribute("y1", String(height - padY));
  axisX.setAttribute("x2", String(width - padX));
  axisX.setAttribute("y2", String(height - padY));
  svg.appendChild(axisX);

  const axisY = createSvgElement("line", "line-chart-axis");
  axisY.setAttribute("x1", String(padX));
  axisY.setAttribute("y1", String(padY));
  axisY.setAttribute("x2", String(padX));
  axisY.setAttribute("y2", String(height - padY));
  svg.appendChild(axisY);

  if (xZero >= padX && xZero <= width - padX) {
    const vRef = createSvgElement("line", "line-chart-ref");
    vRef.setAttribute("x1", xZero.toFixed(2));
    vRef.setAttribute("y1", String(padY));
    vRef.setAttribute("x2", xZero.toFixed(2));
    vRef.setAttribute("y2", String(height - padY));
    svg.appendChild(vRef);
  }

  if (yZero >= padY && yZero <= height - padY) {
    const hRef = createSvgElement("line", "line-chart-ref");
    hRef.setAttribute("x1", String(padX));
    hRef.setAttribute("y1", yZero.toFixed(2));
    hRef.setAttribute("x2", String(width - padX));
    hRef.setAttribute("y2", yZero.toFixed(2));
    svg.appendChild(hRef);
  }

  const line = createSvgElement("polyline", "line-chart-path");
  line.setAttribute("points", polylinePoints);
  svg.appendChild(line);

  const labels = createElement("div", "line-chart-labels");
  labels.appendChild(
    createElement("span", "muted", `${formatValue(minX)} eV  ..  ${formatValue(maxX)} eV (relative energy)`)
  );
  labels.appendChild(createElement("span", "muted", `DOS range: ${formatValue(minY)} .. ${formatValue(maxY)}`));

  const wrapper = createElement("div", "line-chart-wrap");
  wrapper.appendChild(svg);
  wrapper.appendChild(labels);
  return wrapper;
}

function createKeyValueList(entries) {
  const list = createElement("dl", "kv-list");

  for (const [key, value] of entries) {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = String(value);
    list.appendChild(dt);
    list.appendChild(dd);
  }

  return list;
}

function createBadge(text, tone) {
  const badge = createElement("span", `badge ${tone || "neutral"}`, text);
  return badge;
}

function createCodePanel(title, text) {
  const section = createSection(title);

  const actions = createElement("div", "inline-actions");
  const copyButton = createElement("button", "secondary", "Copy");
  copyButton.type = "button";
  copyButton.addEventListener("click", async () => {
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(String(text || ""));
      setStatus(`${title} copied to clipboard.`, "success");
    } catch (_error) {
      setStatus(`Unable to copy ${title}.`, "warn");
    }
  });
  actions.appendChild(copyButton);
  section.appendChild(actions);

  section.appendChild(createCodeBlock(text));
  return section;
}

function createCodeBlock(text) {
  const pre = createElement("pre", "code-block");
  pre.textContent = String(text || "");
  return pre;
}

function appendWarnings(container, warnings) {
  if (!Array.isArray(warnings) || warnings.length === 0) {
    return;
  }

  const section = createElement("section", "warning-block");
  section.appendChild(createElement("h4", "warning-title", "Warnings"));

  const list = createElement("ul", "warning-list");
  for (const warning of warnings) {
    list.appendChild(createElement("li", "", String(warning)));
  }

  section.appendChild(list);
  container.appendChild(section);
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return String(value);
    }

    if (Number.isInteger(value)) {
      return String(value);
    }

    const abs = Math.abs(value);
    if ((abs > 0 && abs < 1e-4) || abs >= 1e4) {
      return value.toExponential(3);
    }

    return String(Number(value.toFixed(6)));
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}

function humanizeDelimiter(delimiter) {
  if (delimiter === "\t") {
    return "Tab";
  }
  if (delimiter === ",") {
    return "Comma";
  }
  if (delimiter === ";") {
    return "Semicolon";
  }
  return String(delimiter);
}

function setStatus(message, tone = "neutral") {
  resultStatusEl.textContent = message;
  resultStatusEl.dataset.state = tone;
}

function createElement(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text) {
    element.textContent = text;
  }
  return element;
}

function createSvgElement(tag, className = "") {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  if (className) {
    element.setAttribute("class", className);
  }
  return element;
}

function safeStorageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch (_error) {
    return null;
  }
}

function safeStorageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (_error) {
    // Ignore storage write failures in restricted browser contexts.
  }
}
