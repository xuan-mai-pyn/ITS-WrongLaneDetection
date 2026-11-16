async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  let payload = null;
  try {
    payload = await response.json();
  } catch (e) {
    payload = null;
  }

  if (!response.ok) {
    const errorMessage =
      (payload && (payload.detail || payload.message)) ||
      `Lỗi máy chủ (${response.status})`;
    throw new Error(errorMessage);
  }
  return payload;
}

window.ITSApi = {
  health() {
    return requestJson("/api/health");
  },
  statistics() {
    return requestJson("/api/statistics");
  },
  videos() {
    return requestJson("/api/videos");
  },
  violations() {
    return requestJson("/api/violations");
  },
  uploadVideo(formData) {
    return requestJson("/api/videos/upload", {
      method: "POST",
      body: formData,
    });
  },
  startDetection(payload) {
    return requestJson("/api/detection/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  detectionStatus(taskId) {
    return requestJson(`/api/detection/${encodeURIComponent(taskId)}/status`);
  },
};
