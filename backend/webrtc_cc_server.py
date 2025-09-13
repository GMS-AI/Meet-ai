# # working code 
# import json
# import time
# from typing import List

# from fastapi import FastAPI, Request, Response
# from fastapi.middleware.cors import CORSMiddleware
# from aiortc import RTCPeerConnection, RTCSessionDescription

# # ----------------- FastAPI app -----------------
# app = FastAPI(title="Meet CC → WebRTC (captions only)")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], allow_credentials=True,
#     allow_methods=["*"], allow_headers=["*"],
# )

# # ----------------- transcript store -----------------
# _lines: List[str] = []
# _last_ts = 0

# def add_line(speaker: str | None, text: str | None):
#     global _last_ts
#     txt = (text or "").strip()
#     if not txt:
#         return
#     spk = (speaker or "Unknown").strip() or "Unknown"
#     _lines.append(f"{spk}: {txt}")
#     if len(_lines) > 4000:
#         del _lines[:-4000]
#     _last_ts = int(time.time() * 1000)

# # ----------------- routes -----------------
# @app.post("/webrtc/offer")
# async def webrtc_offer(req: Request):
#     """
#     Signaling endpoint: accepts SDP offer (text/plain or application/sdp),
#     returns SDP answer as raw SDP (NOT JSON).
#     """
#     sdp = (await req.body()).decode("utf-8", errors="ignore")
#     pc = RTCPeerConnection()

#     @pc.on("datachannel")
#     def on_datachannel(dc):
#         if dc.label == "cc":
#             @dc.on("message")
#             def on_message(msg):
#                 try:
#                     data = json.loads(msg)
#                     add_line(data.get("speaker"), data.get("text"))
#                 except Exception:
#                     pass

#     await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
#     answer = await pc.createAnswer()
#     await pc.setLocalDescription(answer)

#     # Return RAW SDP so the browser can setRemoteDescription successfully
#     return Response(content=pc.localDescription.sdp, media_type="application/sdp")

# @app.get("/transcript")
# def transcript(max_chars: int = 20000):
#     text = "\n".join(_lines[-1000:])
#     fresh = (int(time.time() * 1000) - _last_ts) < 2500
#     return {"text": text[-max_chars:], "fresh": fresh}


# 2nd woorking transcription
# import json
# import time
# import traceback
# from typing import List

# from fastapi import FastAPI, Request, Response, Body, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from aiortc import RTCPeerConnection, RTCSessionDescription

# app = FastAPI(title="Meet CC → WebRTC (captions only)")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], allow_credentials=True,
#     allow_methods=["*"], allow_headers=["*"],
# )

# # ----------------- transcript store -----------------
# _lines: List[str] = []
# _last_ts = 0

# # def add_line(speaker: str | None, text: str | None):
# #     global _last_ts
# #     txt = (text or "").strip()
# #     if not txt:
# #         return
# #     spk = (speaker or "Unknown").strip() or "Unknown"
# #     _lines.append(f"{spk}: {txt}")
# #     if len(_lines) > 4000:
# #         del _lines[:-4000]
# #     _last_ts = int(time.time() * 1000)

# # working
# def add_line(speaker: str | None, text: str | None):
#     global _last_ts
#     txt = (text or "").strip()
#     if not txt:
#         return
#     spk = (speaker or "Unknown").strip() or "Unknown"
#     line = f"{spk}: {txt}"

#     # if last line is same speaker, replace it instead of appending
#     if _lines and _lines[-1].startswith(spk + ":"):
#         _lines[-1] = line
#     else:
#         _lines.append(line)

#     if len(_lines) > 4000:
#         del _lines[:-4000]
#     _last_ts = int(time.time() * 1000)

# # ----------------- helpers -----------------
# def _pc_for_captions():
#     pc = RTCPeerConnection()

#     @pc.on("datachannel")
#     def on_datachannel(dc):
#         if dc.label == "cc":
#             @dc.on("message")
#             def on_message(msg):
#                 try:
#                     data = json.loads(msg)
#                     add_line(data.get("speaker"), data.get("text"))
#                 except Exception:
#                     # swallow malformed frames
#                     pass
#     return pc

# # ----------------- routes -----------------
# @app.get("/health")
# def health():
#     return {"ok": True}

# @app.get("/transcript")
# def transcript(max_chars: int = 20000):
#     text = "\n".join(_lines[-1000:])
#     fresh = (int(time.time() * 1000) - _last_ts) < 2500
#     return {"text": text[-max_chars:], "fresh": fresh}

# # RAW SDP signaling (browser sends offer.sdp as text)
# @app.post("/webrtc/offer")
# async def webrtc_offer(req: Request):
#     try:
#         sdp = (await req.body()).decode("utf-8", errors="ignore")
#         pc = _pc_for_captions()
#         await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
#         answer = await pc.createAnswer()
#         await pc.setLocalDescription(answer)
#         return Response(content=pc.localDescription.sdp, media_type="application/sdp")
#     except Exception as e:
#         traceback.print_exc()
#         # Return a readable error to client
#         raise HTTPException(status_code=400, detail=f"Invalid SDP offer: {e}")

# # JSON signaling (safer; browser sends {type,sdp})
# @app.post("/webrtc/offer_json")
# async def webrtc_offer_json(payload: dict = Body(...)):
#     """
#     Expected payload:
#     { "type": "offer", "sdp": "<full offer SDP from RTCPeerConnection.createOffer()>" }
#     Returns:
#     { "type": "answer", "sdp": "<answer sdp>" }
#     """
#     try:
#         offer_type = payload.get("type")
#         offer_sdp = payload.get("sdp")
#         if offer_type != "offer" or not offer_sdp:
#             raise ValueError("Payload must include type='offer' and a non-empty sdp")

#         pc = _pc_for_captions()
#         await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
#         answer = await pc.createAnswer()
#         await pc.setLocalDescription(answer)
#         return {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
#     except Exception as e:
#         traceback.print_exc()
#         raise HTTPException(status_code=400, detail=f"Invalid JSON offer: {e}")


# 3 parsing (convo)
# import json
# import time
# import traceback
# from typing import List, Dict
# import os
# from fastapi import FastAPI, Request, Response, Body, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from aiortc import RTCPeerConnection, RTCSessionDescription

# # ----------------- app setup -----------------
# app = FastAPI(title="Meet CC → WebRTC (captions only)")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ----------------- transcript store -----------------
# _conversation: List[Dict[str, str]] = []   # [{ "speaker": "You", "text": "..." }]
# _last_ts = 0


# def add_line(speaker: str | None, text: str | None):
#     """
#     Store structured conversation: merge text if same speaker continues.
#     """
#     global _last_ts
#     txt = (text or "").strip()
#     if not txt:
#         return
#     spk = (speaker or "Unknown").strip() or "Unknown"

#     # Merge with last speaker if same
#     if _conversation and _conversation[-1]["speaker"].lower() == spk.lower():
#         _conversation[-1]["text"] += " " + txt
#     else:
#         _conversation.append({"speaker": spk, "text": txt})

#     # keep buffer size reasonable
#     if len(_conversation) > 4000:
#         del _conversation[:-4000]

#     _last_ts = int(time.time() * 1000)

# def _cooldown_or_raise(action: str):
#     """
#     Hard server-side gate:
#     - If called too soon, DO NOT forward to Gemini.
#     - Return 429 to the client so quotas aren't consumed.
#     """
#     now = time.time()
#     gap = now - _last_call_at[action]
#     if gap < LLM_COOLDOWN_SEC:
#         left = int(LLM_COOLDOWN_SEC - gap)
#         # IMPORTANT: we return 429 before calling Gemini — nothing upstream is hit.
#         raise HTTPException(
#             status_code=429,
#             detail=f"Cooldown in effect ({LLM_COOLDOWN_SEC}s). Try again in ~{left}s. "
#                    "No Gemini call was made."
#         )
#     _last_call_at[action] = now

# # ----------------- helpers -----------------
# def _pc_for_captions():
#     pc = RTCPeerConnection()

#     @pc.on("datachannel")
#     def on_datachannel(dc):
#         if dc.label == "cc":
#             print("[DEBUG] Datachannel 'cc' opened")

#             @dc.on("message")
#             def on_message(msg):
#                 try:
#                     data = json.loads(msg)
#                     speaker = data.get("speaker")
#                     text = data.get("text")
#                     add_line(speaker, text)
#                     print(f"[DEBUG] Added: {speaker}: {text}")
#                 except Exception as e:
#                     print("[ERROR] Failed to process CC message:", e)
#                     traceback.print_exc()

#     return pc


# # ----------------- routes -----------------
# @app.get("/health")
# def health():
#     return {"ok": True}


# @app.get("/transcript")
# def transcript(max_chars: int = 20000):
#     """
#     Returns structured transcript:
#     {
#       "conversation": [
#         { "speaker": "Niharika Rindhe", "text": "Hello, I am Niharika..." },
#         { "speaker": "You", "text": "Hi, nice to meet you" }
#       ],
#       "fresh": true
#     }
#     """
#     conv = _conversation[-1000:]  # recent blocks
#     total = 0
#     result = []

#     # enforce max_chars (approx by text length)
#     for block in reversed(conv):
#         total += len(block["text"])
#         if total > max_chars:
#             break
#         result.insert(0, block)

#     fresh = (int(time.time() * 1000) - _last_ts) < 2500
#     return {"conversation": result, "fresh": fresh}


# # RAW SDP signaling (browser sends offer.sdp as text)
# @app.post("/webrtc/offer")
# async def webrtc_offer(req: Request):
#     try:
#         sdp = (await req.body()).decode("utf-8", errors="ignore")
#         pc = _pc_for_captions()
#         await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
#         answer = await pc.createAnswer()
#         await pc.setLocalDescription(answer)
#         return Response(content=pc.localDescription.sdp, media_type="application/sdp")
#     except Exception as e:
#         traceback.print_exc()
#         raise HTTPException(status_code=400, detail=f"Invalid SDP offer: {e}")
# # --- put near the other globals ---
# LLM_COOLDOWN_SEC = int(os.getenv("LLM_COOLDOWN_SEC", "60"))  # default 60s
# _last_call_at = {"summary": 0.0, "nextq": 0.0, "explain": 0.0}

# # JSON signaling (safer; browser sends {type,sdp})
# @app.post("/webrtc/offer_json")
# async def webrtc_offer_json(payload: dict = Body(...)):
#     """
#     Expected payload:
#     { "type": "offer", "sdp": "<full offer SDP from RTCPeerConnection.createOffer()>" }
#     Returns:
#     { "type": "answer", "sdp": "<answer sdp>" }
#     """
#     try:
#         offer_type = payload.get("type")
#         offer_sdp = payload.get("sdp")
#         if offer_type != "offer" or not offer_sdp:
#             raise ValueError("Payload must include type='offer' and a non-empty sdp")

#         pc = _pc_for_captions()
#         await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
#         answer = await pc.createAnswer()
#         await pc.setLocalDescription(answer)
#         return {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
#     except Exception as e:
#         traceback.print_exc()
        # raise HTTPException(status_code=400, detail=f"Invalid JSON offer: {e}")
# 4th
import json
import time
import traceback
from typing import List, Dict

from fastapi import FastAPI, Request, Response, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription

app = FastAPI(title="Meet CC → WebRTC (captions only)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ----------------- transcript store -----------------
_conversation: List[Dict] = []
_last_ts = 0

def add_line(speaker: str | None, text: str | None):
    """Update conversation store without repeating partials"""
    global _last_ts
    txt = (text or "").strip()
    if not txt:
        return
    spk = (speaker or "Unknown").strip() or "Unknown"

    # if same speaker spoke last, update instead of duplicating
    if _conversation and _conversation[-1]["speaker"] == spk:
        _conversation[-1]["text"] = txt
    else:
        _conversation.append({"speaker": spk, "text": txt})

    # keep transcript manageable
    if len(_conversation) > 4000:
        del _conversation[:-4000]

    _last_ts = int(time.time() * 1000)

# ----------------- helpers -----------------
def _pc_for_captions():
    pc = RTCPeerConnection()

    @pc.on("datachannel")
    def on_datachannel(dc):
        if dc.label == "cc":
            @dc.on("message")
            def on_message(msg):
                try:
                    data = json.loads(msg)
                    add_line(data.get("speaker"), data.get("text"))
                except Exception:
                    # swallow malformed frames
                    pass
    return pc

# ----------------- routes -----------------
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/transcript")
def transcript(max_chars: int = 20000):
    # structured output
    fresh = (int(time.time() * 1000) - _last_ts) < 2500
    conv = _conversation[-1000:]  # last 1000 turns max
    return {
        "conversation": conv,
        "fresh": fresh
    }

# RAW SDP signaling
@app.post("/webrtc/offer")
async def webrtc_offer(req: Request):
    try:
        sdp = (await req.body()).decode("utf-8", errors="ignore")
        pc = _pc_for_captions()
        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        return Response(content=pc.localDescription.sdp, media_type="application/sdp")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid SDP offer: {e}")

# JSON signaling
@app.post("/webrtc/offer_json")
async def webrtc_offer_json(payload: dict = Body(...)):
    try:
        offer_type = payload.get("type")
        offer_sdp = payload.get("sdp")
        if offer_type != "offer" or not offer_sdp:
            raise ValueError("Payload must include type='offer' and a non-empty sdp")

        pc = _pc_for_captions()
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        return {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid JSON offer: {e}")

