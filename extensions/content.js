// content.js — observe Meet captions and send them over WebRTC DataChannel "cc"

let pc = null;
let dc = null;
let webrtcReady = false;

// ------- WebRTC (signaling with backend) -------
async function startWebRTC() {
  if (webrtcReady) return;
  pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });

  dc = pc.createDataChannel("cc", { ordered: true });
  dc.onopen = () => {
    console.log("[CC-WebRTC] datachannel open");
    webrtcReady = true;
  };
  dc.onclose = () => {
    console.log("[CC-WebRTC] datachannel closed");
    webrtcReady = false;
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const res = await fetch("http://127.0.0.1:8765/webrtc/offer", {
    method: "POST",
    headers: { "Content-Type": "application/sdp" },
    body: offer.sdp
  });
  const answerSDP = await res.text();
  await pc.setRemoteDescription({ type: "answer", sdp: answerSDP });

  console.log("[CC-WebRTC] connected");
}

function stopWebRTC() {
  try { dc && dc.close(); } catch {}
  try { pc && pc.close(); } catch {}
  pc = null; dc = null; webrtcReady = false;
}

function sendCaptionLine(speaker, text) {
  if (dc && dc.readyState === "open") {
    dc.send(JSON.stringify({ speaker, text, ts: Date.now() }));
  }
}

// ------- Caption watcher (DOM) -------
const mutationConfig = { childList: true, attributes: true, subtree: true, characterData: true };
let canUseAriaBasedTranscriptSelector = true;
let transcriptObserver = null;

// small throttle to avoid spam
const MIN_CHARS_DELTA = 40;
const MIN_MS_DELTA = 1500;
const perSpeakerState = {}; // { [speaker]: { lastLen, lastAt, lastSentText } }

function maybeSendThrottled(speaker, text, force=false) {
  speaker = speaker || "Unknown";
  text = (text || "").trim();
  if (!text) return;

  const now = Date.now();
  const st = perSpeakerState[speaker] || { lastLen: 0, lastAt: 0, lastSentText: "" };
  const len = text.length;
  const grew = len - st.lastLen;
  const dt = now - st.lastAt;

  if (force || grew >= MIN_CHARS_DELTA || dt >= MIN_MS_DELTA) {
    if (text !== st.lastSentText) {
      sendCaptionLine(speaker, text);
      perSpeakerState[speaker] = { lastLen: len, lastAt: now, lastSentText: text };
    }
  }
}

function transcriptMutationCallback() {
  try {
    const people =
      canUseAriaBasedTranscriptSelector
        ? document.querySelector(`div[role="region"][tabindex="0"]`)?.children
        : document.querySelector(".a4cQT")?.childNodes[1]?.firstChild?.childNodes;

    if (!people) return;

    // In ARIA case, the last child is "Jump to bottom", so real last person is -2
    const idx = canUseAriaBasedTranscriptSelector ? (people.length - 2) : (people.length - 1);
    if (idx < 0) return;

    const person = people[idx];
    const currentPersonName = person?.childNodes?.[0]?.textContent || "Unknown";
    const currentTranscriptText = person?.childNodes?.[1]?.textContent || "";

    if (!currentTranscriptText) return;

    maybeSendThrottled(currentPersonName, currentTranscriptText, false);
  } catch (e) {
    console.error("[CC-WebRTC] mutation error", e);
  }
}

async function startCaptionObserver() {
  // Wait for transcript container to exist
  const waitForElement = async (selector) => {
    while (!document.querySelector(selector)) {
      await new Promise(r => requestAnimationFrame(r));
    }
    return document.querySelector(selector);
  };

  let transcriptTargetNode = await waitForElement(`div[role="region"][tabindex="0"]`);
  if (!transcriptTargetNode) {
    // fallback (older UI)
    transcriptTargetNode = document.querySelector(".a4cQT");
    canUseAriaBasedTranscriptSelector = false;
  }

  if (!transcriptTargetNode) {
    console.warn("[CC-WebRTC] transcript node not found");
    return;
  }

  // Dim captions panel a bit so you know it's hooked (optional)
  try {
    transcriptTargetNode.setAttribute("style", "opacity:0.2");
  } catch {}

  transcriptObserver = new MutationObserver(transcriptMutationCallback);
  transcriptObserver.observe(transcriptTargetNode, mutationConfig);
  console.log("[CC-WebRTC] transcript observer attached");
}

// ------- Messaging from popup -------
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "start_webrtc_cc") {
    startWebRTC().then(() => startCaptionObserver()).then(() => {
      sendResponse({ ok: true });
    }).catch(err => {
      console.error(err);
      sendResponse({ ok: false, error: String(err) });
    });
    return true; // async response
  }
  if (msg?.type === "stop_webrtc_cc") {
    try { transcriptObserver && transcriptObserver.disconnect(); } catch {}
    stopWebRTC();
    sendResponse({ ok: true });
  }
});
