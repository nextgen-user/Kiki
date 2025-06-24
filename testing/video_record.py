# import threading
# import Misc.basics as BASICS

# import time
# t=(threading.Thread(target=BASICS.record_video))
# t.start()
# time.sleep(4)
# BASICS.stop=True
# time.sleep(1)
# t.join()

# print("EXITING..")
from google.genai import types
from google import genai
import time
client = genai.Client(api_key="AIzaSyDtP05TyoIy9j0uPL7_wLEhgQEE75AZQSc")
from pydantic import BaseModel
import threading
import Misc.basics as BASICS

class RESPONSE(BaseModel):
    query: str
    human_in_image: bool

chat = client.chats.create(model="gemini-2.5-flash-preview-05-20"   , config=types.GenerateContentConfig(
        system_instruction="Helpful assistant",response_mime_type= "application/json",response_schema= list[RESPONSE]),)
video_file = client.files.upload(file="/home/pi/emo_v3/kiki-2025-03-06/image.jpg")
response = chat.send_message(message=[video_file,"Based on this image , start a humorous conversation with the user by asking a question to the user."])
print(response.text)
# fswebcam -d /dev/video0 -D 2 -S 2 -r 1280x720 image.jpg