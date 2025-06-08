from tendo import singleton
current_instance = singleton.SingleInstance()
import time
import matplotlib.pyplot as plt
import cv2
from flask import Flask, render_template,request,redirect,url_for,Response
import subprocess
# warnings.filterwarnings("error")
app = Flask(__name__)
import requests
Broker = 'broker.hivemq.com'
sub_topic = "emo/recieve"  
from Misc.basics import basics
base = basics(1)
import argparse
parser = argparse.ArgumentParser(description='A test program.')

parser.add_argument("--tunnel", help="Prints the supplied argument.")

args = parser.parse_args()


#print(args.tunnel)


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
TOKEN = "5182224145:AAEjkSlPqV-Q3rH8A9X8HfCDYYEQ44v_qy0"
chat_id = "5075390513"


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

cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
def gather_img():
    while True:
        # time.sleep(0.1)
        _, img = cam.read()
        _, frame = cv2.imencode('.jpg', img)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')






        


# @app.route("/forward")
# def tasks():
# 	return render_template('index.html')

# @app.route("/backward")
# def tasks():
# 	return render_template('index.html')

# @app.route("/forward")
# def tasks():
# 	return render_template('index.html')
    
@app.route("/mjpeg")
def mjpeg():
    return Response(gather_img(), mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.errorhandler(404)
# def page_not_found(error):
#     print("-"*100)
#     subprocess.Popen("play ~/Inta_Robo2/soundeffects/thunder.mp3",shell=True)
#     time.sleep(8)
#     return "Hello world"
    

app.run(host='0.0.0.0',port=5000, threaded=True)
