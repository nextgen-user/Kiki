from google import genai
import time
import cv2
from google.genai import types

client = genai.Client(api_key="AIzaSyDtP05TyoIy9j0uPL7_wLEhgQEE75AZQSc")

from Misc.basics import move, record_video
    


while video_file.state.name == "PROCESSING":
    print('.', end='')
    time.sleep(1)
    video_file = client.files.get(name=video_file.name)

chat = client.chats.create(model="gemini-2.5-flash-preview-05-20"   , config=types.GenerateContentConfig(
        system_instruction="You are a cat. Your name is Neko."),)
video_file = client.files.upload(file=videopath)
response = chat.send_message("I have 2 dogs in my house.")

contents=["The following is the video recording tour of my house:", video_file]
TARGET="GO NEAR FRIDGE"

direction="STOP"
duration = 1
while True:
    move(direction)
    record_video(duration)
    move("STOP")
    video_file2 = client.files.upload(file="/home/pi/emo_v3/kiki-2025-03-06/livestream_output.avi")
    while video_file2.state.name == "PROCESSING":
        print('.', end='')
        time.sleep(1)
        video_file2 = client.files.get(name=video_file2.name)
    contents=contents.append(video_file2)

    response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[query, video_file]
    )
    


