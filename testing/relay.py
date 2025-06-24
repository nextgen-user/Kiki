

import RPi.GPIO as GPIO 

from time import sleep 


GPIO.setmode(GPIO.BCM) 
Relay1_GPIO = 18

GPIO.setup(Relay1_GPIO, GPIO.OUT)
GPIO.output(Relay1_GPIO, GPIO.LOW)  
sleep(1) 
GPIO.output(Relay1_GPIO, GPIO.HIGH) 
sleep(1) 
# GPIO.output(Relay1_GPIO, GPIO.LOW) 