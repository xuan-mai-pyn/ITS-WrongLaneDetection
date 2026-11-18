async function loadDashboard(notify = false) {
  try {
    const [stats, videos] = await Promise.all([
      ITSApi.statistics(),
      ITSApi.videos(),
    ]);

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

    if (notify) {
      showToast("Đã cập nhật dữ liệu mới nhất.");
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
