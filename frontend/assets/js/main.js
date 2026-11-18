document.addEventListener("DOMContentLoaded", () => {
  highlightActiveNav();
  initBackendHealthIndicator();
  updateHeaderClock();
});

function highlightActiveNav() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".sidebar a");
  navLinks.forEach((link) => {
    const href = link.getAttribute("href");
    if (href && (currentPath === href || currentPath.endsWith(href))) {
      link.classList.add("active");
    }
  });
}

function updateHeaderClock() {
  const clockEl = document.getElementById("header-clock");
  if (!clockEl) return;
  const renderTime = () => {
    clockEl.textContent = new Date().toLocaleString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };
  renderTime();
  setInterval(renderTime, 30000);
}

async function initBackendHealthIndicator() {
  const sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;

  const badge = document.createElement("div");
  badge.className = "backend-status-badge";
  badge.innerHTML = `<span class="status-dot" id="apiStatusDot"></span><span id="apiStatusText">Đang kiểm tra máy chủ...</span>`;
  sidebar.appendChild(badge);

  const dot = document.getElementById("apiStatusDot");
  const text = document.getElementById("apiStatusText");

  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      dot.classList.add("online");
      text.textContent = "Máy chủ API: Hoạt động";
    } else {
      throw new Error("Lỗi kết nối");
    }
  } catch (err) {
    dot.classList.add("offline");
    text.textContent = "Máy chủ API: Ngoại tuyến";
  }
}

function formatDate(isoString) {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleString("vi-VN");
  } catch (e) {
    return String(isoString);
  }
}

function statusTag(status) {
  const normalized = String(status || "pending").toLowerCase();
  if (normalized === "completed") {
    return `<span class="tag ok">Hoàn thành</span>`;
  }
  if (normalized === "processing" || normalized === "running") {
    return `<span class="tag warn">Đang xử lý</span>`;
  }
  if (normalized === "failed" || normalized === "error") {
    return `<span class="tag danger">Lỗi xử lý</span>`;
  }
  return `<span class="tag warn">Chờ xử lý</span>`;
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; z-index: 9999;
    padding: 12px 18px; border-radius: 8px; font-size: 0.9rem; font-weight: 500;
    color: #fff; background: ${isError ? "#dc2626" : "#16a34a"};
    box-shadow: 0 6px 16px rgba(0,0,0,0.18); opacity: 1; transition: opacity 0.3s ease;
  `;
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    toast.style.opacity = "0";
  }, 3500);
}
