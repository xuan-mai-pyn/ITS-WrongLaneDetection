let cachedViolations = [];

function escapeHistory(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

function renderViolationsTable(violations) {
  const tbody = document.getElementById("history-violations");
  if (!tbody) return;

  tbody.innerHTML = violations.length
    ? violations
        .map(
          (item) => `
          <tr>
            <td>#${item.track_id}</td>
            <td>${escapeHistory(item.video_id)}</td>
            <td><strong>${escapeHistory(item.vehicle_type || "Phương tiện")}</strong></td>
            <td><span class="tag danger">${escapeHistory(item.source_lane)} &rarr; ${escapeHistory(item.destination_lane)}</span></td>
            <td>${typeof formatDate === "function" ? formatDate(item.detected_at) : escapeHistory(item.detected_at)}</td>
          </tr>`
        )
        .join("")
    : '<tr><td colspan="5" class="empty-state">Không tìm thấy bản ghi vi phạm phù hợp.</td></tr>';
}

function initHistoryFilters() {
  const searchInput = document.getElementById("history-search");
  const filterSelect = document.getElementById("history-vehicle-filter");
  if (!searchInput && !filterSelect) return;

  const applyFilters = () => {
    const keyword = (searchInput ? searchInput.value : "").trim().toLowerCase();
    const selected = filterSelect ? filterSelect.value.toLowerCase() : "all";

    const filtered = cachedViolations.filter((item) => {
      const trackStr = String(item.track_id ?? "").toLowerCase();
      const videoStr = String(item.video_id ?? "").toLowerCase();
      const laneStr = `${item.source_lane ?? ""} ${item.destination_lane ?? ""}`.toLowerCase();
      const typeStr = String(item.vehicle_type ?? "").toLowerCase();

      const matchKeyword =
        !keyword ||
        trackStr.includes(keyword) ||
        videoStr.includes(keyword) ||
        laneStr.includes(keyword);
      const matchType = selected === "all" || !typeStr || typeStr.includes(selected);

      return matchKeyword && matchType;
    });

    renderViolationsTable(filtered);
  };

  if (searchInput) searchInput.addEventListener("input", applyFilters);
  if (filterSelect) filterSelect.addEventListener("change", applyFilters);
}

async function loadHistory() {
  try {
    const [videos, violations] = await Promise.all([
      ITSApi.videos(),
      ITSApi.violations(),
    ]);

    document.getElementById("history-videos").innerHTML = videos.length
      ? videos
          .map(
            (video) => `
            <tr>
              <td>${escapeHistory(video.original_filename)}</td>
              <td>${typeof formatDate === "function" ? formatDate(video.uploaded_at) : escapeHistory(video.uploaded_at)}</td>
              <td>${typeof statusTag === "function" ? statusTag(video.status) : escapeHistory(video.status)}</td>
              <td>${video.processing_seconds == null ? "—" : `${video.processing_seconds.toFixed(2)} s`}</td>
              <td>${video.processed_frames}</td>
              <td>${video.vehicle_count}</td>
              <td>${video.violation_count}</td>
            </tr>`
          )
          .join("")
      : '<tr><td colspan="7" class="empty-state">Chưa có video nào được ghi nhận.</td></tr>';

    cachedViolations = violations || [];
    renderViolationsTable(cachedViolations);
  } catch (error) {
    if (typeof showToast === "function") {
      showToast(error.message, true);
    } else {
      console.error(error);
    }
  }
}

initHistoryFilters();
loadHistory();
