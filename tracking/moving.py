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

time.sleep(2.0)  # allow camera sensor to warm up
tk = time.time()
flag=0
print("a")
while True:
        dist = distance()
        print(dist)
        # if dist < 25:
        #     robot.stop()
        #     count=count+1
        #     time.sleep(1)
        #     robot.backward(0.8,1)
        #     if (count%3 ==1) & (flag==0):
        #         robot.right(0.8,random.randint(0.5,1))
        #         flag=1
        #     else:
        #         robot.left(0.8,random.randint(0.5,1))
        #         flag=0
        # else:
        #     robot.forward(0.8)
        #     flag=0

         
    
    