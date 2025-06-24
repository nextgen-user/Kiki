from google.genai import types
from google import genai
import time
import sys
sys.path.insert(1, '/home/pi/emo_v3/kiki-2025-03-06/')
from ast import literal_eval
client = genai.Client(api_key="AIzaSyDtP05TyoIy9j0uPL7_wLEhgQEE75AZQSc")
from pydantic import BaseModel
import threading
import subprocess
import RPi.GPIO as GPIO
from  mcp_handlers.robot_control.robot_control import turn_left,turn_right,forward,backward,stop,activate
activate()
TRIG=26
ECHO=13
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)
def measure_distance():
    time.sleep(0.2)
    GPIO.output(TRIG,True)
    time.sleep(0.00001)
    GPIO.output(TRIG,False)
    while GPIO.input(ECHO)==0:
        pulse_start=time.time()
    while GPIO.input(ECHO)==1:
        pulse_end=time.time()
        
    pulse_duration=pulse_end-pulse_start
    distance=pulse_duration*17150
    distance=round(distance,2)
    return distance
def take_image(string):
    subprocess.call(" ffmpeg -i 'http://localhost:5000/mjpeg' -frames:v 1 -f image2 -vf"+ f" drawtext=text='{string}':fontcolor=black:fontsize=25:x=40:y=50: "+" /home/pi/emo_v3/kiki-2025-03-06/media/selfie.jpeg  -y",shell=True)
    
class Direction(BaseModel):
    response: str
    direction: str
    degree:str

chat = client.chats.create(model="gemini-2.5-flash-preview-05-20"   , config=types.GenerateContentConfig(
        system_instruction="You are a robot that can move in multiple directions.Possible directions are `FORWARD,TURN_RIGHT,TURN_LEFT,NONE` and possible degree is between [0,180].When directions is `FORWARD` , the robot will move forward in a straight path till it encounters the obstacle/wall in front.Thus degree is set to 'none'.if the direction is `TURN_LEFT,TURN_RIGHT`, the robot will turn left/right the specified amount of degree.",response_mime_type= "application/json",response_schema= list[Direction]),)
video_file = client.files.upload(file="/home/pi/emo_v3/kiki-2025-03-06/indoor_pos_data/livestream_output2.avi")
while video_file.state.name == "PROCESSING":
    print('.', end='')
    time.sleep(1)
    video_file = client.files.get(name=video_file.name)
response = chat.send_message(message=[video_file,"The following is a video of my house showing various objects and locations.Remember this.Do not make any movments right now."])
print(response.text)
while True:
    take_image("Current_location")
    video_file = client.files.upload(file="/home/pi/emo_v3/kiki-2025-03-06/media/selfie.jpeg")
    while video_file.state.name == "PROCESSING":
        print('.', end='')
        time.sleep(1)
        video_file = client.files.get(name=video_file.name)
    response = chat.send_message(message=[video_file,"This is the current location of the robot after the previous movements.Proceed with moving towards the bedroom."])
    for responses in literal_eval(response.text):
        print(responses)
        print(responses["response"])
        direction = responses["direction"]
        degree = responses["degree"]
        print(f"Moving in direction: {direction} for {degree} seconds")
        input("APPROVE?")
        if direction != "NONE":
            if direction== "FORWARD":
                while True:
                    distance=measure_distance()
                    if distance> 100:
                        forward()
                    else:
                        stop()
                        time.sleep(1)
                        break
            elif direction == "BACKWARD":
                while True:
                    distance=measure_distance()
                    if distance> 100:
                        backward()
                    else:
                        stop()
                        time.sleep(1)
                        break
            elif direction == "TURN_LEFT":
                time.sleep(1)
                turn_left(int(degree))
                time.sleep(8)
            elif direction == "TURN_RIGHT":
                time.sleep(1)
                turn_right(int(degree))
                time.sleep(8)


            
        
    

# from Misc.basics import move, record_video
# record_video(1)
