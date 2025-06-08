from google.genai import types
from google import genai
import time
import sys
sys.path.insert(1, '/home/pi/emo_v3/kiki-2025-03-06/')
from ast import literal_eval
from Misc.basics import move, record_video
client = genai.Client(api_key="AIzaSyDtP05TyoIy9j0uPL7_wLEhgQEE75AZQSc")
from pydantic import BaseModel

class Direction(BaseModel):
    response: str
    direction: str
    STEPS: str 

chat = client.chats.create(model="gemini-2.5-flash-preview-05-20"   , config=types.GenerateContentConfig(
        system_instruction="You are a robot that can move in multiple directions.Always move backward first if you think that you are too near an object to avoid crashing into it.You must move backward as well if you cannot understand the current state of surroundings from the image.Possible directions are `FORWARD,BACKWARD,STEER_RIGHT,STEER_LEFT,NONE` and possible steps are`1,2,NONE`.WHen directions are `FORWARD,BACKWARD,STEER_RIGHT,STEER_LEFT` STEPS cannot be none",response_mime_type= "application/json",response_schema= list[Direction]),)
video_file = client.files.upload(file="/home/pi/emo_v3/kiki-2025-03-06/indoor_pos_data/livestream_output2.avi")
while video_file.state.name == "PROCESSING":
    print('.', end='')
    time.sleep(1)
    video_file = client.files.get(name=video_file.name)
response = chat.send_message(message=[video_file,"The following is a video of my house showing various objects and locations.Remember this.Do not make any movments right now."])
print(response.text)
while True:
    video_file = client.files.upload(file="/home/pi/emo_v3/kiki-2025-03-06/indoor_pos_data/livestream_output.avi")
    while video_file.state.name == "PROCESSING":
        print('.', end='')
        time.sleep(1)
        video_file = client.files.get(name=video_file.name)
    response = chat.send_message(message=[video_file,"This is the current location of the robot after the previous movements.Proceed with moving towards the bedroom."])
    for responses in literal_eval(response.text):
        print(responses)
        print(responses["response"])
        direction = responses["direction"]
        steps = responses["STEPS"]
        print(f"Moving in direction: {direction} for {steps} seconds")
        input("APPROVE?")
        if direction != "NONE":
            move(direction)
            record_video(int(steps))
            move("STOP")

            
        
    

# from Misc.basics import move, record_video
# record_video(1)
