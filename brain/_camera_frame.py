import base64
import io
import PIL.Image
import cv2
import asyncio
def drain_camera_buffer(cap, max_frames_to_drain=30):
    """
    Reads and discards all available frames from the camera buffer
    until no more frames are immediately available or a max limit is reached.
    This ensures the next 'read' will get the freshest possible frame.
    """
    frames_discarded = 0
    while frames_discarded < max_frames_to_drain:
        ret, _ = cap.read() # Read a frame, but discard it (we don't need its content)
        if not ret:
            # No more frames in buffer for now, or an error occurred
            break
        frames_discarded += 1
    # print(f"DEBUG: Discarded {frames_discarded} frames from buffer.") # Uncomment for debugging
    return frames_discarded
def _get_frame(cap):

    drain_camera_buffer(cap)
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
    x= {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}
    # file_extension = ".jpg"  
        
    # output_filename = f"/home/pi/emo_v3/kiki-2025-03-06/brain/saved_image{file_extension}"


    # with open(output_filename, "wb") as f:
    #     f.write(image_bytes)
    return x

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

            frame = await asyncio.to_thread(_get_frame, cap)
            if frame is None:
                print("get_frames: _get_frame returned None, stopping.")
                cap = await asyncio.to_thread(cv2.VideoCapture, "http://localhost:5000/mjpeg")
                continue

            if self.out_queue:
                await self.out_queue.put(frame)
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        print("get_frames task cancelled.")
    except Exception as e:
        print(f"Exception in get_frames: {e}")
    finally:
        if cap and cap.isOpened():
            print("Releasing video capture.")
            await asyncio.to_thread(cap.release)



