(function (window, document) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};

  const config = window.ClaimsPageConfig || {};
  const computed = ClaimsTable.computed;
  const columns = ClaimsTable.columns;
  const modal = ClaimsTable.modal;
  const filters = ClaimsTable.filters;
  const exporter = ClaimsTable.exporter;
  const utils = ClaimsTable.utils;

  const serverClaims = Array.isArray(config.claims) ? config.claims : [];

  ClaimsTable.state = {
    isAdmin: Boolean(config.isAdmin),
    claimsData: serverClaims,

    filterState: {
      commFrom: "",
      commTo: "",
      targetFrom: "",
      targetTo: "",
      overdueOnly: false,
      duplicateOnly: false
    },

    gridApi: null,
    currentClaimId: null,
    editMode: false,
    bsModal: null
  };

  function onCellClicked(params) {
    if (params.colDef.field !== "actions") return;

    const button = params.event.target.closest("button[data-action]");
    if (!button || button.disabled) return;

    const id = button.dataset.id;
    const action = button.dataset.action;

    if (action === "view") modal.openModal(id, false);
    if (action === "edit") modal.openModal(id, true);
    if (action === "delete") modal.deleteClaim(id);
  }

  function onRowDoubleClicked(params) {
    if (params.event && params.event.target && params.event.target.closest("button")) return;
    modal.openModal(params.data.id, false);
  }

  function buildGridOptions() {
    const state = ClaimsTable.state;

    return {
      columnDefs: columns.columnDefs,
      defaultColDef: columns.defaultColDef,
      columnMenu: "new",
      rowData: state.claimsData,

      pagination: true,
      paginationPageSize: 10,
      paginationPageSizeSelector: [10, 20, 50, 100],

      animateRows: true,
      rowSelection: "single",

      enableCellTextSelection: true,
      ensureDomOrder: true,
      suppressClipboardPaste: true,

      overlayNoRowsTemplate: `
        <span class="ct-empty-state">
          No claims found
        </span>
      `,

      isExternalFilterPresent: function () {
        const fs = state.filterState;
        return Boolean(
          fs.commFrom ||
          fs.commTo ||
          fs.targetFrom ||
          fs.targetTo ||
          fs.overdueOnly ||
          fs.duplicateOnly
        );
      },

      doesExternalFilterPass: function (node) {
        const claim = node.data;
        if (!claim) return false;

        const fs = state.filterState;

        if ((fs.commFrom || fs.commTo) &&
            !utils.dateIsBetween(claim.supplier_communication_date, fs.commFrom, fs.commTo)) {
          return false;
        }

        if ((fs.targetFrom || fs.targetTo) &&
            !utils.dateIsBetween(claim.target_date, fs.targetFrom, fs.targetTo)) {
          return false;
        }

        if (fs.overdueOnly && !computed.isOverdue(claim)) {
          return false;
        }

        if (fs.duplicateOnly && !computed.isDuplicateDmc(claim)) {
          return false;
        }

        return true;
      },

      rowClassRules: {
        "ct-row-overdue": function (params) {
          return computed.isOverdue(params.data);
        }
      },

      onCellClicked: onCellClicked,
      onRowDoubleClicked: onRowDoubleClicked
    };
  }

  function bindModalButtons() {
    const state = ClaimsTable.state;

    document.getElementById("ctCancelEditBtn").addEventListener("click", modal.cancelEdit);

    if (state.isAdmin) {
      const editBtn = document.getElementById("ctEditBtn");
      const saveBtn = document.getElementById("ctSaveBtn");
      const deleteBtn = document.getElementById("ctDeleteBtn");

      if (editBtn) {
        editBtn.addEventListener("click", function () {
          modal.setModalMode(true);
        });
      }

      if (saveBtn) {
        saveBtn.addEventListener("click", modal.saveClaim);
      }

      if (deleteBtn) {
        deleteBtn.addEventListener("click", function () {
          if (state.currentClaimId !== null) {
            modal.deleteClaim(state.currentClaimId, true);
          }
        });
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const state = ClaimsTable.state;

    const modalEl = document.getElementById("claimDetailModal");
    state.bsModal = new bootstrap.Modal(modalEl);

    const gridElement = document.getElementById("claimsGrid");
    state.gridApi = agGrid.createGrid(gridElement, buildGridOptions());

    filters.populateInitialFilters();
    filters.bindFilterEvents();
    exporter.bindExportEvents();
    bindModalButtons();
  });

})(window, document);