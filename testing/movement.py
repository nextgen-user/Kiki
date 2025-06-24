import RPi.GPIO as GPIO
from  mcp_handlers.robot_control.robot_control import turn_left,turn_right,forward,backward,stop,activate,deactivate
import time
import threading
activate()
time.sleep(1)
turn_right(90)
time.sleep(8)
deactivate()