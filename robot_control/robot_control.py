import requests
import time

FLASK_APP_URL = "http://localhost:8501"

motors_OFF=True

def send_move_command(command_value):
    """Sends a 'State' command to the Flask app."""
    params = {
        'State': command_value
    }
    response=requests.get(FLASK_APP_URL, params=params)
    print(response.text)

def send_action (command_value):
    """Sends a 'action' command to the Flask app."""
    params = {
        'type': command_value
    }
    response=requests.get(FLASK_APP_URL+"/action", params=params)
    print(response.text)

def turn_left(degree):
    send_action("6")
    time.sleep(0.1)
    send_action("L")
    time.sleep(degree*0.00866666666)
    send_action("S")
    time.sleep(0.1)
    send_action("7")
def turn_right(degree):
    send_action("6")
    time.sleep(0.1)
    send_action("R")
    time.sleep(degree*0.00866666666)
    send_action("S")
    time.sleep(0.1)
    send_action("7")

def left():

    send_action("L")
def right():

    send_action("R")
    
def forward():
    send_action("F")

def backward():
    send_action("B")

def stop():
    send_action("S")

def activate():
    send_action("5")


def deactivate():
    send_action("1")

    
# send_action("1")