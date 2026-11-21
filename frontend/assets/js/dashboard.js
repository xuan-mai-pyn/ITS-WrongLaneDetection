async function loadDashboard(notify = false) {
  try {
    const [statsResult, videosResult, healthResult] = await Promise.allSettled([
      ITSApi.statistics(),
      ITSApi.videos(),
      ITSApi.health(),
    ]);
    if (statsResult.status === "rejected" || videosResult.status === "rejected") {
      throw new Error(
        statsResult.status === "rejected"
          ? statsResult.reason.message
          : videosResult.reason.message
      );
    }
    const stats = statsResult.value;
    const videos = videosResult.value;
    const health = healthResult.status === "fulfilled" ? healthResult.value : null;

    document.getElementById("processed-videos").textContent = stats.processed_videos ?? 0;
    document.getElementById("total-vehicles").textContent = stats.total_vehicles ?? 0;
    document.getElementById("total-violations").textContent = stats.total_violations ?? 0;
    document.getElementById("detection-rate").textContent = `${Math.round((stats.detection_rate || 0) * 100)}%`;

    const measures = [
      ["Video đã xử lý", stats.processed_videos ?? 0],
      ["Phương tiện theo dõi", stats.total_vehicles ?? 0],
      ["Vi phạm ghi nhận", stats.total_violations ?? 0],
    ];
    const maximum = Math.max(1, ...measures.map((item) => item[1]));

    document.getElementById("dashboard-chart").innerHTML = `
      <div class="chart-container">
        ${measures
          .map(
            ([label, value]) => `
            <div class="chart-row">
              <span class="chart-label">${label}</span>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" style="width: ${(value / maximum) * 100}%"></div>
              </div>
              <span class="chart-value">${value}</span>
            </div>`
          )
          .join("")}
      </div>`;

    const rows = (videos || []).slice(0, 6);
    document.getElementById("recent-videos").innerHTML = rows.length
      ? rows
          .map(
            (video) => `
            <tr>
              <td>${escapeHtml(video.original_filename)}</td>
              <td>${formatDate(video.uploaded_at)}</td>
              <td>${statusTag(video.status)}</td>
              <td>${video.vehicle_count ?? 0}</td>
              <td>${video.violation_count ?? 0}</td>
            </tr>`
          )
          .join("")
      : '<tr><td colspan="5" class="empty-state">Chưa có video nào được tải lên hệ thống.</td></tr>';

    if (health) renderSystemHealth(health);
    else {
      const container = document.getElementById("system-health");
      const badge = document.getElementById("system-health-badge");
      if (container) container.innerHTML = '<div class="empty-state">Không thể tải trạng thái hệ thống.</div>';
      if (badge) {
        badge.textContent = "Ngoại tuyến";
        badge.className = "tag danger";
      }
    }

    if (notify) {
      showToast("Đã cập nhật dữ liệu mới nhất.");
    }

    function renderSystemHealth(health) {
      const container = document.getElementById("system-health");
      const badge = document.getElementById("system-health-badge");
      if (!container) return;
      const dbOk = String(health.database || "").toLowerCase() === "connected";
      const modelOk = Boolean(health.model_ready);
      const laneOk = Boolean(health.lane_config_ready);
      const ready = dbOk && modelOk && laneOk;
      if (badge) {
        badge.textContent = ready ? "Sẵn sàng đầy đủ" : "Cần kiểm tra";
        badge.className = `tag ${ready ? "ok" : "warn"}`;
      }
      container.innerHTML = `
        <div class="health-item"><span>API máy chủ</span><strong class="ok">Hoạt động</strong></div>
        <div class="health-item"><span>Cơ sở dữ liệu</span><strong class="${dbOk ? "ok" : "bad"}">${dbOk ? "Đã kết nối" : "Không kết nối"}</strong></div>
        <div class="health-item"><span>Mô hình YOLO</span><strong class="${modelOk ? "ok" : "bad"}">${modelOk ? "Sẵn sàng" : "Chưa sẵn sàng"}</strong></div>
        <div class="health-item"><span>Cấu hình làn đường</span><strong class="${laneOk ? "ok" : "bad"}">${laneOk ? "Đã cấu hình" : "Chưa cấu hình"}</strong></div>`;
      if (Array.isArray(health.warnings) && health.warnings.length) {
        container.insertAdjacentHTML(
          "beforeend",
          `<div class="health-item health-warning">
            <span>Cảnh báo</span>
            <ul>${health.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>
          </div>`
        );
      }
    }
  } catch (error) {
    showToast(error.message, true);
    document.getElementById("recent-videos").innerHTML =
      '<tr><td colspan="5" class="empty-state">Không thể tải dữ liệu từ máy chủ API.</td></tr>';
  }
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("refresh-dashboard");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => loadDashboard(true));
  }
  loadDashboard(false);
});
