async function loadStatistics() {
  const breakdownContainer = document.getElementById("statistics-breakdown");
  if (breakdownContainer) breakdownContainer.innerHTML = '<p class="empty-state">Đang tải dữ liệu thống kê...</p>';
  try {
    const [stats, violations] = await Promise.all([
      ITSApi.statistics(),
      ITSApi.violations(),
    ]);

    document.getElementById("processed-videos").textContent = stats.processed_videos ?? 0;
    document.getElementById("total-vehicles").textContent = stats.total_vehicles ?? 0;
    document.getElementById("total-violations").textContent = stats.total_violations ?? 0;
    document.getElementById("detection-rate").textContent = `${Math.round((stats.detection_rate || 0) * 100)}%`;

    if (!breakdownContainer) return;

    const violationList = Array.isArray(violations) ? violations : [];
    if (!violationList.length) {
      breakdownContainer.innerHTML = '<p class="empty-state">Chưa có bản ghi vi phạm để phân bổ theo loại phương tiện.</p>';
      return;
    }

    const byVehicleType = violationList.reduce((acc, item) => {
      const key = String(item.vehicle_type || "unknown").toLowerCase();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});

    const entries = Object.entries(byVehicleType).sort((a, b) => b[1] - a[1]);
    const maxCount = Math.max(1, ...entries.map((entry) => entry[1]));

    breakdownContainer.innerHTML = `
      <div class="chart-container">
        ${entries
          .map(
            ([vehicleType, count]) => `
            <div class="chart-row stat-bar-row">
              <span class="chart-label">${escapeStatHtml(vehicleTypeName(vehicleType))}</span>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" style="width: ${(count / maxCount) * 100}%"></div>
              </div>
              <span class="chart-value">${count} lượt (${Math.round((count / violationList.length) * 100)}%)</span>
            </div>`
          )
          .join("")}
      </div>
      <p class="statistics-breakdown-note">
        Biểu đồ tổng hợp ${violationList.length} bản ghi vi phạm từ các video đã ghi nhận. Không phải tổng số phương tiện phát hiện theo loại.
      </p>`;
  } catch (error) {
    showToast(error.message, true);
    const breakdownContainer = document.getElementById("statistics-breakdown");
    if (breakdownContainer) {
      breakdownContainer.innerHTML = '<p class="empty-state">Không thể tải dữ liệu thống kê từ máy chủ API.</p>';
    }
  }
}

function escapeStatHtml(value) {
  const el = document.createElement("span");
  el.textContent = value ?? "";
  return el.innerHTML;
}

loadStatistics();
