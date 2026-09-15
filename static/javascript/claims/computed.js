(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};
  const utils = ClaimsTable.utils;
  const constants = ClaimsTable.constants;

  function isClosed(claim) {
    return claim.current_status === "closed" || Boolean(claim.close_date);
  }

  function isOverdue(claim) {
    const targetDate = utils.normalizeDate(claim.target_date);
    if (!targetDate) return false;
    if (isClosed(claim)) return false;

    return targetDate < utils.getToday();
  }

  function computeD3Days(claim) {
    return utils.daysBetween(claim.supplier_communication_date, claim.d3_date);
  }

  function computeD4Days(claim) {
    return utils.daysBetween(claim.d3_date, claim.d4_date);
  }

  function computeOpenDays(claim) {
    const start = claim.supplier_communication_date;
    if (!start) return null;

    const end = isClosed(claim) ? (claim.close_date || claim.d8_date) : null;

    return utils.daysBetween(
      start,
      end || new Date().toISOString().slice(0, 10)
    );
  }

  function compute8DStatus(claim) {
    if (claim.d8_date || isClosed(claim)) return "D8";

    if (claim.d4_date) {
      if (claim.improvement_action === "yes") {
        return claim.d5_d6_date ? "D7" : "D5/D6";
      }

      return "D7";
    }

    if (claim.d3_date) return "D4";
    if (claim.supplier_communication_date) return "D3";

    return "D1";
  }

  function getDuplicateDmcSet() {
    const counts = {};
    const claimsData = ClaimsTable.state.claimsData;

    claimsData.forEach(function (claim) {
      const dmc = String(claim.pcba_dmc || "").trim();
      if (!dmc) return;

      counts[dmc] = (counts[dmc] || 0) + 1;
    });

    return new Set(Object.keys(counts).filter(function (dmc) {
      return counts[dmc] > 1;
    }));
  }

  function isDuplicateDmc(claim) {
    const dmc = String(claim.pcba_dmc || "").trim();
    if (!dmc) return false;

    return getDuplicateDmcSet().has(dmc);
  }

  function getClaimedComponents(claim) {
    return Array.isArray(claim.claimed_components) ? claim.claimed_components : [];
  }

  function formatClaimedComponents(claim) {
    const entries = getClaimedComponents(claim);

    if (!entries.length) return "";

    return entries.map(function (entry) {
      const componentLabel = constants.CLAIMED_COMPONENT_LABEL_MAP[entry.component] || entry.component || "";
      const rootCauseLabel = entry.root_cause
        ? (constants.ROOT_CAUSE_LABEL_MAP[entry.root_cause] || entry.root_cause)
        : "";

      if (!componentLabel) return "";

      return rootCauseLabel ? `${componentLabel} (${rootCauseLabel})` : componentLabel;
    }).filter(Boolean).join("; ");
  }

  ClaimsTable.computed = {
    isClosed,
    isOverdue,
    computeD3Days,
    computeD4Days,
    computeOpenDays,
    compute8DStatus,
    getDuplicateDmcSet,
    isDuplicateDmc,
    getClaimedComponents,
    formatClaimedComponents
  };
})(window);