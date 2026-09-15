(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};
  const constants = ClaimsTable.constants;
  const utils = ClaimsTable.utils;

  function applyColumnFilter(field, value) {
    const gridApi = ClaimsTable.state.gridApi;
    const model = gridApi.getFilterModel() || {};

    if (value) {
      model[field] = {
        filterType: "text",
        type: "equals",
        filter: value
      };
    } else {
      delete model[field];
    }

    gridApi.setFilterModel(model);
  }

  function getUniqueValues(field) {
    return [...new Set(
      ClaimsTable.state.claimsData
        .map(item => item[field])
        .filter(value => value !== undefined && value !== null && String(value).trim() !== "")
        .map(value => String(value).trim())
    )].sort((a, b) => a.localeCompare(b));
  }

  function populateSelect(selectId, field) {
    const select = document.getElementById(selectId);
    if (!select) return;

    const firstOption = select.querySelector("option");
    const placeholder = firstOption ? firstOption.outerHTML : `<option value="">All</option>`;

    select.innerHTML = placeholder + getUniqueValues(field).map(function (value) {
      return `<option value="${utils.escapeAttr(value)}">${utils.escapeHtml(value)}</option>`;
    }).join("");
  }

  function populateFixedSelect(selectId, options) {
    const select = document.getElementById(selectId);
    if (!select) return;

    const firstOption = select.querySelector("option");
    const placeholder = firstOption ? firstOption.outerHTML : `<option value="">All</option>`;

    select.innerHTML = placeholder + options.map(function ([value, label]) {
      return `<option value="${utils.escapeAttr(value)}">${utils.escapeHtml(label)}</option>`;
    }).join("");
  }

  function populateDynamicFilters() {
    populateSelect("ctFilterManufacturer", "manufacturer");
    populateSelect("ctFilterProject", "project");
  }

  function updateExternalFilters() {
    const state = ClaimsTable.state;

    state.filterState.commFrom = document.getElementById("ctCommFrom").value;
    state.filterState.commTo = document.getElementById("ctCommTo").value;
    state.filterState.targetFrom = document.getElementById("ctTargetFrom").value;
    state.filterState.targetTo = document.getElementById("ctTargetTo").value;
    state.filterState.overdueOnly = document.getElementById("ctOverdueOnly").checked;
    state.filterState.duplicateOnly = document.getElementById("ctDuplicateOnly").checked;

    state.gridApi.onFilterChanged();
  }

  function resetFilters() {
    const state = ClaimsTable.state;

    document.getElementById("ctQuickFilter").value = "";

    document.getElementById("ctFilterSupplier").value = "";
    document.getElementById("ctFilterManufacturer").value = "";
    document.getElementById("ctFilterProject").value = "";
    document.getElementById("ctFilterClaimType").value = "";
    document.getElementById("ctFilterStatus").value = "";
    document.getElementById("ctFilterFailureType").value = "";
    document.getElementById("ctFilterFailureCluster").value = "";
    document.getElementById("ctFilterPpm").value = "";
    document.getElementById("ctFilterImprovement").value = "";

    document.getElementById("ctCommFrom").value = "";
    document.getElementById("ctCommTo").value = "";
    document.getElementById("ctTargetFrom").value = "";
    document.getElementById("ctTargetTo").value = "";
    document.getElementById("ctOverdueOnly").checked = false;
    document.getElementById("ctDuplicateOnly").checked = false;

    state.filterState.commFrom = "";
    state.filterState.commTo = "";
    state.filterState.targetFrom = "";
    state.filterState.targetTo = "";
    state.filterState.overdueOnly = false;
    state.filterState.duplicateOnly = false;

    state.gridApi.setGridOption("quickFilterText", "");
    state.gridApi.setFilterModel(null);
    state.gridApi.onFilterChanged();

    utils.notify("Filters reset", "info");
  }

  function bindFilterEvents() {
    document.getElementById("ctQuickFilter").addEventListener("input", function () {
      ClaimsTable.state.gridApi.setGridOption("quickFilterText", this.value);
    });

    document.getElementById("ctFilterSupplier").addEventListener("change", function () {
      applyColumnFilter("supplier", this.value);
    });

    document.getElementById("ctFilterManufacturer").addEventListener("change", function () {
      applyColumnFilter("manufacturer", this.value);
    });

    document.getElementById("ctFilterProject").addEventListener("change", function () {
      applyColumnFilter("project", this.value);
    });

    document.getElementById("ctFilterClaimType").addEventListener("change", function () {
      applyColumnFilter("claim_type", this.value);
    });

    document.getElementById("ctFilterStatus").addEventListener("change", function () {
      applyColumnFilter("current_status", this.value);
    });

    document.getElementById("ctFilterFailureType").addEventListener("change", function () {
      applyColumnFilter("failure_type", this.value);
    });

    document.getElementById("ctFilterFailureCluster").addEventListener("change", function () {
      applyColumnFilter("failure_cluster", this.value);
    });

    document.getElementById("ctFilterPpm").addEventListener("change", function () {
      applyColumnFilter("ppm", this.value);
    });

    document.getElementById("ctFilterImprovement").addEventListener("change", function () {
      applyColumnFilter("improvement_action", this.value);
    });

    [
      "ctCommFrom",
      "ctCommTo",
      "ctTargetFrom",
      "ctTargetTo",
      "ctOverdueOnly",
      "ctDuplicateOnly"
    ].forEach(function (id) {
      const element = document.getElementById(id);
      if (!element) return;

      element.addEventListener("change", updateExternalFilters);
    });

    document.getElementById("ctResetFilters").addEventListener("click", resetFilters);
  }

  function populateInitialFilters() {
    populateFixedSelect("ctFilterSupplier", constants.SUPPLIER_OPTIONS);
    populateFixedSelect("ctFilterClaimType", constants.CLAIM_TYPE_OPTIONS);
    populateFixedSelect("ctFilterStatus", constants.STATUS_OPTIONS);
    populateFixedSelect("ctFilterFailureType", constants.FAILURE_TYPE_OPTIONS);
    populateFixedSelect("ctFilterFailureCluster", constants.FAILURE_CLUSTER_OPTIONS);

    populateDynamicFilters();
  }

  ClaimsTable.filters = {
    applyColumnFilter,
    getUniqueValues,
    populateSelect,
    populateFixedSelect,
    populateDynamicFilters,
    updateExternalFilters,
    resetFilters,
    bindFilterEvents,
    populateInitialFilters
  };
})(window);