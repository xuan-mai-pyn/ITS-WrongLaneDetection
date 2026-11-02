async function loadDashboard() {
  try {
    const [stats, videos] = await Promise.all([ITSApi.statistics(), ITSApi.videos()]);
    document.getElementById("processed-videos").textContent = stats.processed_videos;
    document.getElementById("total-vehicles").textContent = stats.total_vehicles;
    document.getElementById("total-violations").textContent = stats.total_violations;
    document.getElementById("detection-rate").textContent = `${Math.round(stats.detection_rate * 100)}%`;
    const measures = [
      ["Processed videos", stats.processed_videos],
      ["Tracked vehicles", stats.total_vehicles],
      ["Recorded violations", stats.total_violations]
    ];
    const maximum = Math.max(1, ...measures.map(item => item[1]));
    document.getElementById("dashboard-chart").innerHTML = measures.map(([label, value]) => `
      <div class="bar-row"><span>${label}</span><div class="bar-track"><div class="bar-fill" style="width:${value / maximum * 100}%"></div></div><strong>${value}</strong></div>`).join("");
    const rows = videos.slice(0, 6);
    document.getElementById("recent-videos").innerHTML = rows.length ? rows.map(video => `
      <tr><td>${escapeHtml(video.original_filename)}</td><td>${formatDate(video.uploaded_at)}</td>
      <td>${statusTag(video.status)}</td><td>${video.vehicle_count}</td><td>${video.violation_count}</td></tr>`).join("")
      : '<tr><td colspan="5" class="empty-state">No videos have been uploaded.</td></tr>';
  } catch (error) {
    showToast(error.message, true);
    document.getElementById("recent-videos").innerHTML = '<tr><td colspan="5" class="empty-state">Could not load API data.</td></tr>';
  }
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

loadDashboard();
