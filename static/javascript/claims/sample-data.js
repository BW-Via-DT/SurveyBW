(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};

  ClaimsTable.sampleClaims = [
    {
      id: 1,
      supplier: "imi_cz_500315291",
      cpm: 2024113,
      customer_claim_number: "CC-88213",
      internal_claim_number: "INT-0451",
      pcba_dmc: "778812",
      claim_type: "0km",
      supplier_communication_date: "2024-11-03",
      transport_requisition: "TR-5521",
      project: "Project Falcon",
      part_number: "PN-44521-A",
      manufacturer: "Bosch GmbH",
      efar_car: "EFAR-33291",

      failure_cluster: "igbt_driver",
      failure_type: "component",
      date_code: "2418",
      failure_mode: "Intermittent relay failure with signal loss under vibration.",
      ppm: "yes",

      // Cada componente reclamado tem a sua própria root cause.
      claimed_components: [
        { component: "relay_k3", root_cause: "solder_issue" }
      ],

      shipment_date: "2024-11-05",
      arrival_supplier_date: "2024-11-12",
      d3_date: "2024-11-15",
      d4_date: "2024-11-28",
      d5_d6_date: "",
      d8_date: "",
      description_actions: "8D analysis started. Supplier performed X-ray inspection and cross-section analysis on returned units.",
      target_date: "2024-12-20",
      close_date: "",

      current_status: "pending_manufacturer",
      costs_associated: 1450.00,
      costs_recovered: 0,

      improvement_action: "yes",
      improvement_identification: "Update reflow oven profile and add AOI inspection checkpoint.",
      cleanpoint: "CP-2024-091"
    },
    {
      id: 2,
      supplier: "h_t_vietnam",
      cpm: 2024087,
      customer_claim_number: "CC-77104",
      internal_claim_number: "INT-0392",
      pcba_dmc: "661120",
      claim_type: "field",
      supplier_communication_date: "2024-09-18",
      transport_requisition: "TR-5390",
      project: "Project Orion",
      part_number: "PN-33810-C",
      manufacturer: "Continental AG",
      efar_car: "EFAR-29940",

      failure_cluster: "ntc",
      failure_type: "process",
      date_code: "2312",
      failure_mode: "Water ingress reported in field units after six months of use.",
      ppm: "no",

      claimed_components: [
        { component: "housing_seal", root_cause: "process" }
      ],

      shipment_date: "2024-09-20",
      arrival_supplier_date: "2024-09-25",
      d3_date: "2024-09-27",
      d4_date: "2024-10-10",
      d5_d6_date: "",
      d8_date: "2024-10-30",
      description_actions: "Root cause confirmed after disassembly of five returned units. Process parameters were reviewed and corrected.",
      target_date: "2024-10-30",
      close_date: "2024-10-30",

      current_status: "closed",
      costs_associated: 890.00,
      costs_recovered: 890.00,

      improvement_action: "no",
      improvement_identification: "",
      cleanpoint: ""
    },
    {
      id: 3,
      supplier: "h_t_vietnam",
      cpm: 2024087,
      customer_claim_number: "CC-77104",
      internal_claim_number: "INT-0392",
      pcba_dmc: "661120",
      claim_type: "field",
      supplier_communication_date: "2024-09-18",
      transport_requisition: "TR-5390",
      project: "Project Orion",
      part_number: "PN-33810-C",
      manufacturer: "Continental AG",
      efar_car: "EFAR-29940",

      failure_cluster: "ntc",
      failure_type: "process",
      date_code: "2312",
      failure_mode: "Water ingress reported in field units after six months of use.",
      ppm: "no",

      // Exemplo com dois componentes reclamados na mesma claim, cada
      // um com uma root cause diferente.
      claimed_components: [
        { component: "housing_seal", root_cause: "process" },
        { component: "ntc_sensor", root_cause: "contamination" }
      ],

      shipment_date: "2024-09-20",
      arrival_supplier_date: "2024-09-25",
      d3_date: "2024-09-27",
      d4_date: "2024-10-10",
      d5_d6_date: "",
      d8_date: "2024-10-30",
      description_actions: "Root cause confirmed after disassembly of five returned units. Process parameters were reviewed and corrected.",
      target_date: "2024-10-30",
      close_date: "2024-10-30",

      current_status: "closed",
      costs_associated: 890.00,
      costs_recovered: 890.00,

      improvement_action: "no",
      improvement_identification: "",
      cleanpoint: ""
    }
  ];
})(window);