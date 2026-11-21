const fileInput = document.getElementById("video-file");
const startButton = document.getElementById("start-analysis");
const inputPreview = document.getElementById("input-preview");
const clearButton = document.getElementById("clear-video");
const uploadZone = document.querySelector(".upload-zone");
let selectedFile = null;
let previewUrl = null;
let pollTimer = null;
let pollingStopped = false;
let taskInProgress = false;

fileInput.addEventListener("change", () => {
  if (taskInProgress) return;
  selectFile(fileInput.files && fileInput.files[0] ? fileInput.files[0] : null);
});

function selectFile(file) {
  if (taskInProgress) return;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  selectedFile = file || null;
  startButton.disabled = !selectedFile;
  clearButton.hidden = !selectedFile;
  document.getElementById("file-meta").textContent = selectedFile
    ? `${selectedFile.name} · ${formatBytes(selectedFile.size)}`
    : "Chưa chọn tệp video nào.";
  if (selectedFile) {
    previewUrl = URL.createObjectURL(selectedFile);
    inputPreview.src = previewUrl;
    inputPreview.hidden = false;
  } else {
    inputPreview.removeAttribute("src");
    inputPreview.hidden = true;
  }
}

clearButton.addEventListener("click", () => {
  if (taskInProgress) return;
  fileInput.value = "";
  selectFile(null);
  setTaskStatus("Sẵn sàng. Vui lòng chọn video mới.", "queued");
});

if (uploadZone) {
  ["dragenter", "dragover"].forEach(name => uploadZone.addEventListener(name, event => {
    event.preventDefault();
  }));
  uploadZone.addEventListener("drop", event => {
    event.preventDefault();
    if (taskInProgress) return;
    const file = event.dataTransfer && event.dataTransfer.files ? event.dataTransfer.files[0] : null;
    if (file) {
      selectFile(file);
    }
  });
}

startButton.addEventListener("click", async () => {
  if (taskInProgress) return;
  if (!selectedFile) {
    showToast("Vui lòng chọn video trước khi bắt đầu.", true);
    return;
  }
  pollingStopped = false;
  if (pollTimer) window.clearTimeout(pollTimer);
  setTaskInProgress(true);
  setTaskStatus("Đang tải video lên hệ thống...", "queued");
  updateProgress(0, 0);
  try {
    const video = await ITSApi.uploadVideo(selectedFile);
    setTaskStatus("Tải video thành công. Đang khởi chạy nhận diện...", "queued");
    const task = await ITSApi.startDetection(video.id);
    setTaskStatus("Tác vụ đã được tiếp nhận. Đang chờ xử lý...", task.status);
    await pollTask(task.id);
  } catch (error) {
    setTaskStatus(error.message || "Tải video hoặc khởi chạy nhận diện thất bại.", "failed");
    document.getElementById("result-summary").textContent = "Không có kết quả do quá trình xử lý chưa thể bắt đầu.";
    showToast(error.message || "Upload thất bại.", true);
    setTaskInProgress(false);
  }
});

function setTaskInProgress(inProgress) {
  taskInProgress = inProgress;
  fileInput.disabled = inProgress;
  clearButton.disabled = inProgress;
  startButton.disabled = inProgress || !selectedFile;
  uploadZone.classList.toggle("is-disabled", inProgress);
  uploadZone.setAttribute("aria-disabled", String(inProgress));
  uploadZone.setAttribute("aria-busy", String(inProgress));
}

function setTaskStatus(message, status) {
  document.getElementById("task-message").textContent = message;
  const tag = document.getElementById("task-status");
  const normalized = String(status || "queued").toLowerCase();
  const labels = { queued: "Chờ xử lý", running: "Đang nhận diện", processing: "Đang nhận diện", completed: "Hoàn thành", failed: "Thất bại" };
  tag.textContent = labels[normalized] || "Sẵn sàng";
  tag.className = `tag ${normalized === "completed" ? "ok" : normalized === "failed" ? "danger" : "warn"}`;
  const steps = document.querySelectorAll(".workflow-step");
  const activeIndex = normalized === "completed" ? 4 : normalized === "failed" ? 3 : normalized === "running" ? 3 : normalized === "queued" ? 1 : 0;
  steps.forEach((step, index) => step.classList.toggle("active", index <= activeIndex));
}

function updateProgress(progress, frames, totalFrames) {
  const safeProgress = Math.max(0, Math.min(100, Number(progress) || 0));
  document.getElementById("task-progress").style.width = `${safeProgress}%`;
  document.getElementById("progress-value").textContent = `${safeProgress}%`;
  document.getElementById("frame-value").textContent = totalFrames
    ? `${Number(frames) || 0} / ${Number(totalFrames)} khung`
    : `${Number(frames) || 0} khung`;
}

async function pollTask(taskId) {
  let connectionFailures = 0;
  for (let attempt = 0; attempt < 301 && !pollingStopped; attempt++) {
    try {
      const task = await ITSApi.taskStatus(taskId);
      connectionFailures = 0;
      updateProgress(task.progress, task.current_frame, task.result && task.result.processed_frames);
      if (task.status === "completed") {
        setTaskStatus("Nhận diện đã hoàn thành.", "completed");
        await renderResult(task);
        setTaskInProgress(false);
        return;
      }
      if (task.status === "failed") {
        setTaskStatus(task.error || "Quá trình nhận diện thất bại.", "failed");
        document.getElementById("result-summary").textContent = task.error || "Không tạo được kết quả.";
        showToast(task.error || "Nhận diện thất bại.", true);
        setTaskInProgress(false);
        return;
      }
      setTaskStatus(task.status === "queued" ? "Đang chờ xử lý..." : "Đang nhận diện video...", task.status);
      await new Promise(resolve => { pollTimer = window.setTimeout(resolve, 1200); });
    } catch (error) {
      connectionFailures++;
      if (connectionFailures >= 5) {
        setTaskStatus("Mất kết nối API hoặc không thể truy cập tác vụ.", "failed");
        document.getElementById("result-summary").textContent = "Đã dừng theo dõi sau nhiều lần không thể kết nối.";
        showToast("Dừng polling do lỗi kết nối.", true);
        setTaskInProgress(false);
        return;
      }
      await new Promise(resolve => { pollTimer = window.setTimeout(resolve, 1200); });
    }
  }
  setTaskStatus("Đã dừng theo dõi tác vụ sau thời gian chờ.", "failed");
  setTaskInProgress(false);
}

async function renderResult(task) {
  const result = task.result || {};
  const warnings = Array.isArray(result.warnings) ? result.warnings : [];
  const scope = result.analysis_scope === "configured_lane_rules"
    ? "Đã áp dụng cấu hình làn đường và quy tắc chuyển làn"
    : result.analysis_scope === "detection_only"
      ? (Array.isArray(result.warnings) && result.warnings.some(warning => String(warning).includes("quy tắc chuyển làn"))
        ? "Đã cấu hình polygon làn; chưa có quy tắc chuyển làn cấm"
        : "Chỉ nhận diện; chưa có cấu hình làn đầy đủ")
      : (result.analysis_scope || "Không xác định");
  document.getElementById("result-summary").innerHTML = `
    <div><strong>Phương tiện theo dõi:</strong> ${Number(result.unique_tracked_vehicles || 0)}</div>
    <div><strong>Tổng lượt vi phạm:</strong> ${Number(result.violation_count || 0)}</div>
    <div><strong>Phạm vi phân tích:</strong> ${escapeHtml(scope)}</div>
    ${warnings.length ? `<div><strong>Cảnh báo:</strong> ${escapeHtml(warnings.join("; "))}</div>` : ""}`;
  const output = document.getElementById("output-video");
  if (!output) return;
  const videoUrl = `/api/detection/${encodeURIComponent(task.id)}/video`;
  output.hidden = true;
  try {
    const response = await fetch(videoUrl, { headers: { Range: "bytes=0-1023" } });
    if (!response.ok) throw new Error("Video kết quả chưa sẵn sàng.");
    output.onerror = null;
    output.src = videoUrl;
    output.hidden = false;
  } catch (error) {
    output.removeAttribute("src");
    output.hidden = true;
    showToast(error.message || "Không thể tải video kết quả.", true);
  }
}

window.addEventListener("beforeunload", () => {
  pollingStopped = true;
  if (pollTimer) window.clearTimeout(pollTimer);
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});
