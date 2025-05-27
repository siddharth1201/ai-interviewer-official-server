import os
import asyncio
import base64
import io
import traceback
import time

import pyaudio

from google import genai
from google.genai import types

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-preview-native-audio-dialog"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key="AIzaSyD9aN0yTsRxuXvZwl5kQA8THMc7ZJQIzd0",
)

# Try CONFIG without input_audio_transcription first to see if that's the issue
CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr"),
        )
    ),
    realtime_input_config=types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=False,
            start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
            end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
            prefix_padding_ms=100,
            silence_duration_ms=1000,
        )
    ),
    # Comment out input transcription for now
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    generation_config=types.GenerationConfig(
        temperature=0.7,
        top_p=0.95,
        top_k=70
    ),
)

pya = pyaudio.PyAudio()

prompt = """ 
You are an ai interviewer and you are interviewing a candidate for a software engineering position.
You will ask the candidate questions and wait for their response.
you will then ask follow-up questions based on their response.
You will not ask the candidate to write code, but you will ask them to explain their thought process and how they would approach a problem.
"""

class AudioLoop:
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=10000)  # Match your WebSocket handler
        self.session = None
        self.active = True
        self.last_audio_time = time.time()
        self.conversation = []

    def add_label(self, label, text):
        return f"{label}: {text}"

    async def send_text(self):
        while self.active:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                self.active = False
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        while self.active:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE)
            self.last_audio_time = time.time()
            await self.out_queue.put({
                "data": data, 
                "mime_type": "audio/pcm"
            })

    async def send_audio_to_gemini(self):
        """Match your WebSocket handler's method name and logic"""
        try:
            while self.active:
                msg = await self.out_queue.get()
                await self.session.send_realtime_input(audio=msg)
        except Exception as e:
            print(f"Error in send_audio_to_gemini: {e}")
            traceback.print_exc()

    async def receive_from_gemini(self):
        """Match your WebSocket handler's method name and logic"""
        try:
            while self.active:
                turn = self.session.receive()

                # Buffer for each label
                ai_text = ""
                candidate_text = ""

                async for response in turn:
                    # Handle audio data
                    if data := response.data:
                        print(f"Received audio data from Gemini: {len(data)} bytes")
                        self.audio_in_queue.put_nowait(data)

                    # Handle transcriptions
                    if response.server_content.output_transcription:
                        chunk = response.server_content.output_transcription.text or ""
                        ai_text += chunk
                        print("AI Transcript:", chunk)

                    if response.server_content.input_transcription:
                        chunk = response.server_content.input_transcription.text or ""
                        candidate_text += chunk
                        print("User Transcript:", chunk)

                # Append only once per speaker at the end of the turn
                if candidate_text.strip():
                    self.conversation.append(self.add_label("User", candidate_text.strip()))
                    print("Appended User text to conversation")

                if ai_text.strip():
                    self.conversation.append(self.add_label("AI", ai_text.strip()))
                    print("Appended AI text to conversation")

                print("conversation:", self.conversation)
                print("Turn complete")

        except Exception as e:
            print(f"Error in receive_from_gemini: {e}")
            traceback.print_exc()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while self.active:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def monitor_silence(self):
        """Add the silence monitoring from your WebSocket handler"""
        try:
            while self.active:
                await asyncio.sleep(0.5)  # Check every 0.5 seconds
                time_since_last_audio = time.time() - self.last_audio_time
                if time_since_last_audio > 2.0:  # 2 seconds threshold
                    print("Detected 2 seconds of silence. Signaling end of speech.")
                    # This might help trigger transcription
                    self.last_audio_time = time.time()  # Reset to prevent repeated signals
        except Exception as e:
            print(f"Error in monitor_silence: {e}")
            traceback.print_exc()

    async def run(self):
        """Match your WebSocket handler structure"""
        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.session = session
                
                # Send initial prompt like your WebSocket handler
                print("Sending initial prompt to Gemini...")
                await self.session.send(input=f"{prompt}", end_of_turn=True)
                print("Initial prompt sent.")
                
                # Create tasks matching your WebSocket handler structure
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.send_audio_to_gemini())
                    tg.create_task(self.receive_from_gemini())
                    tg.create_task(self.listen_audio())
                    tg.create_task(self.play_audio())
                    tg.create_task(self.send_text())
                    tg.create_task(self.monitor_silence())

        except asyncio.CancelledError:
            print("Session cancelled")
        except Exception as e:
            print(f"Error in AudioLoop: {e}")
            traceback.print_exc()
        finally:
            self.active = False
            if hasattr(self, 'audio_stream'):
                self.audio_stream.close()
            print("AudioLoop finished")


if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())