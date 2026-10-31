(() => {
  "use strict";

  // FastAPI backend address
  const API_BASE_URL = "http://127.0.0.1:8000";

  let allClaims = [];
  let toastTimer;

  const $ = (id) => document.getElementById(id);

  const els = {
    apiStatusDot: $("apiStatusDot"),
    apiStatusText: $("apiStatusText"),
    totalClaims: $("totalClaims"),
    underReviewClaims: $("underReviewClaims"),
    approvedClaims: $("approvedClaims"),
    totalAmount: $("totalAmount"),
    claimsBody: $("claimsBody"),
    searchInput: $("searchInput"),
    statusFilter: $("statusFilter"),
    emptyState: $("emptyState"),
    resultsCount: $("resultsCount"),
    refreshButton: $("refreshButton"),
    topRegisterButton: $("topRegisterButton"),
    claimForm: $("claimForm"),
    formMessage: $("formMessage"),
    submitClaimButton: $("submitClaimButton"),
    aiClaimSelect: $("aiClaimSelect"),
    riskButton: $("riskButton"),
    summaryButton: $("summaryButton"),
    aiResult: $("aiResult"),
    claimDialog: $("claimDialog"),
    dialogTitle: $("dialogTitle"),
    claimDetails: $("claimDetails"),
    closeDialogButton: $("closeDialogButton"),
    toast: $("toast")
  };

  // Escape text before inserting it into HTML.
  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[char]));
  }

  // Format amounts as Indian rupees.
  function formatMoney(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "—";
    }

    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2
    }).format(number);
  }

  // Format dates for display.
  function formatDate(value) {
    if (!value) return "—";

    const date = new Date(`${String(value).slice(0, 10)}T00:00:00`);

    if (Number.isNaN(date.getTime())) {
      return String(value);
    }

    return date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  }

  function normalizedStatus(status) {
    return String(status || "Unknown").trim();
  }

  function statusClass(status) {
    const key = normalizedStatus(status)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-");

    const allowed = [
      "under-review",
      "survey-assigned",
      "approved",
      "settled",
      "registered",
      "rejected"
    ];

    return allowed.includes(key)
      ? `status-${key}`
      : "status-default";
  }

  function getClaimId(claim) {
    return claim.claim_id ?? claim.id ?? "";
  }

  // Show whether the backend is connected.
  function setApiStatus(connected, message) {
    els.apiStatusDot.classList.toggle("connected", connected);
    els.apiStatusDot.classList.toggle("disconnected", !connected);
    els.apiStatusText.textContent = message;
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
      els.toast.classList.remove("show");
    }, 3600);
  }

  // Common function for all backend API requests.
  async function apiRequest(path, options = {}) {
    let response;

    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: {
          ...(options.body
            ? { "Content-Type": "application/json" }
            : {}),
          ...(options.headers || {})
        }
      });
    } catch (error) {
      throw new Error(
        `Cannot connect to ${API_BASE_URL}. Start your FastAPI backend and try again.`
      );
    }

    const responseText = await response.text();
    let data = {};

    if (responseText) {
      try {
        data = JSON.parse(responseText);
      } catch {
        data = { detail: responseText };
      }
    }

    if (!response.ok) {
      let detail = "Request failed.";

      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data.detail)) {
        detail = data.detail
          .map(item => item.msg || JSON.stringify(item))
          .join("; ");
      } else if (data.message) {
        detail = data.message;
      } else {
        detail = `Request failed (${response.status}).`;
      }

      throw new Error(detail);
    }

    return data;
  }

  // Update dashboard summary cards.
  function updateStats() {
    const underReview = allClaims.filter(claim =>
      normalizedStatus(claim.claim_status).toLowerCase() === "under review"
    ).length;

    const approved = allClaims.filter(claim =>
      ["approved", "settled"].includes(
        normalizedStatus(claim.claim_status).toLowerCase()
      )
    ).length;

    const totalAmount = allClaims.reduce((sum, claim) => {
      return sum + (Number(claim.claim_amount) || 0);
    }, 0);

    els.totalClaims.textContent =
      allClaims.length.toLocaleString("en-IN");

    els.underReviewClaims.textContent =
      underReview.toLocaleString("en-IN");

    els.approvedClaims.textContent =
      approved.toLocaleString("en-IN");

    els.totalAmount.textContent = formatMoney(totalAmount);
  }

  // Display claims according to search and status filters.
  function renderClaimRows() {
    const query = els.searchInput.value.trim().toLowerCase();
    const selectedStatus = els.statusFilter.value;

    const filtered = allClaims.filter(claim => {
      const status = normalizedStatus(claim.claim_status);

      const searchable = [
        getClaimId(claim),
        claim.policy_number,
        claim.policyholder_name,
        claim.claimant_name,
        claim.vehicle_registration,
        claim.vehicle_number,
        claim.policyholder_id,
        claim.policy_id,
        claim.vehicle_id,
        claim.accident_description
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesSearch =
        !query || searchable.includes(query);

      const matchesStatus =
        selectedStatus === "all" ||
        status.toLowerCase() === selectedStatus.toLowerCase();

      return matchesSearch && matchesStatus;
    });

    els.claimsBody.innerHTML = "";

    if (filtered.length === 0) {
      els.emptyState.classList.remove("hidden");
      els.resultsCount.textContent =
        `Showing 0 of ${allClaims.length} claims`;
      return;
    }

    els.emptyState.classList.add("hidden");

    els.resultsCount.textContent =
      `Showing ${filtered.length} of ${allClaims.length} claims`;

    filtered.forEach(claim => {
      const id = getClaimId(claim);

      const policy =
        claim.policy_number ||
        claim.policy_no ||
        claim.policy_id ||
        "—";

      const holder =
        claim.policyholder_name ||
        claim.claimant_name ||
        claim.customer_name ||
        claim.policyholder_id ||
        "—";

      const date = formatDate(claim.accident_date);
      const amount = formatMoney(claim.claim_amount);
      const status = normalizedStatus(claim.claim_status);

      const row = document.createElement("tr");

      row.innerHTML = `
        <td>#${escapeHTML(id || "—")}</td>

        <td>${escapeHTML(holder)}</td>

        <td>${escapeHTML(policy)}</td>

        <td>${escapeHTML(date)}</td>

        <td class="amount">${escapeHTML(amount)}</td>

        <td>
          <span class="status-pill ${statusClass(status)}">
            ${escapeHTML(status)}
          </span>
        </td>

        <td>
          <button
            type="button"
            class="table-action"
            data-view-claim="${escapeHTML(id)}">
            View ↗
          </button>
        </td>
      `;

      els.claimsBody.appendChild(row);
    });
  }

  // Populate the claim selector for AI tools.
  function updateAiClaimOptions() {
    const currentValue = els.aiClaimSelect.value;

    els.aiClaimSelect.innerHTML =
      '<option value="">Choose a claim…</option>';

    allClaims.forEach(claim => {
      const id = getClaimId(claim);

      if (id === "") return;

      const option = document.createElement("option");

      option.value = String(id);

      option.textContent =
        `#${id} · ${claim.policy_number || claim.policy_id || "Policy not listed"} · ${formatMoney(claim.claim_amount)}`;

      els.aiClaimSelect.appendChild(option);
    });

    const optionExists = [...els.aiClaimSelect.options]
      .some(option => option.value === currentValue);

    if (optionExists) {
      els.aiClaimSelect.value = currentValue;
    }
  }

  // Fetch real claims from FastAPI.
  async function loadClaims(showMessage = false) {
    els.refreshButton.disabled = true;
    els.refreshButton.textContent = "Loading…";

    try {
      const data = await apiRequest("/claims");

      allClaims = Array.isArray(data)
        ? data
        : Array.isArray(data.claims)
          ? data.claims
          : [];

      updateStats();
      renderClaimRows();
      updateAiClaimOptions();

      setApiStatus(true, "API connected");

      if (showMessage) {
        showToast(`Loaded ${allClaims.length} claims.`);
      }
    } catch (error) {
      allClaims = [];

      updateStats();

      els.claimsBody.innerHTML = `
        <tr>
          <td colspan="7" class="table-message">
            ${escapeHTML(error.message)}
          </td>
        </tr>
      `;

      els.emptyState.classList.add("hidden");
      els.resultsCount.textContent = "Claims could not be loaded";

      updateAiClaimOptions();
      setApiStatus(false, "API disconnected");

      if (showMessage) {
        showToast(error.message);
      }
    } finally {
      els.refreshButton.disabled = false;
      els.refreshButton.textContent = "↻ Refresh";
    }
  }

  // Display details for a selected claim.
  function showClaimDetails(claim) {
    const fields = [
      ["Claim ID", getClaimId(claim)],
      ["Status", claim.claim_status],
      ["Policyholder ID", claim.policyholder_id],
      ["Policy number", claim.policy_number || claim.policy_id],
      ["Vehicle ID", claim.vehicle_id],
      ["Garage ID", claim.garage_id],
      ["Accident date", formatDate(claim.accident_date)],
      ["Claim amount", formatMoney(claim.claim_amount)],
      [
        "Created at",
        claim.created_at
          ? new Date(claim.created_at).toLocaleString("en-IN")
          : "—"
      ],
      ["Accident description", claim.accident_description || "—", true]
    ];

    els.dialogTitle.textContent =
      `Claim #${getClaimId(claim)}`;

    els.claimDetails.innerHTML = fields.map(
      ([label, value, full]) => `
        <div class="detail-item ${full ? "full" : ""}">
          <span>${escapeHTML(label)}</span>
          <strong>${escapeHTML(value ?? "—")}</strong>
        </div>
      `
    ).join("");

    if (typeof els.claimDialog.showModal === "function") {
      els.claimDialog.showModal();
    } else {
      alert(
        fields.map(([label, value]) => `${label}: ${value ?? "—"}`).join("\n")
      );
    }
  }

  async function viewClaim(id) {
    try {
      const claim = await apiRequest(
        `/claims/${encodeURIComponent(id)}`
      );

      showClaimDetails(claim.claim || claim);
    } catch (error) {
      const localClaim = allClaims.find(
        claim => String(getClaimId(claim)) === String(id)
      );

      if (localClaim && /404|not found/i.test(error.message)) {
        showClaimDetails(localClaim);
      } else {
        showToast(`Could not load claim: ${error.message}`);
      }
    }
  }

  // Show the response from an AI tool in the dashboard.
  function setAiResult(title, data) {
    els.aiResult.classList.remove("hidden");

    els.aiResult.textContent =
      `${title}\n\n${JSON.stringify(data, null, 2)}`;
  }

  // Call either the risk-assessment or AI-summary endpoint.
  async function runAiAction(kind) {
    const id = els.aiClaimSelect.value;

    if (!id) {
      showToast("Please select a claim first.");
      els.aiClaimSelect.focus();
      return;
    }

    const button =
      kind === "risk" ? els.riskButton : els.summaryButton;

    const originalText = button.textContent;

    button.disabled = true;

    button.textContent =
      kind === "risk" ? "Assessing…" : "Generating…";

    els.aiResult.classList.add("hidden");

    try {
      const endpoint = kind === "risk"
        ? `/claims/${encodeURIComponent(id)}/risk-assessment`
        : `/claims/${encodeURIComponent(id)}/ai-summary`;

      const result = await apiRequest(endpoint, {
        method: "POST"
      });

      const title = kind === "risk"
        ? "Demo risk assessment result"
        : "AI claim summary result";

      setAiResult(title, result);
    } catch (error) {
      setAiResult(
        kind === "risk"
          ? "Risk assessment could not be completed"
          : "AI summary is not available",
        {
          message: error.message,
          hint: kind === "summary"
            ? "The backend endpoint may not be fully implemented yet. Check FastAPI /docs and main.py."
            : "Check that the backend is running and that this claim exists."
        }
      );
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  function setFormMessage(message, type = "") {
    els.formMessage.textContent = message;
    els.formMessage.className =
      `form-message ${type}`.trim();
  }

  // Submit a new claim using the fields required by main.py.
  async function registerClaim(event) {
    event.preventDefault();

    setFormMessage("");

    const formData = new FormData(els.claimForm);

    const payload = {
      claimant_name: String(
        formData.get("claimant_name") || ""
      ).trim(),

      policy_number: String(
        formData.get("policy_number") || ""
      ).trim(),

      vehicle_registration: String(
        formData.get("vehicle_registration") || ""
      ).trim(),

      accident_date: String(
        formData.get("accident_date") || ""
      ),

      claim_amount: Number(
        formData.get("claim_amount")
      ),

      accident_description: String(
        formData.get("accident_description") || ""
      ).trim()
    };

    if (
      !Number.isFinite(payload.claim_amount) ||
      payload.claim_amount <= 0
    ) {
      setFormMessage(
        "Enter a claim amount greater than zero.",
        "error"
      );
      return;
    }

    els.submitClaimButton.disabled = true;
    els.submitClaimButton.textContent = "Submitting…";

    try {
      const result = await apiRequest("/claims", {
        method: "POST",
        body: JSON.stringify(payload)
      });

      setFormMessage(
        result.message || "Claim registered successfully.",
        "success"
      );

      showToast(
        result.message || "Claim registered successfully."
      );

      els.claimForm.reset();

      await loadClaims(false);

      const returnedId =
        result.claim_id ??
        result.claim?.claim_id ??
        result.claim?.id;

      if (returnedId !== undefined) {
        els.aiClaimSelect.value = String(returnedId);
      }
    } catch (error) {
      setFormMessage(error.message, "error");

      showToast(
        `Claim was not registered: ${error.message}`
      );
    } finally {
      els.submitClaimButton.disabled = false;

      els.submitClaimButton.innerHTML =
        'Submit claim <span>→</span>';
    }
  }

  // Search and filter controls.
  els.searchInput.addEventListener(
    "input",
    renderClaimRows
  );

  els.statusFilter.addEventListener(
    "change",
    renderClaimRows
  );

  // Refresh claims from the database.
  els.refreshButton.addEventListener(
    "click",
    () => loadClaims(true)
  );

  // Scroll to the registration form.
  els.topRegisterButton.addEventListener("click", () => {
    $("register-section").scrollIntoView({
      behavior: "smooth",
      block: "start"
    });

    const firstInput = els.claimForm.querySelector(
      'input[name="claimant_name"]'
    );

    setTimeout(() => firstInput.focus(), 350);
  });

  // Handle View button clicks in the claims table.
  els.claimsBody.addEventListener("click", event => {
    const button = event.target.closest(
      "[data-view-claim]"
    );

    if (button) {
      viewClaim(button.dataset.viewClaim);
    }
  });

  // Claim form submission.
  els.claimForm.addEventListener(
    "submit",
    registerClaim
  );

  // AI tools.
  els.riskButton.addEventListener(
    "click",
    () => runAiAction("risk")
  );

  els.summaryButton.addEventListener(
    "click",
    () => runAiAction("summary")
  );

  // Close claim details dialog.
  els.closeDialogButton.addEventListener(
    "click",
    () => els.claimDialog.close()
  );

  els.claimDialog.addEventListener("click", event => {
    if (event.target === els.claimDialog) {
      els.claimDialog.close();
    }
  });

  // Load the dashboard when the page opens.
  loadClaims();
})();