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
import RPi.GPIO as IO
IO.setwarnings(False)
IO.setmode(IO.BCM)
IO.setup(27,IO.IN) #GPIO 3 -> Right IR out
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


def record_video(duration):
    t=time.time()
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
        if time.time() - t > duration:
            cap.release()
            out.release()
            cv2.destroyAllWindows()
            break

        # Write frame to output file
        out.write(frame)
        
def move(direction):
    global robot
    if direction == "FORWARD":
        robot.forward(0.7)
    elif direction == "BACKWARD":
        robot.backward(0.7)
    elif direction == "STEER_RIGHT":
        robot._left_speed(0.1)
        robot._right_speed(1)  
    elif direction == "STEER_LEFT":
        robot._left_speed(1)
        robot._right_speed(0.1)    
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
            elif IO.input(27) == False:
                subprocess.Popen("kill $(pgrep -f main.py)",shell = True)
                subprocess.Popen(f"kill $(pgrep -f effect{order}.mp3)",shell = True)
                stop_playing = True
                time.sleep(4)
                stop_playing = False
                order = 0
                break

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
 


        

    