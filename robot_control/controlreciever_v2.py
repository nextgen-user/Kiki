import time
from flask import Flask, render_template,request,redirect,url_for,Response
app = Flask(__name__)
from importlib import reload
import sys
sys.path.insert(1, '/home/pi/emo_v3/kiki-2025-03-06/')
import tracking.motorkit_robot as motorkit_robot
robot = motorkit_robot.Robot(left_trim=0, right_trim=0)


from memory import memory
m = memory.Memory()

import RPi.GPIO as GPIO 
GPIO.setmode(GPIO.BCM) 
Relay1_GPIO = 18
in1 = 17
in2 = 23
in3 = 27
in4 = 22
anchored=True

GPIO.setup(Relay1_GPIO, GPIO.OUT)
step_sleep = 0.001
step_count = 4000 # 5.625*(1/64) per step, 4096 steps is 360°
step_sequence = [[1,0,0,1],
                 [1,0,0,0],
                 [1,1,0,0],
                 [0,1,0,0],
                 [0,1,1,0],
                 [0,0,1,0],
                 [0,0,1,1],
                 [0,0,0,1]]
GPIO.setmode( GPIO.BCM )
GPIO.setup( in1, GPIO.OUT )
GPIO.setup( in2, GPIO.OUT )
GPIO.setup( in3, GPIO.OUT )
GPIO.setup( in4, GPIO.OUT )
GPIO.setup(20, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)
# initializing
GPIO.output( in1, GPIO.LOW )
GPIO.output( in2, GPIO.LOW )
GPIO.output( in3, GPIO.LOW )
GPIO.output( in4, GPIO.LOW )


motor_pins = [in1,in2,in3,in4]
motor_step_counter = 0 

def cleanup():
    GPIO.output( in1, GPIO.LOW )
    GPIO.output( in2, GPIO.LOW )
    GPIO.output( in3, GPIO.LOW )
    GPIO.output( in4, GPIO.LOW )

    GPIO.cleanup()

def anchor(dir):
    global anchored
    global motor_step_counter
    global step_sleep
    global step_count
    global motor_pins
    anchored=dir
    try:
        i = 0
        for i in range(step_count):
            for pin in range(0, len(motor_pins)):
                GPIO.output( motor_pins[pin], step_sequence[motor_step_counter][pin] )
            if dir==True:
                motor_step_counter = (motor_step_counter - 1) % 8
            elif dir==False:
                motor_step_counter = (motor_step_counter + 1) % 8
            else: # defensive programming
                print( "uh oh... direction should *always* be either True or False" )
                cleanup()
                exit( 1 )
            time.sleep( step_sleep )
    except Exception as e:      
        print("Error in anchor function:", e)
        cleanup()
    motor_step_counter=0

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
                GPIO.output(20, GPIO.LOW )
                GPIO.output(21,  GPIO.LOW)
            time.sleep(1)
            if isreload :
                reload(motorkit_robot)
                isreload = False
                robot.stop()
    except Exception as e:

        print(e)
        isreload = True
        print(e)


lighton=False
@app.route("/")
def move():
    global lighton
    global isreload
    global turns
    global timed
    global times
    global anchored
    global changed_dir
    direction = request.args.get('State')
    print(direction)
    try:
        if direction == "V":
            if not lighton:
                GPIO.output(Relay1_GPIO, GPIO.HIGH)  
                print("SUCCESS")
                lighton=True
            else:
                GPIO.output(Relay1_GPIO, GPIO.LOW)  
                print("SUCCESS")
                lighton=False

            
        # if (direction == "F"or direction == "B") and (not anchored):
        #     robot.stop()

        #     anchor(True)

        #     print(f"LIFTING {True}")
        #     GPIO.output(20, GPIO.LOW )
        #     GPIO.output(21,  GPIO.LOW)
        #     robot.stop()
        #     direction = "S"
        # elif (direction == "L" or direction == "R") and( anchored):
        #     GPIO.output(20, GPIO.LOW )
        #     GPIO.output(21,  GPIO.LOW)
        #     anchor(False)
        #     print(f"LIFTING {False}")
        #     direction = "S"
        #     GPIO.output(20, GPIO.LOW )
        #     GPIO.output(21,  GPIO.LOW)

        elif direction == "F" : 
            robot.forward(0.7)
        elif direction == "B":
            robot.backward(0.7) 
        elif direction == "L" :
            # robot.right(1)
            GPIO.output(20, False)
            GPIO.output(21, True) 
        elif direction == "R":
            # robot.left(1) 
            GPIO.output(20, True)
            GPIO.output(21, False)  
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
            direction = "S"
            GPIO.output(20, GPIO.LOW )
            GPIO.output(21,  GPIO.LOW)



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
    global isreload
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
    elif action=="5":
        GPIO.output(Relay1_GPIO, GPIO.HIGH) 
    elif action=="6":
        anchor(True)   

    elif action=="7":
        anchor(False)
        # GPIO.output(20, False)
        # GPIO.output(21, True)  
        # time.sleep(0.8)
        # GPIO.output(20, GPIO.LOW)
        # GPIO.output(21, GPIO.LOW)  
        # anchor(True)
    elif action=="8":
        anchor(False)
        GPIO.output(20, True)
        GPIO.output(21, False)  
        time.sleep(0.8)
        GPIO.output(20, GPIO.LOW)
        GPIO.output(21, GPIO.LOW)  
        anchor(True)
    try:


        if action == "F" : 
            robot.forward(0.7)
        elif action == "B":
            robot.backward(0.7) 
        elif action == "L" :
            GPIO.output(20, False)
            GPIO.output(21, True) 
        elif action == "R":
            GPIO.output(20, True)
            GPIO.output(21, False)  

        
        else:
            robot.stop()
            GPIO.output(20, GPIO.LOW )
            GPIO.output(21,  GPIO.LOW)



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



@app.route("/auto_move")
def auto_move():
    global turns
    global timed
    global m
    global isreload
    action = request.args.get('type')
    try:


        if action == "F" : 
            robot.forward(0.7)
        elif action == "B":
            robot.backward(0.7) 
        elif action == "L" :
            GPIO.output(20, False)
            GPIO.output(21, True) 
        elif action == "R":
            GPIO.output(20, True)
            GPIO.output(21, False)  

        
        else:
            robot.stop()
            GPIO.output(20, GPIO.LOW )
            GPIO.output(21,  GPIO.LOW)



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



    

app.run(host='0.0.0.0',port=8501, threaded=True)
