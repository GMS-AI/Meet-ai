const $ = (id) => document.getElementById(id);
function setStatus(s){ $("status").textContent = s; }

async function sendToActiveTab(message) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) throw new Error("No active tab");
  return chrome.tabs.sendMessage(tab.id, message);
}

$("start").onclick = async () => {
  setStatus("starting… (open on the Meet tab)");
  try {
    const res = await sendToActiveTab({ type: "start_webrtc_cc" });
    if (res?.ok) {
      setStatus("streaming captions → backend");
      $("start").disabled = true;
      $("stop").disabled = true; // briefly
      setTimeout(() => $("stop").disabled = false, 800);
    } else {
      setStatus("failed to start: " + (res?.error || ""));
    }
  } catch (e) {
    setStatus("error: " + (e.message || e));
  }
};

$("stop").onclick = async () => {
  try {
    await sendToActiveTab({ type: "stop_webrtc_cc" });
    setStatus("stopped");
    $("start").disabled = false;
    $("stop").disabled = true;
  } catch (e) {
    setStatus("error: " + (e.message || e));
  }
};
