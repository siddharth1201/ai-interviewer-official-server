import asyncio
import struct
import time
from datetime import datetime
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

class AudioTestHandler:
    def __init__(self):
        self.ws = None
        self.active = True
        self.audio_count = 0
        self.start_time = time.time()
        self.mic_file = None
        self.speaker_file = None
        self.output_dir = "audio_logs"
        self.stream_info = {
            "mic_chunks": 0,
            "speaker_chunks": 0,
            "total_bytes": 0,
            "sample_rate": None,  # To be determined from frontend if possible
            "channels": None,     # To be determined from frontend if possible
            "bit_depth": 16      # Assuming 16-bit PCM
        }
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
    def set_websocket(self, ws):
        self.ws = ws
        
    def _get_timestamped_filename(self, audio_type):
        """Generate a timestamped filename for audio output"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"{audio_type}_{timestamp}.pcm")
        
    def _open_audio_files(self):
        """Open new audio files for writing"""
        self.mic_file = open(self._get_timestamped_filename("mic"), "wb")
        self.speaker_file = open(self._get_timestamped_filename("speaker"), "wb")
        
    def _close_audio_files(self):
        """Close audio files if open"""
        if self.mic_file:
            self.mic_file.close()
        if self.speaker_file:
            self.speaker_file.close()
            
    async def listen_and_log(self):
        """Listen for audio data, save it, and log stream details"""
        try:
            self._open_audio_files()
            while self.active:
                # Read WebSocket message
                data = await self.ws.receive_bytes()
                
                if len(data) < 1:
                    print("Received empty data")
                    continue
                    
                flag = data[0]
                audio_data = data[1:]
                
                self.audio_count += 1
                self.stream_info["total_bytes"] += len(audio_data)
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                # Log detailed stream information
                print(f"\n[{elapsed:.2f}s] Audio chunk #{self.audio_count}")
                print(f"  - Flag: 0x{flag:02x}")
                print(f"  - Data length: {len(audio_data)} bytes")
                
                # Save audio data and log type
                if flag == 0x01:
                    print("  - Type: Microphone audio")
                    self.stream_info["mic_chunks"] += 1
                    self.mic_file.write(audio_data)
                    self.mic_file.flush()
                elif flag == 0x02:
                    print("  - Type: Speaker audio")
                    self.stream_info["speaker_chunks"] += 1
                    self.speaker_file.write(audio_data)
                    self.speaker_file.flush()
                else:
                    print(f"  - Type: Unknown (flag={flag})")
                    
                # Print first few bytes as hex for debugging
                if len(audio_data) > 0:
                    hex_sample = ' '.join(f'{b:02x}' for b in audio_data[:min(16, len(audio_data))])
                    print(f"  - First bytes: {hex_sample}{'...' if len(audio_data) > 16 else ''}")
                    
                # Analyze audio data
                if len(audio_data) >= 2:
                    try:
                        sample_count = len(audio_data) // 2
                        samples = struct.unpack(f'<{sample_count}h', audio_data[:sample_count*2])
                        max_amplitude = max(abs(s) for s in samples[:min(100, sample_count)])
                        print(f"  - Samples: {sample_count}, Max amplitude: {max_amplitude}")
                        
                        # Log stream characteristics
                        print(f"  - Stream Info:")
                        print(f"    - Bit depth: {self.stream_info['bit_depth']} bits")
                        print(f"    - Total bytes received: {self.stream_info['total_bytes']}")
                        print(f"    - Microphone chunks: {self.stream_info['mic_chunks']}")
                        print(f"    - Speaker chunks: {self.stream_info['speaker_chunks']}")
                        
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
                if flag == 0x01:
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
        finally:
            self._close_audio_files()
    
    async def send_periodic_status(self):
        """Send periodic status updates with stream summary"""
        try:
            while self.active:
                await asyncio.sleep(5)
                elapsed = time.time() - self.start_time
                print(f"\n[STATUS] Running for {elapsed:.1f}s")
                print(f"  - Total audio chunks: {self.audio_count}")
                print(f"  - Microphone chunks: {self.stream_info['mic_chunks']}")
                print(f"  - Speaker chunks: {self.stream_info['speaker_chunks']}")
                print(f"  - Total bytes received: {self.stream_info['total_bytes']}")
                print(f"  - Audio files saved in: {self.output_dir}")
                if self.audio_count == 0:
                    print("[STATUS] No audio received yet - check frontend connection")
                print()
        except Exception as e:
            print(f"Error in status updates: {e}")
    
    async def run(self):
        """Main run loop"""
        print("Audio test handler started")
        print(f"Saving audio to: {self.output_dir}")
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
            self._close_audio_files()
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
        "instructions": "This server will log all received audio data and save it to PCM files"
    }


@app.get("/status")
async def status():
    return {
        "server": "Audio Test Server",
        "endpoint": "/ws/audio", 
        "purpose": "Debug audio streaming from frontend and save audio data"
    }


if __name__ == "__main__":
    print("Starting Audio Test Server...")
    print("Connect your frontend to ws://127.0.0.1:9000/ws/audio")
    print("Check console output for audio data logs and saved files")
    uvicorn.run(app, host="127.0.0.1", port=9000)