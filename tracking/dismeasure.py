# import socket
# import time
# from imutils.video import VideoStream
# import imagezmq
# sender = imagezmq.ImageSender(connect_to='tcp://100.82.37.16:5555')
# rpi_name = socket.gethostname() # send RPi hostname with each image
# picam = VideoStream(usePiCamera=False).start()
# time.sleep(2.0)
# while True:  
#     image = picam.read()
#     sender.send_image(rpi_name, image)
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(14, GPIO.OUT)
pwm=GPIO.PWM(14, 50)
pwm.start(0)
def SetAngle(angle):

	duty = angle / 18 + 2

	GPIO.output(14, True)

	pwm.ChangeDutyCycle(duty)

	time.sleep(1)

	GPIO.output(14, False)

	pwm.ChangeDutyCycle(0)
SetAngle(100)  
time.sleep(1)
SetAngle(0)  