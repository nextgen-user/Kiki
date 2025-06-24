import RPi.GPIO as gpio
import time
gpio.setmode(gpio.BCM)
gpio.setup(20, gpio.OUT)
gpio.setup(21, gpio.OUT)
time.sleep(1)
gpio.output(20, False)
gpio.output(21, True)
time.sleep(0.1)
gpio.cleanup()