(function (window) {
  "use strict";

  const ClaimsTable = window.ClaimsTable = window.ClaimsTable || {};

  function notify(message, type = "info") {
    if (typeof window.showToast === "function") {
      window.showToast(message, type);
      return;
    }

    if (window.Swal) {
      Swal.fire({
        icon: type === "danger" ? "error" : type,
        title: message,
        timer: 2500,
        showConfirmButton: false
      });
    }
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char];
    });
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, "&#096;");
  }

  function fmtDate(value) {
    if (!value) return "";

    const date = new Date(String(value) + "T00:00:00");
    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleDateString("en-GB");
  }

  function fmtMoney(value) {
    const number = Number(value || 0);

    return number.toLocaleString("en-GB", {
      style: "currency",
      currency: "EUR"
    });
  }

  function normalizeDate(value) {
    if (!value) return null;

    const date = new Date(String(value) + "T00:00:00");
    if (Number.isNaN(date.getTime())) return null;

    date.setHours(0, 0, 0, 0);
    return date;
  }

  function getToday() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return today;
  }

  function dateIsBetween(value, from, to) {
    const date = normalizeDate(value);
    const fromDate = normalizeDate(from);
    const toDate = normalizeDate(to);

    if (!date) return false;
    if (fromDate && date < fromDate) return false;
    if (toDate && date > toDate) return false;

    return true;
  }

  function daysBetween(fromValue, toValue) {
    const from = normalizeDate(fromValue);
    const to = normalizeDate(toValue);

    if (!from || !to) return null;

    return Math.round((to.getTime() - from.getTime()) / 86400000);
  }

  ClaimsTable.utils = {
    notify,
    escapeHtml,
    escapeAttr,
    fmtDate,
    fmtMoney,
    normalizeDate,
    getToday,
    dateIsBetween,
    daysBetween
  };
})(window);