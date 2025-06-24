from shutil import move
import socket
import time
import imagezmq
from imutils.video import VideoStream
import codecs  
import tracking.motorkit_robot as motorkit_robot
import RPi.GPIO as GPIO
from time import sleep
import random
import RPi.GPIO as GPIO
from time import sleep
test_list = [70,170,20]

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO_TRIGGER = 18
GPIO_ECHO = 24
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
pwm=GPIO.PWM(17, 50)
pwm.start(0)
count=0
def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)
 
    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance = (TimeElapsed * 34300) / 2
 
    return distance

def SetAngle(angle,no):

	duty = angle / 18 + 2

	GPIO.output(no, True)

	pwm.ChangeDutyCycle(duty)

	sleep(1)

	GPIO.output(no, False)

	pwm.ChangeDutyCycle(0)

LEFT_TRIM = 0
RIGHT_TRIM = 0
robot = motorkit_robot.Robot(left_trim=LEFT_TRIM, right_trim=RIGHT_TRIM)
newt = 0
sender = imagezmq.ImageSender(connect_to='tcp://intense-bastion-75103.herokuapp.com:5555')
check = True
rpi_name = socket.gethostname()
picam = VideoStream(usePiCamera=False).start()
time.sleep(2.0)  # allow camera sensor to warm up
tk = time.time()
SetAngle(80,17)
flag=0
counter = 1
while True:
    image = picam.read()
    reply_hub = sender.send_image(rpi_name, image)  
    movement = reply_hub.decode()
    print(movement)
    if "forward" in movement:
        robot.forward(0.7)
        check = False
        counter = counter - 0.1
        print(counter)
    elif "idle" in movement:
        robot.stop()
        check = False
    elif "None" in movement:
        robot.stop()
        # dist = distance()
        # if dist < 20:
        #     count=count+1
        #     time.sleep(1)
        #     robot.backward(0.6,1)
        #     time.sleep(1.5)
        #     if (count%3 ==1) & (flag==0):
        #         robot.right(0.8,0.2)
        #         flag=1
        #     else:
        #         robot.left(0.8,0.2)
        #         flag=0
        # dist = distance()
        # print(dist)
        # if dist < 40:
        #     print("object detected")
        #     robot.steer(-0.8,-0.3)
        #     time.sleep(0.5)
        #     robot.stop()
        # else:
        #     if time.time() - tk > 1:
        #         rand = random.choice(test_list)
        #         SetAngle(rand,17)
        #         tk = time.time()
    elif "right_turn" in movement:
        robot.steer(0.7,-0.2)
        check = False
    elif "left_turn" in movement:
        robot.steer(0.7,0.2)
        check = False
        print("a")
    elif "Direction_right" in movement:
        robot.right(0.7)
    elif "Direction_left" in movement:
        robot.left(0.7)
    
         
    
    