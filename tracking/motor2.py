import tracking.motorkit_robot as motorkit_robot
import time
import serial

import RPi.GPIO as GPIO 

GPIO.setmode(GPIO.BCM) 
Relay1_GPIO = 18

GPIO.setup(Relay1_GPIO, GPIO.OUT)
GPIO.output(Relay1_GPIO, GPIO.HIGH) 

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
ser.reset_input_buffer()
time.sleep(3)
LEFT_TRIM = 0
RIGHT_TRIM = 0
robot = motorkit_robot.Robot(left_trim=LEFT_TRIM, right_trim=RIGHT_TRIM)
robot.right(1)
ser.write(b"BACKWARD\n")

time.sleep(2)
ser.write(b"STOP\n")

robot.stop()
GPIO.output(Relay1_GPIO, GPIO.LOW)  

# robot.steer(1,1)
# time.sleep(10)
# robot.stop()
# # time.sleep(1)
# robot.forward(1)
# time.sleep(1)
# robot.stop()
# robot.forward(0.8)
# time.sleep(0.3)
# robot.stop()
# time.sleep(1)

# robot.backward(0.8)
# time.sleep(0.5)
# robot.stop()
# time.sleep(1)

# robot.steer(0.8,0.8)
# time.sleep(3)
# robot.stop()
# time.sleep(0.5)

# robot.backward(0.8)
# time.sleep(1)
# robot.stop()