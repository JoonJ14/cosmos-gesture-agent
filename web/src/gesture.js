const KEY_TO_INTENT = {
  "1": "OPEN_MENU",
  "2": "CLOSE_MENU",
  "3": "SWITCH_RIGHT",
  "4": "SWITCH_LEFT",
};

export function createEventId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `evt-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function intentFromTestKey(key) {
  return KEY_TO_INTENT[key] || null;
}

export async function setupCamera(videoElement) {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 960, height: 540 },
    audio: false,
  });
  videoElement.srcObject = stream;
  await videoElement.play();
  return stream;
}

export function createHandsPipeline(onResults) {
  if (!window.Hands) {
    return null;
  }

  const hands = new window.Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
  });

  hands.setOptions({
    maxNumHands: 2,
    modelComplexity: 0,
    minDetectionConfidence: 0.6,
    minTrackingConfidence: 0.5,
  });

  hands.onResults(onResults);
  return hands;
}

export function startHandsCameraLoop(videoElement, hands) {
  if (!window.Camera || !hands) {
    return null;
  }

  const camera = new window.Camera(videoElement, {
    onFrame: async () => {
      await hands.send({ image: videoElement });
    },
    width: 960,
    height: 540,
  });

  camera.start();
  return camera;
}

// TODO: replace keyboard test triggers with gesture proposal logic based on landmarks.
// TODO: add temporal smoothing and deliberate-hold heuristics for OPEN_MENU and CLOSE_MENU.
// TODO: add directionality checks for SWITCH_RIGHT and SWITCH_LEFT.
export function proposeGestureFromLandmarks(_results) {
  return null;
}
