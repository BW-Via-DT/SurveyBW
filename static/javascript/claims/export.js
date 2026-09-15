(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};
  const constants = ClaimsTable.constants;
  const computed = ClaimsTable.computed;
  const utils = ClaimsTable.utils;

  function formatExportValue(field, value) {
    if (value === undefined || value === null) return "";

    if (field === "supplier") return constants.SUPPLIER_LABEL_MAP[value] || value;
    if (field === "claim_type") return constants.CLAIM_TYPE_LABEL_MAP[value] || value;
    if (field === "current_status") return constants.STATUS_LABEL_MAP[value] || value;
    if (field === "failure_type") return constants.FAILURE_TYPE_LABEL_MAP[value] || value;
    if (field === "failure_cluster") return constants.FAILURE_CLUSTER_LABEL_MAP[value] || value;
    if (field === "ppm" || field === "improvement_action") return constants.YES_NO_LABELS[value] || value;

    if ([
      "supplier_communication_date",
      "shipment_date",
      "arrival_supplier_date",
      "d3_date",
      "d4_date",
      "d5_d6_date",
      "d8_date",
      "target_date",
      "close_date"
    ].includes(field)) {
      return utils.fmtDate(value);
    }

    if (["costs_associated", "costs_recovered"].includes(field)) {
      return Number(value || 0).toFixed(2);
    }

    return value;
  }

  function buildExportParams(fileNamePrefix) {
    const today = new Date().toISOString().slice(0, 10);

    return {
      fileName: `${fileNamePrefix}_${today}`,
      columnKeys: ClaimsTable.columns.EXPORT_COLUMN_KEYS,
      processHeaderCallback: function (params) {
        const colDef = params.column.getColDef();
        return colDef.headerName || colDef.field || colDef.colId;
      },
      processCellCallback: function (params) {
        const field = params.column.getColId();
        const claim = params.node.data;

        if (field === "status_8d") return computed.compute8DStatus(claim);
        if (field === "d3_days") return computed.computeD3Days(claim) ?? "";
        if (field === "d4_days") return computed.computeD4Days(claim) ?? "";
        if (field === "open_days") return computed.computeOpenDays(claim) ?? "";
        if (field === "claimed_components") return computed.formatClaimedComponents(claim);

        return formatExportValue(field, params.value);
      }
    };
  }

  function exportFilteredClaims() {
    const gridApi = ClaimsTable.state.gridApi;
    if (!gridApi) return;

    const params = buildExportParams("claims_export");
    params.fileName += ".csv";

    gridApi.exportDataAsCsv(params);
    utils.notify("Export CSV generated", "success");
  }

  function exportFilteredClaimsExcel() {
    const gridApi = ClaimsTable.state.gridApi;
    if (!gridApi) return;

    const params = buildExportParams("claims_export");
    params.fileName += ".xlsx";
    params.sheetName = "Claims";

    gridApi.exportDataAsExcel(params);
    utils.notify("Export Excel generated", "success");
  }

  function bindExportEvents() {
    document.getElementById("ctExportCsv").addEventListener("click", function (event) {
      event.preventDefault();
      exportFilteredClaims();
    });

    document.getElementById("ctExportExcel").addEventListener("click", function (event) {
      event.preventDefault();
      exportFilteredClaimsExcel();
    });
  }

  ClaimsTable.exporter = {
    formatExportValue,
    exportFilteredClaims,
    exportFilteredClaimsExcel,
    bindExportEvents
  };
})(window);