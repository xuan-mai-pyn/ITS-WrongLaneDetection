/* Thin REST client shared by the dashboard pages. */
window.ITSApi = {
  async request(path, options = {}) {
    const response = await fetch(path, options);
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
      const message = body && body.detail ? body.detail : `Request failed (${response.status}).`;
      throw new Error(message);
    }
    return body;
  },
  statistics() { return this.request("/api/statistics"); },
  videos() { return this.request("/api/videos"); },
  violations() { return this.request("/api/violations"); },
  startDetection(videoId) {
    return this.request("/api/detection/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId })
    });
  },
  uploadVideo(file) {
    const form = new FormData();
    form.append("file", file);
    return this.request("/api/videos/upload", { method: "POST", body: form });
  },
  taskStatus(taskId) { return this.request(`/api/detection/${encodeURIComponent(taskId)}/status`); }
};
