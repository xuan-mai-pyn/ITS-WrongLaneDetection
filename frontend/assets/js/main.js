window.showToast = function (message, isError = false) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("visible");
  window.setTimeout(() => toast.classList.remove("visible"), 3600);
};

window.formatDate = function (value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
};

window.statusTag = function (status) {
  const safe = String(status || "unknown");
  return `<span class="tag ${safe}">${safe}</span>`;
};
