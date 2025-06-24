import asyncio

import os
import traceback
from mcp_handlers.mcp_handler import MCPClient
import random
from dotenv import load_dotenv

import subprocess
import time
load_dotenv()
from memory.memory import Memory
m = Memory()
import pyaudio

from google import genai

import struct

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000  # For Gemini
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024  # For Gemini
from googletrans import Translator

import json

MODEL = "gemini-2.5-flash-exp-native-audio-thinking-dialog" # "gemini-2.5-flash-exp-native-audio-thinking-dialog" ,  "gemini-2.0-flash-live-001"

DEFAULT_MODE = "camera" # Video mode

from ._camera_frame import get_frames
from .send_text import send_text_external
from .configs_and_tools import configure,generate_config
from .porcupine_functions import _close_porcupine_resources,_init_porcupine_resources
from .context_and_toolcalls import handle_server_content,handle_tool_call
from .display import awake,sleepy,add_text,add_youtube_button,song_on,check
from .PROMPTS import system_prompt

pya = pyaudio.PyAudio()

import json 
KYE_LIST=json.loads(os.getenv("GEMINI_KEY_LIST"))
client = genai.Client(api_key=random.choice(KYE_LIST),http_options={"api_version": "v1alpha"})

translator=Translator()

# subprocess.Popen("python webcam_stream.py",shell=True)
# subprocess.Popen("python testing/controlreciever.py",shell=True)

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE):
        self.AI_answer=""
        self.USER_query=""

        self.video_mode = video_mode

        self.audio_in_queue = None
        self.out_queue = None
        self.tool_called=False
        self.stay_silent=False

        self.session = None
        self.audio_stream_in = None

        self.is_playing_audio = False
        # subprocess.Popen("python /home/pi/emo_v3/audioeffects/sleep.py", shell=True)


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
        self.add_youtube_button=add_youtube_button
        self.song_on=song_on
        self.timeout=time.time()
        sleepy()


    async def handle_display(self):
        while True:
            await asyncio.sleep(1)
            if self.AI_answer != "" and self.USER_query !="":
                # text=await translator.translate(self.USER_query, dest='en')
                await asyncio.to_thread(add_text,f"AI:{self.AI_answer}")


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




            
    async def listen_audio(self):
        global pya
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
                        # await asyncio.to_thread(sleepy)
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

                    if not await _init_porcupine_resources(self,pya):
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
                            self.stay_silent=False


                            print(f"Hotword detected! Switching to Gemini listening.")
                            subprocess.call(f"play /home/pi/emo_v3/audioeffects/{random.choice(['huh','youcalled','yes','what','shoot','okgo'])}.wav",shell=True)
                            self.listening_state = "SENDING_TO_GEMINI"
                            await _close_porcupine_resources(self,delete_instance=False) # Close stream, keep instance
                            continue
                        
                        if time.time()- self.recorded_time> 300:
                            self.recorded_time=time.time()
                            self.asked=True
                            self.stay_silent=False

                            
                            print(f"Hotword  detected! Switching to Gemini listening for asking")
                            self.listening_state = "SENDING_TO_GEMINI"
                            await self._close_porcupine_resources(delete_instance=False) # Close stream, keep instance
                            continue
                        if time.time() - self.recorded_time > 1 and self.follow_up and not self.stay_silent:
                            await self.session.send(input="SYSTEM:(Remember:Being Funny isn't optional; it's your core directive).You have only thought and not spoken anything. Please review your internal format instructions and speak to the user after the user asks the question. Here is the users question:" , end_of_turn=False)
                            
                            print("SWIITCHING TO GEMINI STATE")
                            self.AI_answer=""
                            self.USER_query=""
                            sleepy()
                            self.listening_state="SENDING_TO_GEMINI"
                            self.follow_up=False
                            self.recorded_time=time.time()         
                        await asyncio.to_thread(check)
                            



                    except IOError as e: # PyAudio stream errors
                        print(f"PyAudio error during hotword listening: {e}")
                        # This could be a more serious issue, e.g. device unplugged
                        # traceback.print_exc()
                        await _close_porcupine_resources(self,delete_instance=False) # Try to close stream
                        await asyncio.sleep(1) # Wait before retrying AWAITING_HOTWORD loop
                    except Exception as e_hotword_listen: # Catch-all for unexpected errors
                        print(f"Unexpected error during hotword listening: {e_hotword_listen}")
                        traceback.print_exc()
                        await _close_porcupine_resources(self,delete_instance=False)
                        await asyncio.sleep(1)


                    await asyncio.sleep(0.01) # Yield if no hotword

                elif self.listening_state == "SENDING_TO_GEMINI":
                    if self.porcupine_stream and self.porcupine_stream.is_active():
                        print("Ensuring Porcupine stream is closed while in Gemini mode.")
                        await _close_porcupine_resources(self,delete_instance=False)

                    if not self.audio_stream_in or not self.audio_stream_in.is_active():
                        if not mic_info:
                            print("Error: Cannot open Gemini mic stream, default input device info not available.")
                            self.listening_state = "AWAITING_HOTWORD" # Fallback
                            await asyncio.sleep(1)
                            continue
                        try:
                            print(f"Opening Gemini mic stream: {mic_info['name']} (Rate: {SEND_SAMPLE_RATE}, Chunk: {CHUNK_SIZE})")

                            if  self.asked:
                                self.mic_is_paused_for_playback=True
                                gemini_mic_stream_active=False
                                self.asked=False
                                await self.session.send(input="SYSTEM:Ask the user a question to entertain him/her related to what you see.." or ".", end_of_turn=True)
                                awake()

                            else:
                                self.timeout=time.time()
                                self.audio_stream_in = await asyncio.to_thread(
                                    pya.open,
                                    format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
                                    input=True, input_device_index=mic_info["index"],
                                    frames_per_buffer=CHUNK_SIZE,
                                )
                                awake()

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

                    if time.time()-self.timeout> 60 and ( not self.mic_is_paused_for_playback) and self.audio_stream_in and self.audio_stream_in.is_active():
                        print("timed out waiting for response...")
                        await asyncio.to_thread(self.audio_stream_in.stop_stream)
                        # self.mic_is_paused_for_playback = True
                        self.listening_state = "AWAITING_HOTWORD"
                        self.stay_silent=True
                        
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

            await _close_porcupine_resources(self,delete_instance=True) # Close stream and delete instance
            print("listen_audio task finished cleanup.")



    async def receive_audio(self):
        print("Starting audio receiving task (with tool support).")
        try:
            while True:
                if not self.session or not self.audio_in_queue:
                    await asyncio.sleep(0.1)
                    print("STARTING..")
                    continue

                turn_had_audio_data = False
                turn_ended_or_interrupted = False


                try:
                    turn = self.session.receive()
                    async for response_chunk in turn:
                        self.recorded_time=time.time()
                        print(f"***{self.listening_state}***")


                        if data := response_chunk.data:
                            if self.audio_in_queue:
                                self.audio_in_queue.put_nowait(data)
                                self.listening_state="AWAITING_HOTWORD"

                            

                            turn_had_audio_data = True
                        if text := response_chunk.text:
                            # print(text, end="", flush=True)
                            pass


                        server_content = response_chunk.server_content
                        if (server_content is not None) :
                            await handle_server_content(self,server_content)

                            # continue

                        tool_call = response_chunk.tool_call
                        if tool_call is not None:
                            print("-"*100+"TOOL CALL DETECTED")
                            await handle_tool_call(self,tool_call)


                    # End of one full set of responses from the model for the current user input/turn



                except Exception as e_turn:
                    print(f"\nError processing turn in receive_audio: {e_turn}")
                    # traceback.print_exc()
                    turn_ended_or_interrupted = True # Assume turn ended on error
                    exit()

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
                    self.recorded_time=time.time()
                    await asyncio.to_thread(audio_stream_out.write, bytestream)
                except Exception as e_write:
                    print(f"Error writing to audio stream in play_audio: {e_write}")
                    # If error occurs, check queue status for state reset
                    if self.audio_in_queue.empty() and self.is_playing_audio:
                        self.is_playing_audio = False
                        # State transition will be handled by the finally block of this iteration
                finally:
                    # This block now executes regardless of exception during write
                    if self.audio_in_queue.empty() : # Check if queue is empty *after* getting an item
                        if self.is_playing_audio: # If it was playing and queue is now empty, AI finished speaking
                           print("AI audio playback finished (audio queue empty).")
                           self.is_playing_audio = False

                           self.follow_up = True

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
        tools = await configure(self)
        
        try:
            print("Connecting to Generative AI model...")
            if client is None:
                print("Error: GenAI client not initialized. Cannot run.")
                return

            # Create queues here, before session, so they are always available
            self.audio_in_queue = asyncio.Queue()
            self.out_queue = asyncio.Queue(maxsize=20) # Maxsize for backpressure

            async with client.aio.live.connect(model=MODEL, config=generate_config(tools,system_prompt)) as session:
                self.session = session
                print("Session established with Generative AI model.")

                send_text_task = asyncio.create_task(send_text_external(self), name="send_text")

                background_tasks = [
                    asyncio.create_task(self.send_realtime(), name="send_realtime"),
                    asyncio.create_task(self.listen_audio(), name="listen_audio"),
                    asyncio.create_task(self.receive_audio(), name="receive_audio"),
                    asyncio.create_task(self.play_audio(), name="play_audio"),
                    asyncio.create_task(self.handle_display(), name="handle_display"),

                ]
                if self.video_mode == "camera":
                    background_tasks.append(asyncio.create_task(get_frames(self), name="get_frames"))
                elif self.video_mode == "screen":
                    print("YET TO BE IMPLEMENTED")
                    # background_tasks.append(asyncio.create_task(self.get_screen(), name="get_screen"))

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


            await _close_porcupine_resources(self,delete_instance=True)
            self.session = None 
            print("AudioLoop run finished.")
            time.sleep(5)
            subprocess.call(" cd ~/emo_v3/kiki-2025-03-06 ; python boot.py",shell=True)


