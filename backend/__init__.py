from fastapi import Body

@app.post("/webrtc/offer_json")
async def webrtc_offer_json(payload: dict = Body(...)):
    offer = RTCSessionDescription(sdp=payload["sdp"], type=payload["type"])
    pc = RTCPeerConnection()
    # ... handlers ...
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {"type": pc.localDescription.type, "sdp": pc.localDescription.sdp}
