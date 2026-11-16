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
  uploadVideo(fileOrFormData) {
    const body =
      fileOrFormData instanceof FormData ? fileOrFormData : new FormData();
    if (!(fileOrFormData instanceof FormData) && fileOrFormData) {
      body.append("file", fileOrFormData);
    }
    return requestJson("/api/videos/upload", {
      method: "POST",
      body,
    });
  },
  startDetection(videoIdOrPayload) {
    const body =
      typeof videoIdOrPayload === "object" && videoIdOrPayload !== null
        ? videoIdOrPayload
        : { video_id: videoIdOrPayload };
    return requestJson("/api/detection/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },
  taskStatus(taskId) {
    return requestJson(`/api/detection/${encodeURIComponent(taskId)}/status`);
  },
  detectionStatus(taskId) {
    return this.taskStatus(taskId);
  },
};
