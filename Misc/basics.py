import gtts
import playsound
import subprocess
import smtplib
import time
import threading
import wave
import random
import cv2
import tracking.motorkit_robot as motorkit_robot
robot = motorkit_robot.Robot(left_trim=0, right_trim=0)
import pyaudio
import RPi.GPIO as GPIO 
GPIO.setmode(GPIO.BCM) 
Relay1_GPIO = 18
in1 = 17
in2 = 23
in3 = 27
in4 = 22
GPIO.setup(Relay1_GPIO, GPIO.OUT)
step_sleep = 0.002
step_count = 2500 # 5.625*(1/64) per step, 4096 steps is 360°
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
    global motor_step_counter
    global step_sleep
    global step_count
    global motor_pins
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
order = 0
stop_playing = False
from googletrans import Translator
from requests_futures.sessions import FuturesSession
TOKEN = "5182224145:AAEjkSlPqV-Q3rH8A9X8HfCDYYEQ44v_qy0"
chat_id = "5075390513"
session = FuturesSession()
language = "english"
hotword = "None"
TOKEN = "5182224145:AAEjkSlPqV-Q3rH8A9X8HfCDYYEQ44v_qy0"
chat_id = "5075390513"
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000 
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "/home/pi/Inta_Robo2/output.wav"
p = pyaudio.PyAudio()

stop=False

class record_audio():
    def __init__(self):
        self.recording = False
        
    def start(self):
        if self.recording: return
        try:
            self.frames = []
            self.stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK,
                            stream_callback=self.callback,input_device_index=1)
            print("Stream active:", self.stream.is_active())
            print("start Stream")
            self.recording = True
        except:
            raise

    def stop(self):
        if not self.recording: return
        self.recording = False
        print("Stop recording")
        self.stream.stop_stream()
        self.stream.close()

        with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(self.frames))
    def callback(self, in_data, frame_count, time_info, status):
        self.frames.append(in_data)
        return in_data, pyaudio.paContinue


def record_video():
    global stop
    stream_url = 'http://localhost:5000/mjpeg'
    output_filename = '/home/pi/emo_v3/kiki-2025-03-06/indoor_pos_data/livestream_output.avi'
    codec = 'MJPG'  
    fps = 20.0     
    frame_size = (320, 240)  

    cap = cv2.VideoCapture(stream_url)
    

    if not cap.isOpened():
        print("Error: Could not open stream")
        exit()

    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(output_filename, fourcc, fps, frame_size)

    while True:
        # Read frame from stream
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame")
            break
        print(stop)
        if stop:
            cap.release()
            out.release()
            cv2.destroyAllWindows()
            stop=False
            return "DONE"

        # Write frame to output file
        out.write(frame)
        
        
def move(direction):
    global robot
    if direction == "FORWARD":
        robot.forward(0.7)
    elif direction == "BACKWARD":
        robot.backward(0.7)
    elif direction == "TURN_RIGHT":
        anchor(False)
        GPIO.output(20, True)
        GPIO.output(21, False)  
        time.sleep(0.8)
        GPIO.output(20, GPIO.LOW)
        GPIO.output(21, GPIO.LOW)  
        anchor(True)
    elif direction == "TURN_LEFT":
        anchor(False)
        GPIO.output(20, False)
        GPIO.output(21, True)  
        time.sleep(0.8)
        GPIO.output(20, GPIO.LOW)
        GPIO.output(21, GPIO.LOW)  
        anchor(True)
    elif direction == "STOP":
        robot.stop()
    else:
        print("Invalid direction command. Use FORWARD, BACKWARD, RIGHT_STEER, LEFT_STEER, or STOP.")

class basics:
    
    global language
    def __init__(self, default):
           
        self.default = default            
    def changelang(self,lang):  
        global language 
        language = lang

    def reset(self):
        global order
        order = 0

    def stop(self):
        global stop
        stop=True

    def terminate(self):
        global order
        global stop_playing
        subprocess.Popen(f"kill $(pgrep -f effect{order}.mp3)",shell = True)
        stop_playing = True
        time.sleep(4)
        stop_playing = False
        order = 0
        
    def process(self,count):
        """
        function to print square of given num
        """
        global order
        global stop_playing

        # while True:
        #     if "notrunning" in (open("sample.txt","r")).read():
        #         file = open("sample.txt","w")
        #         file.write("running")
        #         file.close()
        #         subprocess.call(f"play /home/pi/effect{name}.mp3",shell=True)
        #         file = open("sample.txt","w")
        #         file.write("notrunning")
        #         file.close()
        #         break
        while True:
            if count == order:
                subprocess.call(f"play /home/pi/effect{order}.mp3",shell=True)
                order = order +1
                break
            elif stop_playing:
                break
            # elif IO.input(27) == False:
            #     subprocess.Popen("kill $(pgrep -f main.py)",shell = True)
            #     subprocess.Popen(f"kill $(pgrep -f effect{order}.mp3)",shell = True)
            #     stop_playing = True
            #     time.sleep(4)
            #     stop_playing = False
            #     order = 0
            #     break

    # Adds an instance variable 
    def speak(self,audio):  
        t = time.time()
        global language
        translator = Translator()
        
        if language == "english":
            t1 = gtts.gTTS(audio,slow=True)
            print(time.time()-t)
            t1.save("/home/pi/welcome.mp3") 
            print(time.time()-t)
    
        else:
            k = translator.translate(audio, dest='hi')
            t1 = gtts.gTTS(k.text,slow=True,lang="hi")
            t1.save("/home/pi/welcome.mp3")     
        
        subprocess.call("sox /home/pi/welcome.mp3 /home/pi/effect.mp3  pitch +500 ",shell = True)
        print(time.time()-t)
        playsound.playsound("/home/pi/effect.mp3")
        print(time.time()-t)

    def spoke(self,order,thinking,audio):  
        global TOKEN
        global chat_id
        global language
        id = order
        translator = Translator()

        if language == "english":
            t1 = gtts.gTTS(audio,slow=False)
            t1.save("/home/pi/welcome.mp3")     
        else:
            k = translator.translate(audio, dest='hi')
            t1 = gtts.gTTS(k.text,slow=False,lang="hi")
            t1.save("/home/pi/welcome.mp3")      
        subprocess.call(f"sox /home/pi/welcome.mp3 /home/pi/effect{id}.mp3  pitch +500 ",shell = True)
        subprocess.Popen("kill $(pgrep -f thinking.mp3)",shell = True)
        (threading.Thread(target=self.process, args=(id,))).start()       

    def spike(self,order,thinking,audio):  
        global TOKEN
        global chat_id
        global language
        id = order
        translator = Translator()
        session.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text=The answer is👇\n{audio}")

        if language == "english":
            t1 = gtts.gTTS(audio,slow=False)
            t1.save("/home/pi/welcome.mp3")     
        else:
            k = translator.translate(audio, dest='hi')
            t1 = gtts.gTTS(k.text,slow=False,lang="hi")
            t1.save("/home/pi/welcome.mp3")      
        subprocess.call(f"sox /home/pi/welcome.mp3 /home/pi/effect{id}.mp3  pitch +500 ",shell = True)
        subprocess.Popen("kill $(pgrep -f thinking.mp3)",shell = True)
        (threading.Thread(target=self.process, args=(id,))).start()  

    def quack(self,thinking,audio):  
        global TOKEN
        global chat_id
        global language
        translator = Translator()
        session.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text=The answer is👇\n{audio}")

        if language == "english":
            t1 = gtts.gTTS(audio,slow=False)
            t1.save("/home/pi/welcome.mp3")     
        else:
            k = translator.translate(audio, dest='hi')
            t1 = gtts.gTTS(k.text,slow=True,lang="hi")
            t1.save("/home/pi/welcome.mp3")      
        subprocess.call("sox /home/pi/welcome.mp3 /home/pi/effect.mp3  pitch +500 ",shell = True)
        try:
            thinking.kill()
        except:
            pass
        subprocess.Popen("kill $(pgrep -f thinking.mp3)",shell = True)

        playsound.playsound("/home/pi/effect.mp3")


    # Retrieves instance variable    
    def sendEmail(self,to, content):
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            
            # Enable low security in gmail
            server.login('vaibhavarduino@gmail.com', 'techi@721')
            server.sendmail('vaibhavarduino@gmail.com', to, content)
            server.close()
            return "Email Sent"
        except Exception as e:
            print(e)
 


        

    