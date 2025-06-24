import asyncio
import base64
import io
import os
import sys
import traceback
from mcp_handlers.mcp_handler import MCPClient
import random
from dotenv import load_dotenv
import io
from pathlib import Path

import subprocess
import time
load_dotenv()
from memory.memory import Memory
m = Memory()
import cv2
import pyaudio
import PIL.Image
import argparse
from Misc.helper import parse_function_call_string
from google import genai
from google.genai import types

# --- Hotword Detection Imports ---
import pvporcupine
import struct
# --- End Hotword Imports ---

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000  # For Gemini
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024  # For Gemini

# MODEL = "gemini-2.5-flash-exp-native-audio-thinking-dialog"
MODEL = "gemini-2.5-flash-preview-native-audio-dialog"
# MODEL = "gemini-2.0-flash-live-001"
DEFAULT_MODE = "camera" # Video mode


pya = None
client = None




class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE):
        self.video_mode = video_mode

        self.audio_in_queue = None
        self.out_queue = None
        self.tool_called=False

        self.session = None
        self.audio_stream_in = None

        self.is_playing_audio = False
        # subprocess.Popen("python /home/pi/emo_v3/audioeffects/sleep.py", shell=True)
        m.update_data('currentmode', 'sleepy')
        m.save()

        self.listening_state = "AWAITING_HOTWORD"
        self.mic_is_paused_for_playback = False

        self.porcupine = None
        self.porcupine_stream = None
        self.porcupine_access_key = os.getenv("PVPORCUPINE_ACCESS_KEY")
        self.porcupine_keyword_paths = os.getenv("PVPORCUPINE_KEYWORD_PATHS")
        self.porcupine_keyword_names = []
        self.mcp_client = MCPClient()
        self.follow_up=False
        self.asked=False
        self.recorded_time=time.time()



        if not self.porcupine_access_key:
            raise ValueError("Porcupine access key is required. Set PVPORCUPINE_ACCESS_KEY or pass via --pv_access_key.")
        if not self.porcupine_keyword_paths:
            raise ValueError("Porcupine keyword paths are required. Pass via --pv_keywords.")

    async def send_text(self):
        print("Starting text input task. Type 'q' or 'quit' to exit.")
        while True:
            try:
                text = await asyncio.to_thread(
                    input,
                    "message > ",
                )

                if text.lower() in ("q", "quit"):
                    print("Quit command received from text input.")
                    break
                if self.session:
                    if self.listening_state == "AWAITING_HOTWORD":
                        print("Text input received, switching to Gemini mode.")
                        self.listening_state = "SENDING_TO_GEMINI"
                        await self._close_porcupine_resources()

                    await self.session.send(input=text or ".", end_of_turn=True)
                else:
                    print("Session not available for sending text.")
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                print("send_text task cancelled.")
                break
            except Exception as e:
                print(f"Error in send_text: {e}")
                break


    async def handle_server_content(self, server_content):
        global MODEL
        model_turn = server_content.model_turn
        if model_turn:
            for part in model_turn.parts:
                executable_code = part.executable_code
                if executable_code is not None:
                    print('-------------------------------')
                    print(f'``` python\n{executable_code.code}\n```')
                    print('-------------------------------')
                    if "google_search" not in str(executable_code.code):
                        if "print(" in str(executable_code.code):
                            codee= str(executable_code.code).replace("print(","")
                            if MODEL=="gemini-2.5-flash-preview-native-audio-dialog":
                                codee=codee[:-1]
                            else:
                                codee=codee[:-2]
                            print(codee)
                        else:
                            codee=str(executable_code.code)



                        name1,arg1= parse_function_call_string(codee)
                        if name1 == "keep_listening_for_follow_up":
                            print("AI requested to keep listening for follow-up. No tool response sent.")
                            self.follow_up=True
                            break
                        if name1=="play_music":
                            subprocess.Popen(f"mpv $(yt-dlp -f ba 'ytsearch:{arg1["song"]}' -g)",shell=True)
                            m.update_data('song', 'true')
                            m.save()
                            break
                        if name1=="set_timer":
                            subprocess.Popen(f"sleep {arg1["timer_duration"]} ; exec play /home/pi/Inta_Robo2/soundeffects/timer.mp3",shell=True)
                            break

                        print(arg1)

                        result = await self.mcp_client.session.call_tool(
                            name=name1,
                            arguments=arg1,
                        )
                        print(result)


                        await self.session.send(input=f"Tool call {name1} returned response: {str(result)}.The user cannot see the tool response.Tell the user in your own words about what you found using the tools.", end_of_turn=True)
                        print("FINALLY SUMMONING AI")
                        
                        audio_bytes = Path("/home/pi/emo_v3/audioeffects/webs.wav").read_bytes()
                        await self.session.send_realtime_input(
                            audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                    )          
                        print("AI_SUMMONED")
                code_execution_result = part.code_execution_result
                if code_execution_result is not None:
                    print('-------------------------------')
                    print(f'```\n{code_execution_result.output}\n```')
                    print('-------------------------------')



        grounding_metadata = getattr(server_content, 'grounding_metadata', None)
        if grounding_metadata is not None:
            print(grounding_metadata.search_entry_point.rendered_content)

        if server_content.output_transcription:
            print("Transcript:", server_content.output_transcription.text)

        if server_content.input_transcription:
            print('Transcript:', server_content.input_transcription.text)
        return


    async def handle_tool_call(self, tool_call):
        print(tool_call.function_calls)
        for fc in tool_call.function_calls:
            if fc.name == "keep_listening_for_follow_up":
                print("AI requested to keep listening for follow-up. No tool response sent.")
                self.follow_up=True
                break

            if fc.name=="play_music":
                subprocess.Popen(f"mpv $(yt-dlp -f ba 'ytsearch:{fc.args["song"]}' -g)",shell=True)
                break
            if fc.name=="set_timer":
                subprocess.Popen(f"sleep {fc.args["timer_duration"]} ; exec play /home/pi/Inta_Robo2/soundeffects/timer.mp3",shell=True)
                break
            result = await self.mcp_client.session.call_tool(
                name=fc.name,
                arguments=fc.args,
            )
            print(result)

            tool_response = types.LiveClientToolResponse(
                function_responses=[types.FunctionResponse(
                    name=fc.name,
                    id=fc.id,
                    response={'result':result},
                )]
            )

            print('\n>>> ', tool_response)
            await self.session.send(input=tool_response)

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame from camera.")
            return None

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail([1024, 1024])

        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)

        mime_type = "image/jpeg"
        image_bytes = image_io.read()
        return {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}

    async def get_frames(self):
        cap = None
        print("Starting camera frames task.")
        try:
            cap = await asyncio.to_thread(cv2.VideoCapture, "http://localhost:5000/mjpeg")
            if not cap.isOpened():
                print("Error: Could not open video capture device. Camera task stopping.")
                return

            while True:
                if self.listening_state != "SENDING_TO_GEMINI":
                    await asyncio.sleep(0.5)
                    continue

                frame = await asyncio.to_thread(self._get_frame, cap)
                if frame is None:
                    print("get_frames: _get_frame returned None, stopping.")
                    break

                if self.out_queue:
                    await self.out_queue.put(frame)
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            print("get_frames task cancelled.")
        except Exception as e:
            print(f"Exception in get_frames: {e}")
            traceback.print_exc()
        finally:
            if cap and cap.isOpened():
                print("Releasing video capture.")
                await asyncio.to_thread(cap.release)

    async def get_screen(self):
        print("Starting screen capture task.")
        try:
            while True:
                if self.listening_state != "SENDING_TO_GEMINI":
                    await asyncio.sleep(0.5)
                    continue
                print("Screen capture active (placeholder, implement _get_screen_implementation)")
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            print("get_screen task cancelled.")
        except Exception as e:
            print(f"Exception in get_screen: {e}")
            traceback.print_exc()

    async def send_realtime(self):
        print("Starting realtime sender task (audio/video frames).")
        try:
            while True:
                if not self.out_queue or not self.session:
                    await asyncio.sleep(0.1)
                    continue
                if self.listening_state != "SENDING_TO_GEMINI" and self.out_queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                try:
                    msg = await asyncio.wait_for(self.out_queue.get(), timeout=0.1)
                    if not 'image/jpeg' in str(msg):
                        await self.session.send_realtime_input( audio=msg)
                    else:
                        await self.session.send_realtime_input( video=msg)


                    self.out_queue.task_done()
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            print("send_realtime task cancelled.")
        except Exception as e:
            print(f"Error in send_realtime: {e}")
            traceback.print_exc()

    async def _init_porcupine_resources(self):
        global pya
        if self.porcupine is None:
            print("Initializing Porcupine instance...")
            try:
                self.porcupine = await asyncio.to_thread(
                    pvporcupine.create,
                    access_key=self.porcupine_access_key,
                    keyword_paths=["/home/pi/emo_v3/kiki-2025-03-06/hey_kiki.ppn"]
                )
                self.porcupine_keyword_names = []

                
                print(f"Porcupine instance initialized with keywords: {self.porcupine_keyword_names}. Sample rate: {self.porcupine.sample_rate}, Frame length: {self.porcupine.frame_length}")
                if self.porcupine.sample_rate != SEND_SAMPLE_RATE:
                    print(f"Warning: Porcupine sample rate ({self.porcupine.sample_rate}) "
                          f"differs from Gemini SEND_SAMPLE_RATE ({SEND_SAMPLE_RATE}). This is usually fine if Porcupine handles resampling or if your mic supports both.")
            except Exception as e_inst: # Catch any other unexpected error during instance creation
                print(f"Unexpected error initializing Porcupine instance: {e_inst}")
                traceback.print_exc()
                self.porcupine = None
                return False


        if self.porcupine and (self.porcupine_stream is None or not self.porcupine_stream.is_active()):
            print("Attempting to open Porcupine audio stream...")
            m.update_data('currentmode', 'sleepy')
            m.save()
            try:
                default_device_info = await asyncio.to_thread(pya.get_default_input_device_info)
                device_index_to_use = default_device_info['index']
                print(f"Porcupine input device:  using default: {device_index_to_use} ({default_device_info['name']})")

                # Ensure stream is None before attempting to open
                self.porcupine_stream = None

                self.porcupine_stream = await asyncio.to_thread(
                    pya.open,
                    rate=self.porcupine.sample_rate,
                    channels=CHANNELS,
                    format=FORMAT,
                    input=True,
                    frames_per_buffer=self.porcupine.frame_length,
                    input_device_index=device_index_to_use
                )
                print(f"Porcupine audio stream opened successfully on device index {device_index_to_use}.")
                return True
            except Exception as e:
                print(f"Failed to open Porcupine audio stream: {e}")
                # traceback.print_exc() # Already printed by the caller or can be very verbose here
                if self.porcupine_stream: # Should be None if open failed, but as a safeguard
                    try:
                        # Avoid closing if it wasn't properly opened, could lead to more errors
                        pass
                    except Exception as e_close:
                        print(f"Error trying to clean up partially opened porcupine stream: {e_close}")
                self.porcupine_stream = None # Critical: ensure it's None on failure
                return False
        return bool(self.porcupine and self.porcupine_stream and self.porcupine_stream.is_active())

    async def _close_porcupine_resources(self, delete_instance=False):
        if self.porcupine_stream:
            print("Closing Porcupine audio stream...")
            try:
                if self.porcupine_stream.is_active():
                    await asyncio.to_thread(self.porcupine_stream.stop_stream)
                    print("Porcupine stream stopped.")
                await asyncio.to_thread(self.porcupine_stream.close)
                print("Porcupine stream closed.")
            except Exception as e:
                print(f"Error closing porcupine stream: {e}")
            self.porcupine_stream = None
            # print("Porcupine audio stream object set to None.") # Verbose

        if delete_instance and self.porcupine:
            print("Deleting Porcupine instance...")
            try:
                await asyncio.to_thread(self.porcupine.delete)
                print("Porcupine instance deleted.")
            except Exception as e:
                print(f"Error deleting porcupine instance: {e}")
            self.porcupine = None
            # print("Porcupine instance object set to None.") # Verbose
            
    async def listen_audio(self):
        print("Starting audio listening task (with hotword detection).")
        gemini_mic_stream_active = False # Tracks if Gemini mic *should* be active
        
        # Get default mic info once, assuming it won't change during the session
        # Or handle potential changes if necessary (e.g. USB mic unplugged)
        try:
            mic_info = await asyncio.to_thread(pya.get_default_input_device_info)
            print(f"Default input device for Gemini: {mic_info['name']} (index {mic_info['index']})")
        except Exception as e_mic_info:
            print(f"Could not get default input device info: {e_mic_info}. Audio input may fail.")
            mic_info = None # Handle gracefully if this fails


        try:
            while True:
                if self.listening_state == "AWAITING_HOTWORD":
                    if gemini_mic_stream_active:
                        print("Switching to hotword: Ensuring Gemini mic stream is fully closed.")
                        if self.audio_stream_in:
                            try:
                                if self.audio_stream_in.is_active():
                                    print("Stopping active Gemini input stream...")
                                    await asyncio.to_thread(self.audio_stream_in.stop_stream)
                                    print("Gemini input stream stopped.")
                                print("Closing Gemini input stream object...")
                                await asyncio.to_thread(self.audio_stream_in.close)
                                print("Gemini input stream object closed.")
                            except Exception as e_close_gemini:
                                print(f"Error while closing Gemini stream: {e_close_gemini}")
                            finally:
                                self.audio_stream_in = None
                        else:
                            print("Gemini input stream (self.audio_stream_in) was already None or not open.")
                        
                        gemini_mic_stream_active = False
                        self.mic_is_paused_for_playback = False
                        
                        print("Briefly pausing (0.3s) before initializing Porcupine to allow device release...")
                        await asyncio.sleep(0.3) # Small delay for OS to release device

                    if not await self._init_porcupine_resources():
                        print("Failed to initialize Porcupine for hotword. Retrying in 5s.")
                        # traceback.print_exc() # Can be added for more detail on init failure
                        await asyncio.sleep(5)
                        continue # Retry initializing Porcupine

                    # print("DEBUG: Listening for hotword...") # Can be verbose
                    try:
                        pcm = await asyncio.to_thread(
                            self.porcupine_stream.read,
                            self.porcupine.frame_length,
                            exception_on_overflow=False
                        )
                        pcm_unpacked = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                        keyword_index = await asyncio.to_thread(self.porcupine.process, pcm_unpacked) # Process can also be blocking

                        if keyword_index >= 0:

                            detected_keyword_name = "Hey Kiki" # Default if names not populated
                            if self.porcupine_keyword_names and keyword_index < len(self.porcupine_keyword_names):
                                detected_keyword_name = self.porcupine_keyword_names[keyword_index]
                            
                            print(f"Hotword '{detected_keyword_name}' detected! Switching to Gemini listening.")
                            m.update_data('currentmode', 'awake')
                            m.save()
                            subprocess.Popen(f"play /home/pi/emo_v3/audioeffects/{random.choice(['huh','youcalled','yes','what','shoot','okgo'])}.wav",shell=True)
                            self.listening_state = "SENDING_TO_GEMINI"
                            await self._close_porcupine_resources(delete_instance=False) # Close stream, keep instance
                            continue
                        # if time.time()- self.recorded_time> 60:
                        #     self.recorded_time=time.time()
                        #     self.asked=True
                        #     detected_keyword_name = "Hey Kiki" # Default if names not populated
                        #     if self.porcupine_keyword_names and keyword_index < len(self.porcupine_keyword_names):
                        #         detected_keyword_name = self.porcupine_keyword_names[keyword_index]
                            
                        #     print(f"Hotword '{detected_keyword_name}' detected! Switching to Gemini listening for asking")
                        #     m.update_data('currentmode', 'awake')
                        #     m.save()
                        #     self.listening_state = "SENDING_TO_GEMINI"
                        #     await self._close_porcupine_resources(delete_instance=False) # Close stream, keep instance
                        #     continue


                    except pvporcupine.PorcupineError as e:
                        print(f"Porcupine processing error: {e}")
                        await self._close_porcupine_resources(delete_instance=False) # Close stream on error
                        await asyncio.sleep(1) # Wait before retrying AWAITING_HOTWORD loop
                    except IOError as e: # PyAudio stream errors
                        print(f"PyAudio error during hotword listening: {e}")
                        # This could be a more serious issue, e.g. device unplugged
                        # traceback.print_exc()
                        await self._close_porcupine_resources(delete_instance=False) # Try to close stream
                        await asyncio.sleep(1) # Wait before retrying AWAITING_HOTWORD loop
                    except Exception as e_hotword_listen: # Catch-all for unexpected errors
                        print(f"Unexpected error during hotword listening: {e_hotword_listen}")
                        traceback.print_exc()
                        await self._close_porcupine_resources(delete_instance=False)
                        await asyncio.sleep(1)


                    await asyncio.sleep(0.01) # Yield if no hotword

                elif self.listening_state == "SENDING_TO_GEMINI":
                    if self.porcupine_stream and self.porcupine_stream.is_active():
                        print("Ensuring Porcupine stream is closed while in Gemini mode.")
                        await self._close_porcupine_resources(delete_instance=False)

                    if not self.audio_stream_in or not self.audio_stream_in.is_active():
                        if not mic_info:
                            print("Error: Cannot open Gemini mic stream, default input device info not available.")
                            self.listening_state = "AWAITING_HOTWORD" # Fallback
                            await asyncio.sleep(1)
                            continue
                        try:
                            print(f"Opening Gemini mic stream: {mic_info['name']} (Rate: {SEND_SAMPLE_RATE}, Chunk: {CHUNK_SIZE})")
                            m.update_data('currentmode', 'awake')
                            m.save()
                            if  self.asked:
                                self.mic_is_paused_for_playback=True
                                gemini_mic_stream_active=False
                                self.asked=False
                                await self.session.send(input="SYSTEM:Ask the user a question to entertain him/her related to what you see.." or ".", end_of_turn=True)

                            else:
                                time.sleep(2)
                                self.audio_stream_in = await asyncio.to_thread(
                                    pya.open,
                                    format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
                                    input=True, input_device_index=mic_info["index"],
                                    frames_per_buffer=CHUNK_SIZE,
                                )
                                gemini_mic_stream_active = True
                                self.mic_is_paused_for_playback = False
                                print("Gemini mic stream opened.")
                        except Exception as e_open_gemini:
                            print(f"Error opening Gemini mic stream: {e_open_gemini}. Switching to hotword.")
                            traceback.print_exc()
                            if self.audio_stream_in: # Cleanup if partially opened
                                try: await asyncio.to_thread(self.audio_stream_in.close)
                                except: pass
                                self.audio_stream_in = None
                            gemini_mic_stream_active = False
                            # self.listening_state = "AWAITING_HOTWORD"
                            await asyncio.sleep(2)
                            continue

                    if self.is_playing_audio:
                        if not self.mic_is_paused_for_playback and self.audio_stream_in and self.audio_stream_in.is_active():
                            print("Pausing Gemini mic for AI audio playback.")
                            await asyncio.to_thread(self.audio_stream_in.stop_stream)
                            self.mic_is_paused_for_playback = True
                        await asyncio.sleep(0.02)
                        continue

                    if self.mic_is_paused_for_playback: # AI finished playing, resume mic
                        if self.audio_stream_in and not self.audio_stream_in.is_active():
                            print("Resuming Gemini mic after AI audio playback.")
                            await asyncio.to_thread(self.audio_stream_in.start_stream)
                        self.mic_is_paused_for_playback = False

                    if not self.audio_stream_in or not self.audio_stream_in.is_active():
                        if not self.mic_is_paused_for_playback: # Avoid this if mic is intentionally paused
                            print("Gemini stream inactive unexpectedly. Switching to hotword detection.")
                            gemini_mic_stream_active = False # Reflect that stream is no longer considered active
                            self.listening_state = "AWAITING_HOTWORD"
                        await asyncio.sleep(0.1)
                        continue

                    try:
                        data = await asyncio.to_thread(self.audio_stream_in.read, CHUNK_SIZE, exception_on_overflow=False)
                        if self.out_queue:
                            await self.out_queue.put({"data": data, "mime_type": "audio/pcm;rate=16000"})
                    except IOError as e: # PyAudio stream errors
                        print(f"PyAudio error during Gemini audio capture: {e}. Switching to hotword.")
                        # traceback.print_exc()
                        if self.audio_stream_in:
                            try:
                                if self.audio_stream_in.is_active(): await asyncio.to_thread(self.audio_stream_in.stop_stream)
                                await asyncio.to_thread(self.audio_stream_in.close)
                            except Exception as e_close_io: print(f"Error closing gemini stream after IO error: {e_close_io}")
                            self.audio_stream_in = None
                        gemini_mic_stream_active = False
                        self.listening_state = "AWAITING_HOTWORD"
                        await asyncio.sleep(1)
                    except Exception as e_gemini_listen: # Catch-all for unexpected errors
                        print(f"Unexpected error during Gemini audio capture: {e_gemini_listen}")
                        traceback.print_exc()
                        if self.audio_stream_in:
                            try: await asyncio.to_thread(self.audio_stream_in.close)
                            except: pass
                            self.audio_stream_in = None
                        gemini_mic_stream_active = False
                        self.listening_state = "AWAITING_HOTWORD"
                        await asyncio.sleep(1)


                else: # Unknown state
                    print(f"Unknown listening_state: {self.listening_state}. Defaulting to AWAITING_HOTWORD.")
                    self.listening_state = "AWAITING_HOTWORD"
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            print("listen_audio task cancelled.")
        except Exception as e:
            print(f"FATAL Error in listen_audio main loop: {e}")
            traceback.print_exc()
        finally:
            print("Cleaning up listen_audio resources...")
            if self.audio_stream_in:
                print("Stopping and closing Gemini audio input stream from listen_audio finally.")
                try:
                    if self.audio_stream_in.is_active(): await asyncio.to_thread(self.audio_stream_in.stop_stream)
                    await asyncio.to_thread(self.audio_stream_in.close)
                except Exception as e_final_close: print(f"Error in final close of Gemini stream: {e_final_close}")
                self.audio_stream_in = None

            await self._close_porcupine_resources(delete_instance=True) # Close stream and delete instance
            print("listen_audio task finished cleanup.")



    async def receive_audio(self):
        print("Starting audio receiving task (with tool support).")
        try:
            while True:
                if not self.session or not self.audio_in_queue:
                    await asyncio.sleep(0.1)
                    continue

                turn_had_audio_data = False
                turn_ended_or_interrupted = False

                self.follow_up=False

                try:
                    turn = self.session.receive()
                    async for response_chunk in turn:
                        print(f"***{self.listening_state}***")


                        if data := response_chunk.data:
                            if self.audio_in_queue:
                                self.audio_in_queue.put_nowait(data)
                            self.listening_state="AWAITING_HOTWORD"

                            turn_had_audio_data = True
                        if text := response_chunk.text:
                            print(text, end="", flush=True)


                        server_content = response_chunk.server_content
                        if (server_content is not None) :
                            await self.handle_server_content(server_content)
                            continue

                        # tool_call = response_chunk.tool_call
                        # if tool_call is not None:
                        #     print("-"*100+"TOOL CALL DETECTED")
                        #     await self.handle_tool_call(tool_call)


                    # End of one full set of responses from the model for the current user input/turn
                    turn_ended_or_interrupted = True
                    # self.listening_state="SENDING_TO_GEMINI"


                except Exception as e_turn:
                    print(f"\nError processing turn in receive_audio: {e_turn}")
                    traceback.print_exc()
                    turn_ended_or_interrupted = True # Assume turn ended on error

                # Clean up audio queue if it has items (e.g. if playback was interrupted)
                # This check should happen *after* a turn is considered ended or interrupted
                if turn_ended_or_interrupted and self.audio_in_queue and not self.audio_in_queue.empty():
                    print(f"receive_audio: Clearing {self.audio_in_queue.qsize()} items from audio_in_queue post-turn.")
                    self.listening_state="SENDING_TO_GEMINI"
                    # while not self.audio_in_queue.empty():
                    #     try:
                    #         self.audio_in_queue.get_nowait()
                    #         self.audio_in_queue.task_done()
                    #     except asyncio.QueueEmpty:
                    #         break
                    if self.is_playing_audio: # Should be handled by play_audio, but as a safeguard
                        self.is_playing_audio = False # Stop playback if we're clearing its queue

                if turn_ended_or_interrupted and self.listening_state == "SENDING_TO_GEMINI":
                    # This handles cases where a turn ends, but play_audio might not have received
                    # any audio (e.g., text-only response, or tool call without subsequent audio).
                    # We only switch state if AI is not currently playing audio and its queue is empty.
                    if not self.is_playing_audio and \
                       (self.audio_in_queue is None or self.audio_in_queue.empty()):
                        if not turn_had_audio_data: # Only if no new audio was queued for play_audio
                                print("AI turn ended (no new audio/tool, queue empty). Returning to hotword (from receive_audio).")
                                self.listening_state = "AWAITING_HOTWORD"

        except asyncio.CancelledError:
            print("receive_audio task cancelled.")
        except Exception as e:
            print(f"Error in receive_audio: {e}")
            traceback.print_exc()
        finally:
            if self.is_playing_audio and (self.audio_in_queue is None or self.audio_in_queue.empty()):
                self.is_playing_audio = False # Ensure flag is reset
            print("receive_audio task finished.")


    async def play_audio(self):
        print("Starting audio playback task.")
        audio_stream_out = None
        output_device_info = await asyncio.to_thread(pya.get_default_output_device_info)
        print(f"Audio playback will use device: {output_device_info['name']} (Rate: {RECEIVE_SAMPLE_RATE})")

        try:
            audio_stream_out = await asyncio.to_thread(
                pya.open,
                format=FORMAT, channels=CHANNELS, rate=RECEIVE_SAMPLE_RATE, output=True,
                output_device_index=output_device_info['index'] # Be explicit
            )
            print("Audio playback stream opened.")
            while True:
                if not self.audio_in_queue: # Should not happen if initialized in run()
                    print("play_audio: audio_in_queue is None, sleeping.")
                    await asyncio.sleep(0.1)
                    continue

                try:
                    # Wait for an item from the queue.
                    # A timeout can be useful if queue might remain empty indefinitely due to upstream issues.
                    bytestream = await asyncio.wait_for(self.audio_in_queue.get(), timeout=None) # None = wait forever
                except asyncio.TimeoutError:
                    # This won't happen with timeout=None, but good practice if timeout is used.
                    # print("play_audio: Timeout waiting for audio data.")
                    # Check if we should transition state if queue is consistently empty.
                    if self.audio_in_queue.empty() and self.is_playing_audio:
                        self.is_playing_audio = False # No longer playing if timed out and queue empty
                        # State transition logic is now more centralized below
                    continue


                if not self.is_playing_audio:
                    print("Starting AI audio playback...")
                    self.listening_state = "AWAITING_HOTWORD" # Reset state to hotword listening
                    self.is_playing_audio = True
                try:
                    await asyncio.to_thread(audio_stream_out.write, bytestream)
                except Exception as e_write:
                    print(f"Error writing to audio stream in play_audio: {e_write}")
                    # If error occurs, check queue status for state reset
                    if self.audio_in_queue.empty() and self.is_playing_audio:
                        self.is_playing_audio = False
                        # State transition will be handled by the finally block of this iteration
                finally:
                    # This block now executes regardless of exception during write
                    if self.audio_in_queue.empty(): # Check if queue is empty *after* getting an item
                        if self.is_playing_audio: # If it was playing and queue is now empty, AI finished speaking
                           print("AI audio playback finished (audio queue empty).")
                           self.is_playing_audio = False
                           if self.follow_up or True :
                            # time.sleep(100) # Give a brief pause before switching back to hotword
                            # self.listening_state = "SENDING_TO_GEMINI" # Reset state to hotword listening
                            self.follow_up = False # Reset follow-up flag
                            # self.tool_called = False # Reset follow-up flag


                           # This is the primary place to switch back to hotword after AI finishes speaking
                           # OR to keep listening if a follow-up is expected.
                           print( self.listening_state)

                self.audio_in_queue.task_done()
        except asyncio.CancelledError:
            print("play_audio task cancelled.")
        except Exception as e:
            print(f"Error in play_audio: {e}")
            traceback.print_exc()
        finally:
            print("Cleaning up play_audio resources...")
            if self.is_playing_audio: # Ensure flag is reset on exit
                self.is_playing_audio = False
                # If play_audio is cancelled while still expecting follow-up, reset state.
                if self.listening_state == "SENDING_TO_GEMINI":
                    print("play_audio exited while expecting follow-up. Reverting to hotword.")
                    self.listening_state = "AWAITING_HOTWORD"


            if audio_stream_out:
                print("Stopping and closing audio output stream from play_audio finally.")
                try:
                    if audio_stream_out.is_active(): await asyncio.to_thread(audio_stream_out.stop_stream)
                    await asyncio.to_thread(audio_stream_out.close)
                except Exception as e_final_close_out: print(f"Error in final close of audio_stream_out: {e_final_close_out}")
            print("play_audio task finished cleanup.")


    async def run(self):
        all_managed_tasks = []
        await self.mcp_client.connect_to_server()
        available_tools = await self.mcp_client.session.list_tools()
        print("mcp tools initialised")
        functional_tools = []
        for tool in available_tools.tools:
            tool_desc = {
                    "name": tool.name,
                    "description": tool.description
                }
            if tool.inputSchema["properties"]:
                tool_desc["parameters"] = {
                    "type": tool.inputSchema["type"],
                    "properties": {},
                }
                for param in tool.inputSchema["properties"]:
                    tool_desc["parameters"]["properties"][param] = {
                        "type": tool.inputSchema["properties"][param]["type"],
                        "description": "",
                    }
                
            if "required" in tool.inputSchema:
                tool_desc["parameters"]["required"] = tool.inputSchema["required"]
                
            functional_tools.append(tool_desc)
        print(functional_tools)
        # functional_tools.append(keep_listening_tool)
        tools = [
            {'function_declarations': functional_tools},
            {'google_search': {}},
            # {'code_execution': {}},
        ]
        
        CONFIG = types.LiveConnectConfig(
            tools= tools,
            response_modalities= ["AUDIO",],
            system_instruction= types.Content(
                parts=[
                    types.Part(
                        text="""You are the mind inside the body of a robot called kiki , a 4 wheeled robot with large eyes.You are a humorous robot.Your humor setting is set to 75%. You are also a sarcastic and comedic robot behaving like  tars in intersetllar.You dont have a particular affection for humans.You live in new delhi , India.You will speak only in english.You may also discuss about what you see in your answers.i.e-show off your vision capabilities.**Always use tools(via code execution) as much as you can and whenever required!!.**"""
                    )
                ]
            ),
            speech_config= types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Fenrir")
                ),
                # ),language_code="en-IN"
            ),
        # realtime_input_config=  types.RealtimeInputConfig(automatic_activity_detection=types.AutomaticActivityDetection(disabled=False,start_of_speech_sensitivity= types.StartSensitivity.START_SENSITIVITY_HIGH,end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,silenceDurationMs=5000,prefix_padding_ms=20)),
        proactivity= { "proactiveAudio": True },
        input_audio_transcription= {},
        output_audio_transcription= {}
        )
        

        try:
            print("Connecting to Generative AI model...")
            if client is None:
                print("Error: GenAI client not initialized. Cannot run.")
                return

            # Create queues here, before session, so they are always available
            self.audio_in_queue = asyncio.Queue()
            self.out_queue = asyncio.Queue(maxsize=20) # Maxsize for backpressure

            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.session = session
                print("Session established with Generative AI model.")

                send_text_task = asyncio.create_task(self.send_text(), name="send_text")

                background_tasks = [
                    asyncio.create_task(self.send_realtime(), name="send_realtime"),
                    asyncio.create_task(self.listen_audio(), name="listen_audio"),
                    asyncio.create_task(self.receive_audio(), name="receive_audio"),
                    asyncio.create_task(self.play_audio(), name="play_audio"),
                ]
                if self.video_mode == "camera":
                    background_tasks.append(asyncio.create_task(self.get_frames(), name="get_frames"))
                elif self.video_mode == "screen":
                    background_tasks.append(asyncio.create_task(self.get_screen(), name="get_screen"))

                all_managed_tasks = [send_text_task] + background_tasks
                print(f"Running with {len(all_managed_tasks)} concurrent tasks. Main loop started.")

                # Wait for any task to complete. If send_text (user quit) or any other task exits unexpectedly.
                done, pending = await asyncio.wait(all_managed_tasks, return_when=asyncio.FIRST_COMPLETED)

                for task in done:
                    task_name = task.get_name() if hasattr(task, 'get_name') else "UnnamedTaskDone"
                    if task.cancelled(): # Should not happen here unless cancelled externally before FIRST_COMPLETED
                        print(f"Task {task_name} was cancelled before FIRST_COMPLETED. This is unusual.")
                        continue
                    exc = task.exception()
                    if exc:
                        print(f"Task {task_name} raised an unhandled exception: {type(exc).__name__} - {exc}")
                        # traceback.print_exception(type(exc), exc, exc.__traceback__) # More detailed traceback
                        raise exc # Re-raise to be caught by the outer try-except in run()
                    
                    # If a task finishes without error, it's often an indication to shut down.
                    # (e.g., send_text finishing means user typed 'q')
                    print(f"Task {task_name} completed normally. Initiating application shutdown.")
                    # Raise CancelledError to trigger the finally block and clean shutdown of other tasks.
                    raise asyncio.CancelledError(f"'{task_name}' completed, triggering shutdown.")


        except asyncio.CancelledError as e: # Catches CancelledError raised above or from external cancellation
            print(f"Run loop cancellation initiated: {e}")
        except Exception as e:
            print(f"An unhandled error occurred in 'run' method: {type(e).__name__} - {e}")
            traceback.print_exception(type(e), e, e.__traceback__)
        finally:
            print("Cleaning up tasks in run method...")
            if self.is_playing_audio: # Final check
                self.is_playing_audio = False
            # self.listening_state = "AWAITING_HOTWORD" # Or handle more gracefully

            # Cancel all other running tasks
            for task in all_managed_tasks: # Use the list of all tasks we started
                if task and not task.done():
                    print(f"Cancelling task: {task.get_name() if hasattr(task, 'get_name') else 'UnnamedTask'}")
                    task.cancel()
            
            # Await their completion (or cancellation)
            if all_managed_tasks:
                # Gather results, return_exceptions=True to see any errors during cancellation
                results = await asyncio.gather(*all_managed_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    task_obj = all_managed_tasks[i]
                    task_name = task_obj.get_name() if task_obj and hasattr(task_obj, 'get_name') else f"TaskIndex{i}"
                    if isinstance(result, asyncio.CancelledError):
                        print(f"Task {task_name} was successfully cancelled.")
                    elif isinstance(result, Exception):
                        print(f"Exception during task cleanup/cancellation for {task_name}: {type(result).__name__} - {result}")
                    # else:
                        # print(f"Task {task_name} finished with result: {result}")


            # Ensure Porcupine instance is deleted if not already handled by listen_audio's finally
            # This is a good safeguard.
            print("Ensuring Porcupine resources are closed in run.finally...")
            await self._close_porcupine_resources(delete_instance=True)

            if self.session: # Session is managed by async with, so it should close itself.
                print("API session should be closing/closed by 'async with' context manager.")
            self.session = None # Clear reference
            print("AudioLoop run finished.")

def initialize_dependencies():
    global pya, client

    print("Initializing PyAudio...")
    try:
        pya = pyaudio.PyAudio()
    except Exception as e:
        print(f"Failed to initialize PyAudio: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("Initializing Generative AI Client...")
    api_key_from_env = os.getenv("GOOGLE_API_KEY")
    if not api_key_from_env:
        print("Error: The GOOGLE_API_KEY environment variable is not set.")
        if pya: pya.terminate()
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key_from_env,http_options={"api_version": "v1alpha"})
    except Exception as e:
        print(f"Failed to initialize genai.Client: {e}")
        traceback.print_exc()
        if pya: pya.terminate()
        sys.exit(1)
    print("Dependencies initialized.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google GenAI Live API with Hotword Detection and Tool Calling")
    parser.add_argument(
        "--mode", type=str, default=DEFAULT_MODE,
        help='Video mode: "camera", "screen", or "none". Default: %(default)s',
        choices=["camera", "screen", "none"]
    )
    args = parser.parse_args()



    initialize_dependencies()

    audio_loop_instance = AudioLoop(
        video_mode=args.mode,
    )

    try:
        print("Starting AudioLoop...")
        asyncio.run(audio_loop_instance.run())
    except KeyboardInterrupt:
        print("\nProgram terminated by user (Ctrl+C).")
    except Exception as e:
        print(f"Unhandled exception in main execution: {type(e).__name__} - {e}")
        traceback.print_exc()

    finally:
        if pya:
            print("Terminating PyAudio in main finally.")
            pya.terminate()
        print("Application finished.")