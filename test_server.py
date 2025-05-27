import asyncio
import struct
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

class AudioTestHandler:
    def __init__(self):
        self.ws = None
        self.active = True
        self.audio_count = 0
        self.start_time = time.time()
        
    def set_websocket(self, ws):
        self.ws = ws
        
    async def listen_and_log(self):
        """Listen for audio data and log what we receive"""
        try:
            while self.active:
                # Read WebSocket message
                data = await self.ws.receive_bytes()
                
                # Parse the frame (assuming same format as your main server)
                if len(data) < 1:
                    print("Received empty data")
                    continue
                    
                flag = data[0]
                audio_data = data[1:]
                
                self.audio_count += 1
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                print(f"[{elapsed:.2f}s] Audio chunk #{self.audio_count}")
                print(f"  - Flag: 0x{flag:02x}")
                print(f"  - Data length: {len(audio_data)} bytes")
                
                if flag == 0x01:
                    print("  - Type: Microphone audio")
                elif flag == 0x02:
                    print("  - Type: Speaker audio")
                else:
                    print(f"  - Type: Unknown (flag={flag})")
                    
                # Print first few bytes as hex for debugging
                if len(audio_data) > 0:
                    hex_sample = ' '.join(f'{b:02x}' for b in audio_data[:min(16, len(audio_data))])
                    print(f"  - First bytes: {hex_sample}{'...' if len(audio_data) > 16 else ''}")
                    
                # Check if it looks like valid PCM audio data
                if len(audio_data) >= 2:
                    # Try to interpret as 16-bit PCM samples
                    try:
                        sample_count = len(audio_data) // 2
                        samples = struct.unpack(f'<{sample_count}h', audio_data[:sample_count*2])
                        max_amplitude = max(abs(s) for s in samples[:min(100, sample_count)])
                        print(f"  - Samples: {sample_count}, Max amplitude: {max_amplitude}")
                        
                        # Check for silence (very low amplitude)
                        if max_amplitude < 100:
                            print("  - WARNING: Audio appears to be mostly silence")
                        elif max_amplitude > 30000:
                            print("  - Note: High amplitude detected (possible clipping)")
                        else:
                            print("  - Audio levels look normal")
                            
                    except struct.error:
                        print("  - Could not parse as 16-bit PCM")
                
                print("  " + "-" * 50)
                
                # Send a simple response back (optional)
                if flag == 0x01:  # If it's mic audio, send back a simple response
                    response = struct.pack("B", 0x02) + b"test response"
                    await self.ws.send_bytes(response)
                    
        except WebSocketDisconnect:
            print("WebSocket disconnected")
            self.active = False
        except Exception as e:
            print(f"Error in listen_and_log: {e}")
            import traceback
            traceback.print_exc()
            self.active = False
    
    async def send_periodic_status(self):
        """Send periodic status updates"""
        try:
            while self.active:
                await asyncio.sleep(5)  # Every 5 seconds
                elapsed = time.time() - self.start_time
                print(f"\n[STATUS] Running for {elapsed:.1f}s, received {self.audio_count} audio chunks")
                if self.audio_count == 0:
                    print("[STATUS] No audio received yet - check frontend connection")
                print()
        except Exception as e:
            print(f"Error in status updates: {e}")
    
    async def run(self):
        """Main run loop"""
        print("Audio test handler started")
        print("Waiting for audio data...")
        print("=" * 60)
        
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.listen_and_log())
                tg.create_task(self.send_periodic_status())
        except Exception as e:
            print(f"Error in AudioTestHandler: {e}")
        finally:
            self.active = False
            print("Audio test handler stopped")


@app.websocket("/ws/audio")
async def audio_test_ws(ws: WebSocket):
    await ws.accept()
    print(f"WebSocket connected from: {ws.client}")
    
    handler = AudioTestHandler()
    handler.set_websocket(ws)
    
    try:
        await handler.run()
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()


@app.get("/")
async def root():
    return {
        "message": "Audio Test Server", 
        "description": "Connect to /ws/audio to test audio streaming",
        "instructions": "This server will log all received audio data for debugging"
    }


@app.get("/status")
async def status():
    return {
        "server": "Audio Test Server",
        "endpoint": "/ws/audio", 
        "purpose": "Debug audio streaming from frontend"
    }


if __name__ == "__main__":
    print("Starting Audio Test Server...")
    print("Connect your frontend to ws://127.0.0.1:9000/ws/audio")
    print("Check console output for audio data logs")
    uvicorn.run(app, host="127.0.0.1", port=9000)