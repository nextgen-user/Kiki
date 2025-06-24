import RPi.GPIO as GPIO
import time
import statistics # Import the statistics library

TRIG=26
ECHO1=13
ECHO2=5
ECHO3=6
ECHO4=19
list=[ECHO2,ECHO3,ECHO4,ECHO1]
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO1,GPIO.IN)
GPIO.setup(ECHO2,GPIO.IN)
GPIO.setup(ECHO3,GPIO.IN)
GPIO.setup(ECHO4,GPIO.IN)

def measure_distance(PINS):
    distances={}
    for i in PINS:
        # print(i)
        time.sleep(0.2)# for stability and to give time for the sensor to reset
        GPIO.output(TRIG,True)
        time.sleep(0.00001)
        GPIO.output(TRIG,False)
        timeout_start = time.time()
        while GPIO.input(i)==0:
            pulse_start = time.time()
            if pulse_start - timeout_start > 0.1: # 100ms timeout
                break       
        while GPIO.input(i)==1:
            pulse_end=time.time()
            if pulse_end - pulse_start > 0.1: # Echo shouldn't last this long
                break
            
        pulse_duration=pulse_end-pulse_start
        distance=pulse_duration*17150
        distance=round(distance,2)

        distances[str(i)]=distance
    return distances

while True:
    distance=measure_distance([ECHO2])
    print(distance,flush=True)

    # if len()


    # if distance> 100:
    #     forward()
    # else:
    #     stop()
        # time.sleep(1)
        # turn_right(90)
        # time.sleep(8)
