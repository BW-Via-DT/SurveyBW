(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};

  const config = window.ClaimsPageConfig || {};
  const lookups = config.lookups || {};

  function optionsFromLookup(key, fallbackOptions) {
    const rows = Array.isArray(lookups[key]) ? lookups[key] : [];

    if (!rows.length) return fallbackOptions;

    return rows.map(function (row) {
      return [row.code, row.label];
    });
  }
  
  function slugify(label) {
    return String(label)
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }

  function buildOptions(labels) {
    return labels.map(function (label) {
      return [slugify(label), label];
    });
  }

  const SUPPLIER_LABELS = [
    "IMI CZ (500315291)",
    "H&T China (500318549)",
    "H&T Roménia (500322201)",
    "IMI Servia (500321275)",
    "H&T Vietnam",
    "USI",
    "BMK"
  ];

  const CLAIM_TYPE_LABELS_LIST = ["0km", "Field", "0km-Lud", "Field-Lud"];

  const FAILURE_TYPE_LABELS_LIST = ["Process", "Component"];

  const STATUS_LABELS_LIST = [
    "To be shipped",
    "In transit",
    "Pending EMS",
    "Pending Manufacturer",
    "Pending BW",
    "To be closed",
    "Cost Discussion",
    "Closed",
    "At external lab",
    "Share new feedback",
    "Under Analysis at BW",
    "Returned to BW for more analysis"
  ];

  const ROOT_CAUSE_LABELS = [
    "Contamination",
    "Mechanical Damage",
    "Glue on the Solder",
    "Random Defect",
    "Wire Bonding",
    "Process",
    "Solder issue",
    "Wafer etching defect",
    "Wafer fab defect",
    "EOS",
    "NTF",
    "Out of Warranty",
    "Lost software",
    "Missing solder joint",
    "Solder Nok",
    "Wafer deffect",
    "PCBA Damaged",
    "Crack on the die",
    "Process issue",
    "Checksum unstable"
  ];

  const FAILURE_CLUSTER_LABELS = [
    "Leakage",
    "IGBT Pre-Charge",
    "IGBT HSS",
    "NTF",
    "IGBT Driver",
    "IGBT LSS",
    "HV Microcontroller",
    "LV Microcontroller",
    "Under Analysis",
    "NTC - soldering issue",
    "Mosfet",
    "Flyback",
    "Resistor",
    "Contamination",
    "IGBT Out of Spec",
    "Others",
    "Packaging",
    "NA",
    "Solder Broken on IGBT's",
    "SBC",
    "Soldering Issues",
    "Process",
    "NTC",
    "Mechanical Damage",
    "Excess of Flux"
  ];

  // Lista de exemplo/genérica — ajustar depois com os componentes reais
  // (por projeto/BOM, se vier a ser importada de outra plataforma).
  const CLAIMED_COMPONENT_LABELS = [
    "Relay K1",
    "Relay K2",
    "Relay K3",
    "Resistor R1",
    "Capacitor C1",
    "IGBT Module",
    "IGBT Driver IC",
    "Microcontroller (HV)",
    "Microcontroller (LV)",
    "SBC (System Basis Chip)",
    "Mosfet Q1",
    "Diode D1",
    "Connector J1",
    "Housing Seal",
    "Solder Joint",
    "Wire Bonding",
    "Flyback Transformer",
    "NTC Sensor",
    "Fuse",
    "Other"
  ];

  const SUPPLIER_OPTIONS = optionsFromLookup(
    "suppliers",
    buildOptions(SUPPLIER_LABELS)
  );

  const CLAIM_TYPE_OPTIONS = optionsFromLookup(
    "claim_types",
    buildOptions(CLAIM_TYPE_LABELS_LIST)
  );

  const FAILURE_TYPE_OPTIONS = optionsFromLookup(
    "failure_types",
    buildOptions(FAILURE_TYPE_LABELS_LIST)
  );

  const STATUS_OPTIONS = optionsFromLookup(
    "claim_statuses",
    buildOptions(STATUS_LABELS_LIST)
  );

  const ROOT_CAUSE_OPTIONS = optionsFromLookup(
    "root_causes",
    buildOptions(ROOT_CAUSE_LABELS)
  );

  const FAILURE_CLUSTER_OPTIONS = optionsFromLookup(
    "failure_clusters",
    buildOptions(FAILURE_CLUSTER_LABELS)
  );

  const CLAIMED_COMPONENT_OPTIONS = optionsFromLookup(
    "claimed_components",
    buildOptions(CLAIMED_COMPONENT_LABELS)
  );
  const YES_NO_OPTIONS = [["yes", "Yes"], ["no", "No"]];

  ClaimsTable.constants = {
    SUPPLIER_OPTIONS,
    CLAIM_TYPE_OPTIONS,
    FAILURE_TYPE_OPTIONS,
    STATUS_OPTIONS,
    ROOT_CAUSE_OPTIONS,
    FAILURE_CLUSTER_OPTIONS,
    CLAIMED_COMPONENT_OPTIONS,
    YES_NO_OPTIONS,

    SUPPLIER_LABEL_MAP: Object.fromEntries(SUPPLIER_OPTIONS),
    CLAIM_TYPE_LABEL_MAP: Object.fromEntries(CLAIM_TYPE_OPTIONS),
    FAILURE_TYPE_LABEL_MAP: Object.fromEntries(FAILURE_TYPE_OPTIONS),
    STATUS_LABEL_MAP: Object.fromEntries(STATUS_OPTIONS),
    ROOT_CAUSE_LABEL_MAP: Object.fromEntries(ROOT_CAUSE_OPTIONS),
    FAILURE_CLUSTER_LABEL_MAP: Object.fromEntries(FAILURE_CLUSTER_OPTIONS),
    CLAIMED_COMPONENT_LABEL_MAP: Object.fromEntries(CLAIMED_COMPONENT_OPTIONS),
    YES_NO_LABELS: { yes: "Yes", no: "No" }
  };
})(window);