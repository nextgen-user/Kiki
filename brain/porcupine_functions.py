import asyncio
import pvporcupine
import pyaudio
SEND_SAMPLE_RATE = 16000  # For Gemini
CHANNELS=1
FORMAT = pyaudio.paInt16

async def _init_porcupine_resources(self,pya):
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
            self.porcupine = None
            return False


    if self.porcupine and (self.porcupine_stream is None or not self.porcupine_stream.is_active()):
        print("Attempting to open Porcupine audio stream...")
        # m.update_data('currentmode', 'sleepy')
        # m.save()
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