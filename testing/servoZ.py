
# # We imports the GPIO module
# import RPi.GPIO as GPIO
# # We import the command sleep from time
# from time import sleep

# # Stops all warnings from appearing
# GPIO.setwarnings(False)

# # We name all the pins on BOARD mode
# GPIO.setmode(GPIO.BOARD)
# # Set an output for the PWM Signal
# GPIO.setup(12, GPIO.OUT)
# GPIO.setup(16, GPIO.OUT)

# # Set up the PWM on pin #16 at 50Hz
# pwm = GPIO.PWM(12, 50)
# pwm1 = GPIO.PWM(16, 50)

# pwm.start(0) # Start the servo with 0 duty cycle ( at 0 deg position )
# pwm1.start(0) # Start the servo with 0 duty cycle ( at 0 deg position )
# # Tells the servo to turn to the neutral position ( at 0 deg position )
# sleep(0.5) # Tells the servo to Delay for 5sec

# pwm.ChangeDutyCycle(5) # Tells the servo to turn to the left ( -90 deg position )
# pwm1.ChangeDutyCycle(5)
# # sleep(0.5) # Tells the servo to Delay for 5sec
# # pwm.ChangeDutyCycle(7.5) # Tells the servo to turn to the neutral position ( at 0 deg position )
# # pwm1.ChangeDutyCycle(7.5)

# sleep(0.5) # Tells the servo to Delay for 5sec
# # pwm.ChangeDutyCycle(10) # Tells the servo to turn to the right ( +90 deg position )
# # pwm1.ChangeDutyCycle(10)

# # sleep(0.5) # Tells the servo to Delay for 5sec
# pwm.stop(0) # Stop the servo with 0 duty cycle ( at 0 deg position )
# pwm1.stop(0)

# GPIO.cleanup() # Clean up all the ports we've used.
from gpiozero import AngularServo
from time import sleep

servo1 = AngularServo(23,   min_pulse_width=0.0006, max_pulse_width=0.0023)
servo2 = AngularServo(18, min_pulse_width=0.0006, max_pulse_width=0.0023)
# sleep(1)
# servo2.angle=90
# servo1.angle = 90

#18,23
while (True):
    servo1.angle = 90
    servo2.angle = 90

    print("Servo angle set to 90 degrees")
    sleep(2)
    servo1.angle = 20
    servo2.angle = -10

    print("Servo angle set to 0 degrees")

    sleep(2)
    servo1.angle = -90
    servo2.angle = -90

    sleep(2)
    print("Servo angle set to -90 degrees")
