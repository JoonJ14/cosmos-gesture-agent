export function syncOverlaySize(videoElement, canvasElement) {
  const width = videoElement.videoWidth || videoElement.clientWidth || 960;
  const height = videoElement.videoHeight || videoElement.clientHeight || 540;
  canvasElement.width = width;
  canvasElement.height = height;
}

export function drawHandsOverlay(canvasElement, results) {
  const ctx = canvasElement.getContext("2d");
  const width = canvasElement.width;
  const height = canvasElement.height;

  ctx.save();
  ctx.clearRect(0, 0, width, height);

  if (results?.multiHandLandmarks?.length) {
    for (const landmarks of results.multiHandLandmarks) {
      if (window.drawConnectors && window.HAND_CONNECTIONS) {
        window.drawConnectors(ctx, landmarks, window.HAND_CONNECTIONS, {
          color: "#22c55e",
          lineWidth: 2,
        });
      }
      if (window.drawLandmarks) {
        window.drawLandmarks(ctx, landmarks, {
          color: "#e5e7eb",
          lineWidth: 1,
          radius: 2,
        });
      }
    }
  }

  ctx.restore();
}
