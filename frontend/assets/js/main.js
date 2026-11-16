document.addEventListener("DOMContentLoaded", () => {
  highlightActiveNav();
  initBackendHealthIndicator();
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

async function initBackendHealthIndicator() {
  const sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;

  const badge = document.createElement("div");
  badge.className = "backend-status-badge";
  badge.innerHTML = `<span class="status-dot" id="apiStatusDot"></span><span id="apiStatusText">Đang kiểm tra API...</span>`;
  sidebar.appendChild(badge);

  const dot = document.getElementById("apiStatusDot");
  const text = document.getElementById("apiStatusText");

  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      dot.classList.add("online");
      text.textContent = "Backend API: Online";
    } else {
      throw new Error("Non-200 response");
    }
  } catch (err) {
    dot.classList.add("offline");
    text.textContent = "Backend API: Offline";
  }
}
