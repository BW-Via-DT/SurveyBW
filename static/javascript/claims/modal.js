(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};

  const constants = ClaimsTable.constants;
  const computed = ClaimsTable.computed;
  const utils = ClaimsTable.utils;

  const FIELD_GROUPS = [
    {
      title: "General Information",
      icon: "fa-industry",
      fields: [
        { key: "supplier", label: "Supplier", type: "select", options: constants.SUPPLIER_OPTIONS },
        { key: "cpm", label: "CPM", hint: "Claim number created on SAP", type: "number" },
        { key: "customer_claim_number", label: "Customer Claim Number", type: "text" },
        { key: "internal_claim_number", label: "Internal Claim Number", type: "text" },
        { key: "pcba_dmc", label: "PCBA DMC", hint: "Checked automatically for duplicates", type: "text" },
        { key: "claim_type", label: "Claim Type", type: "select", options: constants.CLAIM_TYPE_OPTIONS },
        { key: "project", label: "Project", type: "text" },
        { key: "part_number", label: "Part Number", type: "text" },
        { key: "manufacturer", label: "Manufacturer", type: "text" },
        {
          key: "efar_car",
          label: "EFAR / CAR",
          hint: "Manufacturer report number for the claimed component",
          type: "text"
        }
      ]
    },
    {
      title: "Failure Details",
      icon: "fa-bug",
      fields: [
        { key: "failure_cluster", label: "Failure Cluster", type: "select", options: constants.FAILURE_CLUSTER_OPTIONS },
        { key: "failure_type", label: "Type of Failure", type: "select", options: constants.FAILURE_TYPE_OPTIONS },
        { key: "date_code", label: "Date Code", type: "text" },
        {
          key: "failure_mode",
          label: "Failure Mode",
          hint: "Abstract of the failure mode reported to the supplier",
          type: "textarea",
          full: true
        },

        // Lista repetível: cada linha é um componente reclamado com a
        // sua própria root cause. Substitui os antigos campos únicos
        // "claimed_component" (texto) e "root_cause" (select).
        {
          key: "claimed_components",
          label: "Claimed Components & Root Cause",
          hint: "Add one row per claimed component; each can have a different root cause",
          type: "component_list",
          full: true
        },

        { key: "ppm", label: "PPM Impact", type: "select", options: constants.YES_NO_OPTIONS }
      ]
    },
    {
      title: "Timeline & 8D",
      icon: "fa-calendar-alt",
      fields: [
        { key: "supplier_communication_date", label: "Supplier Communication", type: "date" },
        { key: "transport_requisition", label: "Transport Requisition", type: "text" },
        { key: "shipment_date", label: "Shipment Date", type: "date" },
        { key: "arrival_supplier_date", label: "Arrival to Supplier", type: "date" },
        {
          key: "d3_date",
          label: "Date of D3",
          hint: "Initial report, production data, visual inspection, X-ray...",
          type: "date"
        },
        { key: "d3_days", label: "D3 Days", type: "computed", compute: computed.computeD3Days },
        {
          key: "d4_date",
          label: "Date of D4",
          hint: "Root cause identification",
          type: "date"
        },
        { key: "d4_days", label: "D4 Days", type: "computed", compute: computed.computeD4Days },
        {
          key: "d5_d6_date",
          label: "Date of D5/D6",
          hint: "Identification of actions",
          type: "date",
          dependsOn: "improvement_action",
          dependsValue: "yes"
        },
        {
          key: "d8_date",
          label: "Date of D8",
          hint: "Investigation considered closed",
          type: "date"
        },
        { key: "status_8d", label: "8D Status", type: "computed", compute: computed.compute8DStatus },
        {
          key: "description_actions",
          label: "Description of Actions",
          hint: "Filled in during the D4 phase",
          type: "textarea",
          full: true
        },
        {
          key: "target_date",
          label: "Target Date",
          hint: "For the actions (D4 phase)",
          type: "date"
        },
        {
          key: "close_date",
          label: "Close Date",
          hint: "For the actions (D4 phase)",
          type: "date"
        }
      ]
    },
    {
      title: "Status & Costs",
      icon: "fa-euro-sign",
      fields: [
        { key: "current_status", label: "Current Status", type: "select", options: constants.STATUS_OPTIONS },
        { key: "open_days", label: "Open Days", type: "computed", compute: computed.computeOpenDays },
        { key: "costs_associated", label: "Costs Associated", type: "currency" },
        { key: "costs_recovered", label: "Costs Recovered", type: "currency" }
      ]
    },
    {
      title: "Improvement Action",
      icon: "fa-lightbulb",
      fields: [
        { key: "improvement_action", label: "Improvement Action Defined?", type: "select", options: constants.YES_NO_OPTIONS },
        { key: "improvement_identification", label: "Improvement Action Identification", type: "textarea", full: true },
        { key: "cleanpoint", label: "Cleanpoint", type: "textarea", full: true }
      ]
    }
  ];

  // -----------------------------------------------------------------
  // Campo "component_list": lista repetível de {component, root_cause}
  // -----------------------------------------------------------------

  function componentListRowHtml(entry, index, editable) {
    const disabledAttr = editable ? "" : "disabled";
    const componentVal = (entry && entry.component) || "";
    const rootCauseVal = (entry && entry.root_cause) || "";

    const componentOptions = constants.CLAIMED_COMPONENT_OPTIONS.map(function ([value, label]) {
      const selected = String(value) === String(componentVal) ? "selected" : "";
      return `<option value="${utils.escapeAttr(value)}" ${selected}>${utils.escapeHtml(label)}</option>`;
    }).join("");

    const rootCauseOptions = constants.ROOT_CAUSE_OPTIONS.map(function ([value, label]) {
      const selected = String(value) === String(rootCauseVal) ? "selected" : "";
      return `<option value="${utils.escapeAttr(value)}" ${selected}>${utils.escapeHtml(label)}</option>`;
    }).join("");

    return `
      <div class="cf-component-row" data-index="${index}">
        <select class="cf-input" data-role="component" ${disabledAttr}>
          <option value="">Select component...</option>
          ${componentOptions}
        </select>

        <select class="cf-input" data-role="root_cause" ${disabledAttr}>
          <option value="">Select root cause...</option>
          ${rootCauseOptions}
        </select>

        <button type="button" class="cf-icon-btn cf-component-remove" data-role="remove-row" ${disabledAttr} title="Remove component">
          <i class="fas fa-trash-alt"></i>
        </button>
      </div>
    `;
  }

  function componentListFieldHtml(field, claim) {
    const entries = computed.getClaimedComponents(claim);
    const rowEntries = entries.length ? entries : [{ component: "", root_cause: "" }];

    const rows = rowEntries.map(function (entry, index) {
      return componentListRowHtml(entry, index, false);
    }).join("");

    const hint = field.hint ? `<em>${utils.escapeHtml(field.hint)}</em>` : "";

    return `
      <div class="cf-field cf-field--full cf-field--component-list" data-field="${utils.escapeAttr(field.key)}" data-type="component_list">
        <label class="cf-label">
          ${utils.escapeHtml(field.label)}
          ${hint}
        </label>

        <div class="cf-component-list" data-role="component-list-body">
          ${rows}
        </div>

        <button type="button" class="cf-btn cf-btn--ghost cf-component-add" data-role="add-row" disabled>
          <i class="fas fa-plus me-1"></i>
          Add component
        </button>
      </div>
    `;
  }

  function bindComponentListEvents() {
    const wrapper = document.querySelector('#ctModalBody [data-field="claimed_components"]');
    if (!wrapper) return;

    const body = wrapper.querySelector('[data-role="component-list-body"]');
    const addBtn = wrapper.querySelector('[data-role="add-row"]');

    addBtn.addEventListener("click", function () {
      const index = body.children.length;
      body.insertAdjacentHTML(
        "beforeend",
        componentListRowHtml({ component: "", root_cause: "" }, index, true)
      );
    });

    body.addEventListener("click", function (event) {
      const button = event.target.closest('[data-role="remove-row"]');
      if (!button || button.disabled) return;

      const row = button.closest(".cf-component-row");
      if (!row) return;

      if (body.children.length > 1) {
        row.remove();
      } else {
        // mantém sempre pelo menos uma linha visível; se for a única,
        // só limpa os valores em vez de a remover
        row.querySelectorAll("select").forEach(function (select) {
          select.value = "";
        });
      }
    });
  }

  function setComponentListEditable(editable) {
    document.querySelectorAll(
      '#ctModalBody [data-field="claimed_components"] select, ' +
      '#ctModalBody [data-field="claimed_components"] button'
    ).forEach(function (element) {
      element.disabled = !editable;
    });
  }

  function collectComponentListValues() {
    const rows = document.querySelectorAll(
      '#ctModalBody [data-field="claimed_components"] .cf-component-row'
    );

    const values = [];

    rows.forEach(function (row) {
      const componentSelect = row.querySelector('[data-role="component"]');
      const rootCauseSelect = row.querySelector('[data-role="root_cause"]');

      const component = componentSelect ? componentSelect.value : "";
      const rootCause = rootCauseSelect ? rootCauseSelect.value : "";

      if (component || rootCause) {
        values.push({ component: component, root_cause: rootCause });
      }
    });

    return values;
  }

  // -----------------------------------------------------------------
  // Campos "normais" (texto, select, data, etc.)
  // -----------------------------------------------------------------

  function fieldHtml(field, claim) {
    if (field.type === "component_list") {
      return componentListFieldHtml(field, claim);
    }

    const wrapperClasses = ["cf-field"];

    if (field.full) wrapperClasses.push("cf-field--full");
    if (field.type === "computed") wrapperClasses.push("cf-field--computed");
    if (field.dependsOn) wrapperClasses.push("cf-field--conditional");

    const hint = field.hint ? `<em>${utils.escapeHtml(field.hint)}</em>` : "";

    let hiddenAttr = "";

    if (field.dependsOn) {
      const shouldHide = String(claim[field.dependsOn]) !== String(field.dependsValue);

      hiddenAttr = `
        data-depends-on="${utils.escapeAttr(field.dependsOn)}"
        data-depends-value="${utils.escapeAttr(field.dependsValue)}"
        data-hidden="${shouldHide}"
      `;
    }

    let control = "";

    if (field.type === "computed") {
      const value = field.compute ? field.compute(claim) : "";
      const display = value === null || value === undefined || value === "" ? "—" : value;

      control = `
        <span class="cf-computed-value" data-field="${utils.escapeAttr(field.key)}">
          ${utils.escapeHtml(display)}
        </span>
      `;
    } else if (field.type === "select") {
      const val = claim[field.key] ?? "";

      const options = field.options.map(function ([optionValue, optionLabel]) {
        const selected = String(optionValue) === String(val) ? "selected" : "";

        return `
          <option value="${utils.escapeAttr(optionValue)}" ${selected}>
            ${utils.escapeHtml(optionLabel)}
          </option>
        `;
      }).join("");

      control = `
        <select class="cf-input" data-field="${utils.escapeAttr(field.key)}" disabled>
          <option value="">Select...</option>
          ${options}
        </select>
      `;
    } else if (field.type === "textarea") {
      const val = claim[field.key] ?? "";

      control = `
        <textarea class="cf-textarea" rows="${field.full ? 4 : 2}" data-field="${utils.escapeAttr(field.key)}" disabled>${utils.escapeHtml(val)}</textarea>
      `;
    } else if (field.type === "date") {
      const val = claim[field.key] ?? "";

      control = `
        <input type="date" class="cf-input" data-field="${utils.escapeAttr(field.key)}" value="${utils.escapeAttr(val)}" disabled>
      `;
    } else if (field.type === "number") {
      const val = claim[field.key] ?? "";

      control = `
        <input type="number" class="cf-input" data-field="${utils.escapeAttr(field.key)}" value="${utils.escapeAttr(val)}" disabled>
      `;
    } else if (field.type === "currency") {
      const val = claim[field.key] ?? "";

      control = `
        <div class="cf-input-group">
          <span class="cf-input-group__prefix">€</span>
          <input type="number" step="0.01" class="cf-input" data-field="${utils.escapeAttr(field.key)}" value="${utils.escapeAttr(val)}" disabled>
        </div>
      `;
    } else {
      const val = claim[field.key] ?? "";

      control = `
        <input type="text" class="cf-input" data-field="${utils.escapeAttr(field.key)}" value="${utils.escapeAttr(val)}" disabled>
      `;
    }

    return `
      <div class="${wrapperClasses.join(" ")}" ${hiddenAttr}>
        <label class="cf-label">
          ${utils.escapeHtml(field.label)}
          ${hint}
        </label>
        ${control}
      </div>
    `;
  }

  function renderModalBody(claim) {
    const body = document.getElementById("ctModalBody");
    if (!body) return;

    const duplicateWarning = computed.isDuplicateDmc(claim) ? `
      <div class="ct-modal-warning">
        <i class="fas fa-triangle-exclamation"></i>
        This PCBA DMC (${utils.escapeHtml(claim.pcba_dmc)}) already exists in another claim.
      </div>
    ` : "";

    body.innerHTML = duplicateWarning + FIELD_GROUPS.map(function (group) {
      return `
        <section class="ct-modal-section">
          <div class="ct-modal-section__header">
            <span class="ct-modal-section__icon">
              <i class="fas ${utils.escapeAttr(group.icon)}"></i>
            </span>
            <span>${utils.escapeHtml(group.title)}</span>
          </div>

          <div class="ct-modal-grid">
            ${group.fields.map(function (field) {
              return fieldHtml(field, claim);
            }).join("")}
          </div>
        </section>
      `;
    }).join("");

    bindConditionalFields();
    bindComponentListEvents();
  }

  function bindConditionalFields() {
    const trigger = document.querySelector('#ctModalBody [data-field="improvement_action"]');
    if (!trigger) return;

    trigger.addEventListener("change", function () {
      document.querySelectorAll("#ctModalBody [data-depends-on]").forEach(function (wrapper) {
        const dependsOn = wrapper.dataset.dependsOn;
        const dependsValue = wrapper.dataset.dependsValue;
        const currentField = document.querySelector(`#ctModalBody [data-field="${dependsOn}"]`);

        if (!currentField) return;

        const shouldHide = String(currentField.value) !== String(dependsValue);
        wrapper.dataset.hidden = shouldHide;
      });
    });
  }

  function refreshComputedFields(claim) {
    document.querySelectorAll("#ctModalBody .cf-computed-value").forEach(function (el) {
      const key = el.dataset.field;
      const field = FIELD_GROUPS.flatMap(group => group.fields).find(item => item.key === key);

      if (!field || !field.compute) return;

      const value = field.compute(claim);
      el.textContent = value === null || value === undefined || value === "" ? "—" : value;
    });
  }

  function findClaim(id) {
    return ClaimsTable.state.claimsData.find(function (claim) {
      return String(claim.id) === String(id);
    });
  }

  function openModal(id, startEditing) {
    const claim = findClaim(id);
    if (!claim) return;

    const state = ClaimsTable.state;

    state.currentClaimId = id;

    document.getElementById("ctModalTitle").textContent =
      constants.SUPPLIER_LABEL_MAP[claim.supplier] || claim.supplier || "Claim";

    document.getElementById("ctModalSubtitle").textContent = [
      claim.cpm,
      claim.customer_claim_number,
      claim.part_number,
      claim.current_status ? constants.STATUS_LABEL_MAP[claim.current_status] || claim.current_status : ""
    ].filter(Boolean).join(" · ") || " ";

    renderModalBody(claim);
    setModalMode(Boolean(startEditing && state.isAdmin));

    state.bsModal.show();
  }

  function setModalMode(enable) {
    const state = ClaimsTable.state;
    state.editMode = Boolean(enable && state.isAdmin);

    document.querySelectorAll("#ctModalBody [data-field]").forEach(function (element) {
      // ignora o wrapper da lista de componentes: os seus controlos
      // (selects/botões) são tratados à parte em setComponentListEditable
      if (element.dataset.type === "component_list") return;

      element.disabled = !state.editMode;
    });

    setComponentListEditable(state.editMode);

    document.getElementById("ctModeBadge").classList.toggle("d-none", !state.editMode);
    document.getElementById("ctCancelEditBtn").classList.toggle("d-none", !state.editMode);

    if (state.isAdmin) {
      document.getElementById("ctEditBtn").classList.toggle("d-none", state.editMode);
      document.getElementById("ctSaveBtn").classList.toggle("d-none", !state.editMode);
    }
  }

  function cancelEdit() {
    const state = ClaimsTable.state;

    if (state.editMode && state.currentClaimId !== null) {
      const claim = findClaim(state.currentClaimId);

      if (claim) renderModalBody(claim);

      setModalMode(false);
      return;
    }

    state.bsModal.hide();
  }

  async function saveClaim() {
    const state = ClaimsTable.state;
    const claim = findClaim(state.currentClaimId);

    if (!claim) return;

    const updatedClaim = { ...claim };

    document.querySelectorAll("#ctModalBody [data-field]").forEach(function (element) {
      // A lista de componentes é recolhida à parte
      if (element.dataset.type === "component_list") return;

      const key = element.dataset.field;

      if (!key) return;

      if (element.type === "number") {
        updatedClaim[key] = element.value === "" ? "" : parseFloat(element.value);
      } else {
        updatedClaim[key] = element.value;
      }
    });

    updatedClaim.claimed_components = collectComponentListValues();

    // Se "Improvement Action" passou a "No", limpa a data de D5/D6
    if (updatedClaim.improvement_action !== "yes") {
      updatedClaim.d5_d6_date = "";
    }

    try {
      const response = await fetch(`/api/claims/${encodeURIComponent(updatedClaim.id)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(updatedClaim)
      });

      if (!response.ok) {
      let errorMessage = "Failed to save claim";

      try {
        const errorBody = await response.json();
        errorMessage = errorBody.error || errorBody.details || errorMessage;
        console.error("Save claim API error:", errorBody);
      } catch (_) {
        errorMessage = await response.text();
      }

      throw new Error(errorMessage);
    }

      const savedClaim = await response.json();

      Object.assign(claim, savedClaim);

      state.gridApi.applyTransaction({ update: [claim] });

      ClaimsTable.filters.populateDynamicFilters();
      refreshComputedFields(claim);

      setModalMode(false);
      utils.notify("Claim saved successfully", "success");
    } catch (error) {
      console.error(error);
      utils.notify(error.message || "Could not save the claim", "error");
    }
  }

  async function deleteClaim(id, fromModal) {
    const state = ClaimsTable.state;

    if (!state.isAdmin) return;

    const claim = findClaim(id);
    if (!claim) return;

    const label = claim.cpm || claim.customer_claim_number || `#${id}`;

    const result = await Swal.fire({
      icon: "warning",
      title: "Delete claim?",
      html: `
        <div class="ct-swal-text">
          Claim <strong>${utils.escapeHtml(label)}</strong> will be permanently deleted.
          <br>
          This action cannot be undone.
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
      reverseButtons: true,
      focusCancel: true,
      buttonsStyling: false,
      customClass: {
        popup: "ct-swal-popup",
        confirmButton: "ct-swal-confirm",
        cancelButton: "ct-swal-cancel"
      }
    });

    if (!result.isConfirmed) return;

    try {
      const response = await fetch(`/api/claims/${encodeURIComponent(id)}`, {
        method: "DELETE"
      });

      if (!response.ok) {
        throw new Error("Failed to delete claim");
      }

      state.claimsData = state.claimsData.filter(function (item) {
        return String(item.id) !== String(id);
      });

      state.gridApi.applyTransaction({ remove: [claim] });

      ClaimsTable.filters.populateDynamicFilters();

      if (fromModal) state.bsModal.hide();

      utils.notify("Claim deleted", "success");
    } catch (error) {
      console.error(error);
      utils.notify("Could not delete the claim", "error");
    }
  }

  ClaimsTable.modal = {
    FIELD_GROUPS,
    findClaim,
    openModal,
    setModalMode,
    cancelEdit,
    saveClaim,
    deleteClaim,
    refreshComputedFields
  };
})(window);