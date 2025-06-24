#!/usr/bin/env python3
import serial
import time
import RPi.GPIO as GPIO 

from time import sleep 


GPIO.setmode(GPIO.BCM) 
Relay1_GPIO = 18

GPIO.setup(Relay1_GPIO, GPIO.OUT)
GPIO.output(Relay1_GPIO, GPIO.HIGH)
if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.reset_input_buffer()
    sleep(3)
    if True:

        ser.write(b"FORWARD\n")
        time.sleep(0.4)
        # ser.write(b"BACKWARD\n")
        # print(ser.readline().decode('utf-8').rstrip())

        # time.sleep(1)

        ser.write(b"STOP\n")
    GPIO.output(Relay1_GPIO, GPIO.LOW)


        # line = ser.readline().decode('utf-8').rstrip()
        # print(line)
        # time.sleep(1)