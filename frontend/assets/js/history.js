function escapeHistory(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

async function loadHistory() {
  try {
    const [videos, violations] = await Promise.all([ITSApi.videos(), ITSApi.violations()]);
    document.getElementById("history-videos").innerHTML = videos.length ? videos.map(video => `
      <tr><td>${escapeHistory(video.original_filename)}</td><td>${formatDate(video.uploaded_at)}</td>
      <td>${statusTag(video.status)}</td><td>${video.processing_seconds == null ? "—" : `${video.processing_seconds.toFixed(2)} s`}</td>
      <td>${video.processed_frames}</td>
      <td>${video.vehicle_count}</td><td>${video.violation_count}</td></tr>`).join("")
      : '<tr><td colspan="7" class="empty-state">No video records yet.</td></tr>';
    document.getElementById("history-violations").innerHTML = violations.length ? violations.map(item => `
      <tr><td>#${item.track_id}</td><td>${escapeHistory(item.source_lane)} → ${escapeHistory(item.destination_lane)}</td>
      <td>${escapeHistory(item.video_id)}</td><td>${formatDate(item.detected_at)}</td></tr>`).join("")
      : '<tr><td colspan="4" class="empty-state">No violations have been recorded.</td></tr>';
  } catch (error) {
    showToast(error.message, true);
  }
}

loadHistory();
