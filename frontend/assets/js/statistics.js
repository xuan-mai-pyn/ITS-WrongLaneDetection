async function loadStatistics() {
  try {
    const stats = await ITSApi.statistics();
    document.getElementById("processed-videos").textContent = stats.processed_videos;
    document.getElementById("total-vehicles").textContent = stats.total_vehicles;
    document.getElementById("total-violations").textContent = stats.total_violations;
    document.getElementById("detection-rate").textContent = `${Math.round(stats.detection_rate * 100)}%`;
    const items = [
      ["Uploaded videos", stats.total_videos],
      ["Completed videos", stats.processed_videos],
      ["Tracked vehicles", stats.total_vehicles],
      ["Recorded violations", stats.total_violations],
      ...Object.entries(stats.vehicle_types || {}).map(([label, count]) => [`Vehicles: ${label}`, count])
    ];
    const maximum = Math.max(1, ...items.map(item => item[1]));
    document.getElementById("statistics-breakdown").innerHTML = items.map(([label, value]) => `
      <div class="bar-row"><span>${escapeStatistics(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${value / maximum * 100}%"></div></div><strong>${value}</strong></div>`).join("");
  } catch (error) {
    showToast(error.message, true);
    document.getElementById("statistics-breakdown").innerHTML = '<p class="empty-state">Could not load statistics.</p>';
  }
}

function escapeStatistics(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

loadStatistics();
