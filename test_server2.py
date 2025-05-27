import asyncio
import struct
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

# Audio configuration to match your original code
RECV_SR = 24_000  # Sample rate for received audio (matches your RECV_SR)
CHUNK = 1024      # Chunk size in bytes (matches your CHUNK)
FRAME_DURATION = CHUNK / (RECV_SR * 2)  # Duration of each chunk in seconds (2 bytes per sample for paInt16)

# Simulated or prerecorded audio file (replace with actual PCM file path if available)
# For testing, we'll generate a simple tone if no file is provided
AUDIO_FILE_PATH = "audio.mp3"  # Replace with "path/to/your/audio.pcm" if you have a raw PCM file

async def read_audio_chunks():
    """Read or simulate audio chunks in PCM format."""
    if AUDIO_FILE_PATH:
        with open(AUDIO_FILE_PATH, "rb") as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                yield chunk
                await asyncio.sleep(FRAME_DURATION)  # Simulate real-time playback
    else:
        # Simulate a simple 440Hz sine wave for testing (16-bit PCM, mono, 24kHz)
        import numpy as np
        t = np.linspace(0, 5, int(5 * RECV_SR), endpoint=False)  # 5 seconds of audio
        audio = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16).tobytes()
        for i in range(0, len(audio), CHUNK):
            yield audio[i:i + CHUNK]
            await asyncio.sleep(FRAME_DURATION)  # Simulate real-time playback

@app.websocket("/ws/audio")
async def audio_ws(ws: WebSocket):
    """WebSocket endpoint to send prerecorded or simulated audio to the frontend."""
    await ws.accept()
    try:
        async for chunk in read_audio_chunks():
            # Frame the audio chunk with 0x02 prefix, matching your play_audio method
            msg = struct.pack("B", 0x02) + chunk
            await ws.send_bytes(msg)
            print(f"Sent {len(chunk)} bytes of audio data")
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Error in WebSocket: {e}")

@app.get("/")
async def root():
    return {"message": "Sample audio server is running. Connect to /ws/audio for audio streaming."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9001)