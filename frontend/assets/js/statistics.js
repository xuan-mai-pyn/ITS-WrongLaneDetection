async function loadStatistics() {
  try {
    const [stats, violations, videos] = await Promise.all([
      ITSApi.statistics(),
      ITSApi.violations(),
      ITSApi.videos(),
    ]);

    document.getElementById("processed-videos").textContent = stats.processed_videos ?? 0;
    document.getElementById("total-vehicles").textContent = stats.total_vehicles ?? 0;
    document.getElementById("total-violations").textContent = stats.total_violations ?? 0;
    document.getElementById("detection-rate").textContent = `${Math.round((stats.detection_rate || 0) * 100)}%`;

    const breakdownContainer = document.getElementById("statistics-breakdown");
    if (!breakdownContainer) return;

    const violationList = Array.isArray(violations) ? violations : [];
    if (!violationList.length) {
      const fallbackMetrics = [
        ["Video đã xử lý", stats.processed_videos ?? 0],
        ["Tổng phương tiện nhận diện", stats.total_vehicles ?? 0],
        ["Tổng lượt vi phạm sai làn", stats.total_violations ?? 0],
      ];
      const maxFallback = Math.max(1, ...fallbackMetrics.map((item) => item[1]));
      breakdownContainer.innerHTML = `
        <div class="chart-container">
          ${fallbackMetrics
            .map(
              ([label, value]) => `
              <div class="chart-row">
                <span class="chart-label">${label}</span>
                <div class="chart-bar-bg">
                  <div class="chart-bar-fill" style="width: ${(value / maxFallback) * 100}%"></div>
                </div>
                <span class="chart-value">${value}</span>
              </div>`
            )
            .join("")}
        </div>`;
      return;
    }

    const byVehicleType = violationList.reduce((acc, item) => {
      const key = (item.vehicle_type || "unknown").toUpperCase();
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
            <div class="chart-row">
              <span class="chart-label">${escapeStatHtml(vehicleType)}</span>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" style="width: ${(count / maxCount) * 100}%"></div>
              </div>
              <span class="chart-value">${count} lượt (${Math.round((count / violationList.length) * 100)}%)</span>
            </div>`
          )
          .join("")}
      </div>
      <p class="subtitle" style="margin-top: 12px;">
        Tổng hợp từ ${violationList.length} bản ghi vi phạm trên ${(videos || []).length} video trong hệ thống.
      </p>`;
  } catch (error) {
    showToast(error.message, true);
    const breakdownContainer = document.getElementById("statistics-breakdown");
    if (breakdownContainer) {
      breakdownContainer.innerHTML = '<p class="empty-state">Could not load API data.</p>';
    }
  }
}

function escapeStatHtml(value) {
  const el = document.createElement("span");
  el.textContent = value ?? "";
  return el.innerHTML;
}

loadStatistics();
