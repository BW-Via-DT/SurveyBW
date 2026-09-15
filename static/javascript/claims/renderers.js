(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};
  const constants = ClaimsTable.constants;
  const computed = ClaimsTable.computed;
  const utils = ClaimsTable.utils;

  function labelRenderer(map, className) {
    return function (params) {
      if (!params.value) return "";

      const label = map[params.value] || params.value;
      return `<span class="ct-badge ${className}">${utils.escapeHtml(label)}</span>`;
    };
  }

  function claimTypeRenderer(params) {
    if (!params.value) return "";

    const className = params.value.indexOf("0km") === 0
      ? "ct-badge--0km"
      : "ct-badge--field";

    const label = constants.CLAIM_TYPE_LABEL_MAP[params.value] || params.value;

    return `<span class="ct-badge ${className}">${utils.escapeHtml(label)}</span>`;
  }

  function statusRenderer(params) {
    if (!params.value) return "";

    const label = constants.STATUS_LABEL_MAP[params.value] || params.value;

    return `
      <span class="cf-pill" data-status="${utils.escapeAttr(params.value)}">
        <i class="fas fa-circle"></i>
        ${utils.escapeHtml(label)}
      </span>
    `;
  }

  function status8DRenderer(params) {
    const value = computed.compute8DStatus(params.data);
    return `<span class="ct-badge ct-badge--8d">${utils.escapeHtml(value)}</span>`;
  }

  function yesNoRenderer(params) {
    if (!params.value) return "";

    const label = constants.YES_NO_LABELS[params.value] || params.value;
    const className = params.value === "yes" ? "ct-badge--yes" : "ct-badge--no";

    return `<span class="ct-badge ${className}">${utils.escapeHtml(label)}</span>`;
  }

  function moneyRenderer(params) {
    const number = Number(params.value || 0);
    const className = number === 0 ? "ct-money ct-money--zero" : "ct-money";

    return `<span class="${className}">${utils.escapeHtml(utils.fmtMoney(number))}</span>`;
  }

  function supplierRenderer(params) {
    if (!params.value) return "";

    return utils.escapeHtml(
      constants.SUPPLIER_LABEL_MAP[params.value] || params.value
    );
  }

  function dmcRenderer(params) {
    if (!params.value) return "";

    if (computed.isDuplicateDmc(params.data)) {
      return `
        <span class="ct-dmc-cell" title="This PCBA DMC appears in more than one claim">
          <i class="fas fa-triangle-exclamation"></i>
          ${utils.escapeHtml(params.value)}
        </span>
      `;
    }

    return utils.escapeHtml(params.value);
  }

  // Cada claim pode ter vários componentes reclamados, cada um com a sua
  // própria root cause. Mostra um badge por componente, com a root cause
  // como sub-texto (e também como "title" para tooltip).
  function claimedComponentsRenderer(params) {
    const entries = computed.getClaimedComponents(params.data);
    if (!entries.length) return "";

    const badges = entries.map(function (entry) {
      const componentLabel = constants.CLAIMED_COMPONENT_LABEL_MAP[entry.component] || entry.component;
      if (!componentLabel) return "";

      const rootCauseLabel = entry.root_cause
        ? (constants.ROOT_CAUSE_LABEL_MAP[entry.root_cause] || entry.root_cause)
        : "";

      return `
        <span class="ct-badge ct-badge--claim-comp">
          ${utils.escapeHtml(componentLabel)}${rootCauseLabel ? ` <em>(${utils.escapeHtml(rootCauseLabel)})</em>` : ""}
        </span>
      `;
    }).join("");

    // envolve tudo num único container que corta com "..." se não couber;
    // o texto completo aparece via tooltip do AG Grid (tooltipValueGetter)
    return `<span class="ct-multi-badges">${badges}</span>`;
  }

  function actionsRenderer(params) {
    const isAdmin = ClaimsTable.state.isAdmin;
    const editDisabled = isAdmin ? "" : "disabled";
    const deleteDisabled = isAdmin ? "" : "disabled";
    const claimId = utils.escapeAttr(params.data.id);

    return `
      <div class="ct-actions-cell">
        <button type="button" class="ct-icon-btn ct-icon-btn--view" title="View details" data-action="view" data-id="${claimId}">
          <i class="fas fa-eye"></i>
        </button>

        <button type="button" class="ct-icon-btn ct-icon-btn--edit" title="${isAdmin ? "Edit" : "Administrators only"}" data-action="edit" data-id="${claimId}" ${editDisabled}>
          <i class="fas fa-pen"></i>
        </button>

        <button type="button" class="ct-icon-btn ct-icon-btn--delete" title="${isAdmin ? "Delete" : "Administrators only"}" data-action="delete" data-id="${claimId}" ${deleteDisabled}>
          <i class="fas fa-trash-alt"></i>
        </button>
      </div>
    `;
  }

  ClaimsTable.renderers = {
    failureTypeRenderer: labelRenderer(constants.FAILURE_TYPE_LABEL_MAP, "ct-badge--component"),
    failureClusterRenderer: labelRenderer(constants.FAILURE_CLUSTER_LABEL_MAP, "ct-badge--process"),
    claimTypeRenderer,
    statusRenderer,
    status8DRenderer,
    yesNoRenderer,
    moneyRenderer,
    supplierRenderer,
    dmcRenderer,
    claimedComponentsRenderer,
    actionsRenderer
  };
})(window);