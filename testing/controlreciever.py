import time
from flask import Flask, render_template,request,redirect,url_for,Response
import subprocess
app = Flask(__name__)
import requests
from importlib import reload
import sys
sys.path.insert(1, '/home/pi/emo_v3/kiki-2025-03-06/')
import tracking.motorkit_robot as motorkit_robot
robot = motorkit_robot.Robot(left_trim=0, right_trim=0)
import serial
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
ser.reset_input_buffer()

from memory import memory
m = memory.Memory()
import RPi.GPIO as GPIO 
GPIO.setmode(GPIO.BCM) 
Relay1_GPIO = 18

GPIO.setup(Relay1_GPIO, GPIO.OUT)


#CHECK IF CAMERA AVAILABLE
# p = subprocess.run("fswebcam -r 640x480 --jpeg 85 -D 0.8 web-cam-shot.jpg", capture_output=True, text=True,shell=True)  
# command = "fswebcam -r 640x480 --jpeg 85 -D 0.8 web-cam-shot.jpg"
# out = subprocess.run(command, capture_output=True, text=True,shell=True)
# time.sleep(1)
# out = str(out)
# print(f"output --> {out}")
# if "stat: No such file or directory" in out:
    # subprocess.Popen("play ~/Inta_Robo2/soundeffects/thunder.mp3",shell=True)
    # time.sleep(4)
    # # subprocess.Popen("reboot",shell=True)

isreload = False


TOKEN = "5182224145:AAEjkSlPqV-Q3rH8A9X8HfCDYYEQ44v_qy0"

def play(player):
    global m
    global isreload

    runner = m.get_data(player)
    try:
        for i in range(0,len(list(runner[0])),1):
            if list(runner[0])[i] == "F":
                robot.forward(0.6,runner[1][i])
            elif list(runner[0])[i] == "B":
                robot.backward(0.6,runner[1][i])
            elif list(runner[0])[i] == "L":
                robot.left(0.6,runner[1][i])
            elif list(runner[0])[i] == "R":
                robot.right(0.6,runner[1][i])
            elif list(runner[0])[i] == "S":
                robot.stop()
            time.sleep(1)
            if isreload :
                reload(motorkit_robot)
                isreload = False
                robot.stop()
    except Exception as e:

        print(e)
        isreload = True
        print(e)



@app.route("/")
def hello_world():
    return """
    <body style="background: black;">
        <div style="width: 240px; margin: 0px auto;">
            <img src="/mjpeg" />
        </div>
    </body>
    """
# setup camera and resolution


@app.route("/move")
def move():
    global isreload
    global turns
    global timed
    global times
    direction = request.args.get('dir')
    try:

        if direction == "F":
            robot.forward(1)
        elif direction == "B":
            robot.backward(1)
        elif direction == "R":
            ser.write(b"BACKWARD\n")
            robot.right(1)
        elif direction == "L":
            ser.write(b"FORWARD\n")
            robot.left(1)   
        elif direction == "L1":
            robot.right(0.4,0.07)
        elif direction == "R1":
            robot.left(0.4,0.07)
        elif direction == "R2":
            robot.steer(0.4,0.1)


        elif direction == "L2":
            robot.steer(0.4,-0.1)
        else:
            robot.stop()
            ser.write(b"STOP\n")
        if isreload :
            print("E OCCURED")


            reload(motorkit_robot)
            isreload = False
            robot.stop()
    except Exception as e:
        print("E OCCURED")
        GPIO.output(Relay1_GPIO, GPIO.LOW)  

        print(e)
        isreload = True
        print(e)
    return "Success"



@app.route("/action")
def action():
    global turns
    global timed
    global m
    action = request.args.get('type')
    if action=="1":
        GPIO.output(Relay1_GPIO, GPIO.LOW)  
        print("SUCCESS")

 
    elif action == "2": 
        print(turns)
        print(timed)
        m.update_data('drawing-tv', [turns,timed])
        m.save()
    elif action == "3": 
        play('drawing-tv')
    elif action == "4":
        reload(motorkit_robot)
        turns = ""
        timed = []
        times = 0
    if action=="5":
        GPIO.output(Relay1_GPIO, GPIO.HIGH)  
    return "Success"



        


    

app.run(host='0.0.0.0',port=8501, threaded=True)
