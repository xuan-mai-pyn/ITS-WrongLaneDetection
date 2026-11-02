const fileInput = document.getElementById("video-file");
const startButton = document.getElementById("start-analysis");
const inputPreview = document.getElementById("input-preview");
let selectedFile = null;
let previewUrl = null;

fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
  startButton.disabled = !selectedFile;
  document.getElementById("file-meta").textContent = selectedFile
    ? `${selectedFile.name} · ${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB`
    : "";
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  if (selectedFile) {
    previewUrl = URL.createObjectURL(selectedFile);
    inputPreview.src = previewUrl;
    inputPreview.hidden = false;
  } else {
    inputPreview.hidden = true;
  }
});

startButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  startButton.disabled = true;
  setTaskStatus("Uploading video…", "queued");
  try {
    const video = await ITSApi.uploadVideo(selectedFile);
    const task = await ITSApi.startDetection(video.id);
    setTaskStatus("Task accepted. Waiting for the processing worker…", task.status);
    await pollTask(task.id);
  } catch (error) {
    setTaskStatus(error.message, "failed");
    showToast(error.message, true);
    startButton.disabled = false;
  }
});

function setTaskStatus(message, status) {
  document.getElementById("task-message").textContent = message;
  const tag = document.getElementById("task-status");
  tag.textContent = status;
  tag.className = `tag ${status}`;
}

async function pollTask(taskId) {
  try {
    while (true) {
      const task = await ITSApi.taskStatus(taskId);
      document.getElementById("task-progress").style.width = `${task.progress}%`;
      document.getElementById("progress-value").textContent = `${task.progress}%`;
      document.getElementById("frame-value").textContent = `${task.current_frame} frames`;
      if (task.status === "completed") {
        setTaskStatus("Processing completed.", task.status);
        const warnings = task.result && task.result.warnings ? task.result.warnings.join("\n") : "";
        document.getElementById("result-summary").textContent =
          `Tracked vehicles: ${task.result.unique_tracked_vehicles}\n` +
          `Recorded violations: ${task.result.violation_count}\n` +
          `Analysis scope: ${task.result.analysis_scope}\n${warnings}`;
        const output = document.getElementById("output-video");
        output.src = `/api/detection/${encodeURIComponent(taskId)}/video`;
        output.hidden = false;
        startButton.disabled = false;
        return;
      }
      if (task.status === "failed") {
        setTaskStatus(task.error || "Processing failed.", task.status);
        document.getElementById("result-summary").textContent = task.error || "No result was produced.";
        startButton.disabled = false;
        return;
      }
      setTaskStatus(`Processing video: ${task.progress}%`, task.status);
      await new Promise(resolve => window.setTimeout(resolve, 1200));
    }
  } catch (error) {
    setTaskStatus(error.message, "failed");
    showToast(error.message, true);
    startButton.disabled = false;
  }
}
