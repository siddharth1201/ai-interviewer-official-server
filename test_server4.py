import asyncio
import wave
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import numpy as np
from datetime import datetime

app = FastAPI()

# Directory to store audio files
AUDIO_DIR = "audio_output"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Generate a unique filename based on timestamp
def get_unique_filename():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(AUDIO_DIR, f"recording_{timestamp}.wav")

@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    audio_buffer = bytearray()
    sample_rate = 64000  # Matches client specification
    channels = 1  # Mono
    sample_width = 2  # 16-bit PCM (2 bytes per sample)

    try:
        while True:
            # Receive binary data from WebSocket
            data = await websocket.receive_bytes()
            
            # Check for the 0x01 flag and strip it
            if data[0] == 0x01:
                pcm_data = data[1:]  # Remove the flag byte
            else:
                pcm_data = data  # Handle case where flag might be missing

            # Append PCM data to buffer
            audio_buffer.extend(pcm_data)

    except WebSocketDisconnect:
        # Save the audio buffer to a WAV file when the connection closes
        if audio_buffer:
            filename = get_unique_filename()
            try:
                with wave.open(filename, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_buffer)
                print(f"Audio saved to {filename}")
                # Send confirmation to client
                await websocket.send_text(f"Audio saved as {filename}")
            except Exception as e:
                print(f"Error saving audio: {e}")
                await websocket.send_text(f"Error saving audio: {str(e)}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        await websocket.close()

@app.get("/audio/{filename:path}")
async def get_audio_file(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)