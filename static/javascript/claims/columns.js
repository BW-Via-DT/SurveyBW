(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};
  const constants = ClaimsTable.constants;
  const computed = ClaimsTable.computed;
  const renderers = ClaimsTable.renderers;
  const utils = ClaimsTable.utils;

  const EXPORT_COLUMN_KEYS = [
    "supplier", "cpm", "customer_claim_number", "internal_claim_number", "pcba_dmc",
    "claim_type", "supplier_communication_date", "transport_requisition", "project",
    "part_number", "manufacturer", "efar_car",
    "failure_cluster", "failure_type", "claimed_components", "date_code", "failure_mode",
    "ppm",
    "shipment_date", "arrival_supplier_date", "d3_date", "d3_days", "d4_date", "d4_days",
    "d5_d6_date", "d8_date", "status_8d", "description_actions", "target_date", "close_date",
    "current_status", "open_days", "costs_associated", "costs_recovered",
    "improvement_action", "improvement_identification", "cleanpoint"
  ];

  const columnDefs = [
    {
      field: "supplier",
      headerName: "Supplier",
      minWidth: 190,
      cellRenderer: renderers.supplierRenderer
    },
    {
      field: "cpm",
      headerName: "CPM",
      minWidth: 120,
      filter: "agNumberColumnFilter"
    },
    {
      field: "customer_claim_number",
      headerName: "Customer Claim No.",
      minWidth: 170
    },
    {
      field: "project",
      headerName: "Project",
      minWidth: 150
    },
    {
      field: "part_number",
      headerName: "Part Number",
      minWidth: 150
    },
    {
      field: "manufacturer",
      headerName: "Manufacturer",
      minWidth: 160
    },
    {
      field: "pcba_dmc",
      headerName: "PCBA DMC",
      minWidth: 150,
      cellRenderer: renderers.dmcRenderer
    },
    {
      field: "claim_type",
      headerName: "Claim Type",
      minWidth: 125,
      cellRenderer: renderers.claimTypeRenderer,
      filterParams: {
        valueFormatter: params => constants.CLAIM_TYPE_LABEL_MAP[params.value] || params.value
      }
    },
    {
      field: "current_status",
      headerName: "Status",
      minWidth: 190,
      cellRenderer: renderers.statusRenderer,
      filterParams: {
        valueFormatter: params => constants.STATUS_LABEL_MAP[params.value] || params.value
      }
    },
    {
      headerName: "8D Status",
      colId: "status_8d",
      minWidth: 115,
      sortable: false,
      filter: false,
      cellRenderer: renderers.status8DRenderer,
      valueGetter: params => computed.compute8DStatus(params.data)
    },
    {
      headerName: "Open Days",
      colId: "open_days",
      minWidth: 120,
      filter: "agNumberColumnFilter",
      valueGetter: params => computed.computeOpenDays(params.data)
    },
    {
      field: "supplier_communication_date",
      headerName: "Supplier Comm.",
      minWidth: 150,
      filter: "agDateColumnFilter",
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "target_date",
      headerName: "Target Date",
      minWidth: 130,
      filter: "agDateColumnFilter",
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "close_date",
      headerName: "Close Date",
      minWidth: 130,
      filter: "agDateColumnFilter",
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "failure_cluster",
      headerName: "Failure Cluster",
      minWidth: 165,
      cellRenderer: renderers.failureClusterRenderer
    },
    {
      field: "failure_type",
      headerName: "Failure Type",
      minWidth: 145,
      cellRenderer: renderers.failureTypeRenderer,
      filterParams: {
        valueFormatter: params => constants.FAILURE_TYPE_LABEL_MAP[params.value] || params.value
      }
    },

    {
      headerName: "Claimed Components",
      colId: "claimed_components",
      minWidth: 260,
      filter: "agTextColumnFilter",
      valueGetter: params => computed.formatClaimedComponents(params.data),
      cellRenderer: renderers.claimedComponentsRenderer,
      tooltipValueGetter: params => computed.formatClaimedComponents(params.data)
    },

    {
      field: "ppm",
      headerName: "PPM Impact",
      minWidth: 125,
      cellRenderer: renderers.yesNoRenderer
    },
    {
      field: "improvement_action",
      headerName: "Improvement",
      minWidth: 135,
      cellRenderer: renderers.yesNoRenderer
    },
    {
      field: "costs_associated",
      headerName: "Costs Associated",
      minWidth: 160,
      filter: "agNumberColumnFilter",
      cellRenderer: renderers.moneyRenderer
    },
    {
      field: "costs_recovered",
      headerName: "Costs Recovered",
      minWidth: 155,
      filter: "agNumberColumnFilter",
      cellRenderer: renderers.moneyRenderer
    },

    {
      field: "internal_claim_number",
      headerName: "Internal Claim No.",
      hide: true
    },
    {
      field: "efar_car",
      headerName: "EFAR / CAR",
      hide: true
    },
    {
      field: "transport_requisition",
      headerName: "Transport Requisition",
      hide: true
    },
    {
      field: "date_code",
      headerName: "Date Code",
      hide: true
    },
    {
      field: "failure_mode",
      headerName: "Failure Mode",
      hide: true
    },
    {
      field: "description_actions",
      headerName: "Description of Actions",
      hide: true
    },
    {
      field: "shipment_date",
      headerName: "Shipment Date",
      hide: true,
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "arrival_supplier_date",
      headerName: "Arrival to Supplier",
      hide: true,
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "d3_date",
      headerName: "D3 Date",
      hide: true,
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      headerName: "D3 Days",
      colId: "d3_days",
      hide: true,
      valueGetter: params => computed.computeD3Days(params.data)
    },
    {
      field: "d4_date",
      headerName: "D4 Date",
      hide: true,
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      headerName: "D4 Days",
      colId: "d4_days",
      hide: true,
      valueGetter: params => computed.computeD4Days(params.data)
    },
    {
      field: "d5_d6_date",
      headerName: "D5/D6 Date",
      hide: true,
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "d8_date",
      headerName: "D8 Date",
      hide: true,
      valueFormatter: params => utils.fmtDate(params.value)
    },
    {
      field: "improvement_identification",
      headerName: "Improvement Identification",
      hide: true
    },
    {
      field: "cleanpoint",
      headerName: "Cleanpoint",
      hide: true
    },
    {
      headerName: "Actions",
      field: "actions",
      minWidth: 130,
      maxWidth: 130,
      pinned: "right",
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: renderers.actionsRenderer,
      cellClass: "ct-actions-col",
      suppressNavigable: true
    }
  ];

  const defaultColDef = {
    sortable: true,
    resizable: true,
    suppressHeaderMenuButton: false,
    filter: "agTextColumnFilter",
    floatingFilter: false,
    flex: 1,
    minWidth: 120,
    tooltipValueGetter: params => (params.value === null || params.value === undefined) ? "" : String(params.value),
    filterParams: {
      buttons: ["reset"],
      maxNumConditions: 1
    }
  };

  ClaimsTable.columns = {
    EXPORT_COLUMN_KEYS,
    columnDefs,
    defaultColDef
  };
})(window);