from importlib import reload
import RPi.GPIO as GPIO 
import time
import time
import board
from adafruit_motorkit import MotorKit
import smbus3 as smbus

prev_measurement={}
# MPU6050 Registers
PWR_MGMT_1   = 0x6B
GYRO_CONFIG  = 0x1B
GYRO_ZOUT_H  = 0x47 
ACCEL_YOUT_H = 0x3D

# I2C Communication
DEVICE_ADDRESS = 0x68 

# Gyro Sensitivity (from datasheet for +/- 250 deg/s range)
GYRO_SENSITIVITY = 131.0
ACCEL_SENSITIVITY = 16384.0

TRIG=26
ECHO1=13#FRONT ULTRASONIC SENSOR
ECHO2=5#RIGHT ULTRASONIC SENSOR
ECHO3=6#BACK ULTRASONIC SENSOR
ECHO4=19#LEFT ULTRASONIC SENSOR
list=[ECHO1,ECHO2,ECHO3,ECHO4]

bus = smbus.SMBus(1)


# Proportional Control Constant (tune this for your robot)
KP = 15.0 # Starting with the value from the original Arduino code
G_FORCE = 9.81  # Acceleration due to gravity in m/s^2

BASE_SPEED = 0.6
MAX_SPEED = 1
MIN_SPEED = 0.2

gyro_z_offset = 0.0
yaw = 0.0  #degree
last_time = 0.0
accel_y_offset = 0.0
velocity_y = 0.0  # Velocity in m/s
distance_y = 0.0  # Distance in meters

kit = MotorKit(address = 0x6F)

Relay1_GPIO = 18
in1 = 17
in2 = 23
in3 = 27
in4 = 22
step_sleep = 0.001
step_count = 4000 # 5.625*(1/64) per step, 4096 steps is 360°
step_sequence = [[1,0,0,1],
                 [1,0,0,0],
                 [1,1,0,0],
                 [0,1,0,0],
                 [0,1,1,0],
                 [0,0,1,0],
                 [0,0,1,1],
                 [0,0,0,1]]
anchored=True
GPIO.setmode(GPIO.BCM)
GPIO.setup(Relay1_GPIO, GPIO.OUT)
GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO1,GPIO.IN)
GPIO.setup(ECHO2,GPIO.IN)
GPIO.setup(ECHO3,GPIO.IN)
GPIO.setup(ECHO4,GPIO.IN)
GPIO.setup( in1, GPIO.OUT )
GPIO.setup( in2, GPIO.OUT )
GPIO.setup( in3, GPIO.OUT )
GPIO.setup( in4, GPIO.OUT )
GPIO.setup(20, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)
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
    global anchored
    global motor_step_counter
    global step_sleep
    global step_count
    global motor_pins
    anchored=dir
    try:
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

def mpu_init():
    """Wakes up the MPU6050 and sets the gyro range."""
    # Wake up the MPU-6050, it starts in sleep mode
    bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
    time.sleep(0.1)
    
    # Set Gyroscope configuration
    # We write 0 to GYRO_CONFIG to select the +/- 250 deg/s range
    # This corresponds to the sensitivity of 131.0 LSB/(deg/s)
    bus.write_byte_data(DEVICE_ADDRESS, GYRO_CONFIG, 0)
    time.sleep(0.1)
    print("MPU6050 Initialized.")

def read_raw_data(addr):
    """Reads two bytes from the given address and returns a signed 16-bit value."""
    high = bus.read_byte_data(DEVICE_ADDRESS, addr)
    low = bus.read_byte_data(DEVICE_ADDRESS, addr + 1)
    
    # Concatenate higher and lower value
    value = (high << 8) | low
    
    # To get signed value from MPU6050
    if value > 32768:
        value = value - 65536
    return value


def set_motor_speeds(left_speed, right_speed):
    """Controls the two left and two right motors together."""
    left_speed = max(-1.0, min(1.0, left_speed))
    right_speed = max(-1.0, min(1.0, right_speed))
    
    kit.motor1.throttle = right_speed
    kit.motor2.throttle = -right_speed
    kit.motor3.throttle = left_speed
    kit.motor4.throttle = -left_speed


def calibrate_gyro():
    """Reads the gyroscope to determine the Z-axis offset (drift)."""
    global gyro_z_offset
    print("Calibrating gyroscope. Keep the robot still...")
    
    num_samples = 200
    gyro_z_sum = 0
    
    for _ in range(num_samples):
        gyro_z_sum += read_raw_data(GYRO_ZOUT_H)
        time.sleep(0.01)
        
    gyro_z_offset = gyro_z_sum / num_samples
    print(f"Calibration complete. Gyro Z-axis offset: {gyro_z_offset:.2f}")



def update_pose():
    """
    Calculates robot's current yaw, velocity, and distance by integrating sensor data.
    This function performs integration and is prone to drift over time.
    It should be called in a tight loop for accuracy.
    """
    global yaw, last_time, velocity_y, distance_y
    
    current_time = time.monotonic()
    dt = current_time - last_time
    last_time = current_time
    
    # --- Yaw Calculation (from Gyroscope) ---
    raw_gyro_z = read_raw_data(GYRO_ZOUT_H)
    angular_velocity_z = (raw_gyro_z - gyro_z_offset) / GYRO_SENSITIVITY
    
    if abs(angular_velocity_z) < 0.05: # Hysteresis to reduce drift
        angular_velocity_z = 0.0
        
    yaw += angular_velocity_z * dt
    
    # --- Distance Calculation (from Accelerometer) ---
    # NOTE: Calculating distance from an accelerometer is highly prone to
    # drift. Small measurement errors are integrated twice, leading to
    # large inaccuracies over time. This is for demonstration purposes.

    # 1. Read raw acceleration in the forward (Y) direction
    raw_accel_y = read_raw_data(ACCEL_YOUT_H)

    # 2. Calculate acceleration in m/s^2
    #    - Subtract offset to remove bias
    #    - Divide by sensitivity to get 'g's
    #    - Multiply by g-force constant to get m/s^2
    accel_y = ((raw_accel_y - accel_y_offset) / ACCEL_SENSITIVITY) * G_FORCE
    
    # Hysteresis to reduce noise/drift when stationary
    if abs(accel_y) < 0.1: # Tune this threshold based on sensor noise
        accel_y = 0.0

    # 3. Integrate acceleration to get velocity (v = v_0 + a*t)
    velocity_y += accel_y * dt

    # 4. Integrate velocity to get distance (d = d_0 + v*t)
    distance_y += velocity_y * dt
def drive_straight(speed):
    """Drives the robot and applies P-control correction to maintain a straight line."""
    update_pose()
    print(yaw)
    
    # The "error" is the current yaw angle in degrees. We want it to be 0.
    error = yaw
    
    # The correction is proportional to the error.
    # We divide KP by 100 to scale it for the throttle range (0-1) vs (0-255)
    correction = (KP / 100.0) * error
    
    # Calculate new speeds for each side
    left_speed = speed - correction
    right_speed = speed + correction
    
    # Apply speed limits
    if speed > 0: # Forward
        left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))
    else: # Backward
        left_speed = max(-MAX_SPEED, min(-MIN_SPEED, left_speed))
        right_speed = max(-MAX_SPEED, min(-MIN_SPEED, right_speed))

    set_motor_speeds(left_speed, right_speed)

def turn_right2(degree,touch=False):
    """Turns the robot right by a specified degree."""

    if touch:
        anchor(True)
    move_right()
    time.sleep(degree*0.008)
    stop_moving()
    if touch:
        anchor(False)

def turn_left2(degree,touch=False):
    """Turns the robot right by a specified degree."""
    if touch:
        anchor(True)
    move_left()
    time.sleep(degree*0.008)
    stop_moving()
    if touch:
        anchor(False)

def turn_right(degree,touch=False):
    """Turns the robot right by a specified degree."""
    global yaw,last_time

    yaw=0
    if touch:
        anchor(True)
    mpu_init()
    calibrate_gyro()
    
    move_right()
    last_time = time.monotonic()

    while True:
        update_pose()

        print("yaw",yaw)
        if abs(yaw) >= int(degree-15):
            stop_moving()
            if touch:
                anchor(False)
            print("yaw",yaw)
            return "success"
        
def turn_left(degree,touch=False):
    """Turns the robot left by a specified degree."""
    global yaw,last_time

    yaw=0
    if touch:
        anchor(True)
    mpu_init()
    calibrate_gyro()
    
    move_left()
    last_time = time.monotonic()

    while True:
        update_pose()

        print("yaw",yaw)
        if abs(yaw) >= int(degree-15):
            stop_moving()
            if touch:
                anchor(False)
            print("yaw",yaw)
            return "success"
        
def measure_distance(PINS):
    global prev_measurement
    distances={}
    for i in PINS:
        time.sleep(0.1)# for stability and to give time for the sensor to reset
        GPIO.output(TRIG,True)
        time.sleep(0.00001)
        GPIO.output(TRIG,False)
        while GPIO.input(i)==0:
            pulse_start=time.time()
        while GPIO.input(i)==1:
            pulse_end=time.time()
            
        pulse_duration=pulse_end-pulse_start
        distance=pulse_duration*17150
        distance=round(distance,2)
        distances[str(i)]=distance
    return distances

def calibrate_accelerometer():
    """Reads the accelerometer to determine the Y-axis offset (bias)."""
    global accel_y_offset
    print("Calibrating accelerometer. Keep the robot still and level...")
    
    num_samples = 200
    accel_y_sum = 0
    
    for _ in range(num_samples):
        accel_y_sum += read_raw_data(ACCEL_YOUT_H)
        time.sleep(0.01)
        
    accel_y_offset = accel_y_sum / num_samples
    print(f"Calibration complete. Accel Y-axis offset: {accel_y_offset:.2f}")

def move_right():

    GPIO.output(20, True)
    GPIO.output(21, False)  

def move_left():

    GPIO.output(21, True)
    GPIO.output(20, False)  



def stop_moving():
    GPIO.output(20, GPIO.LOW)
    GPIO.output(21, GPIO.LOW)  
    set_motor_speeds(0, 0)

def move_till_obstacle(distance,direction):
    """Moves the robot  until an obstacle is detected."""
    mpu_init()
    calibrate_gyro()
    calibrate_accelerometer()
    global distance_y, yaw,last_time
    distance_y = 0.0
    yaw = 0.0
    last_time = time.monotonic()
    stopped=time.time()

    i=0
    while True:
        if direction:
            distances = measure_distance([ECHO1])
            print(distances)
            if distances['13']<=distance :
                stop_moving()
                print("Analysing surroundings")
                
            if time.time()-stopped>2 and distances['13']<=distance:
                stop_moving()
                print(f"  -> Final Yaw: {yaw:.2f} degrees")
                print(f"  -> Estimated Distance: {distance_y:.2f} meters")
                break
            elif distances['13']>distance:
                drive_straight(BASE_SPEED)
                time.sleep(0.01)  
                stopped=time.time()

        else:
            distances = measure_distance([ECHO1])
            print(distances)
            if distances['6']<distance :
                stop_moving()
                print(f"  -> Final Yaw: {yaw:.2f} degrees")
                print(f"  -> Estimated Distance: {distance_y:.2f} meters")
                break
            else:
                drive_straight(-BASE_SPEED)
                time.sleep(0.01)

def move_distance(distance,direction):
    """Moves the robot forward distance."""
    mpu_init()
    calibrate_gyro()
    calibrate_accelerometer()
    global distance_y, yaw,last_time
    distance_y = 0.0
    yaw = 0.0
    last_time = time.monotonic()

    while True:
        if direction:
            distances = measure_distance([ECHO1])
            print(distance_y)
            # if distances['13']<100 :
            #     stop_moving()
            #     print(f"  -> AUTOMATIC CRASH PREVENTION: Obstacle detected at {distances['13']} cm")

            #     print(f"  -> Final Yaw: {yaw:.2f} degrees")
            #     print(f"  -> Estimated Distance: {distance_y:.2f} meters")
            #     break
            if abs(distance_y) >= distance:
                stop_moving()
                print(f"  -> Final Yaw: {yaw:.2f} degrees")
                print(f"  -> Estimated Distance: {distance_y:.2f} meters")
                break
            else:
                drive_straight(BASE_SPEED)
                time.sleep(0.01)  
        else:
            distances = measure_distance([ECHO1])
            print(distance_y)
            # if distances['6']<100 :
            #     stop_moving()
            #     print(f"  -> AUTOMATIC CRASH PREVENTION: Obstacle detected at {distances['13']} cm")

            #     print(f"  -> Final Yaw: {yaw:.2f} degrees")
            #     print(f"  -> Estimated Distance: {distance_y:.2f} meters")
            #     break
            if abs(distance_y) >= distance:
                stop_moving()
                print(f"  -> Final Yaw: {yaw:.2f} degrees")
                print(f"  -> Estimated Distance: {distance_y:.2f} meters")
                break
            else:
                drive_straight(-BASE_SPEED)
                time.sleep(0.01)

def move_till_doorway(dorway_distance,doorway_direction):
    """Moves the robot until it detects a doorway."""
    mpu_init()
    calibrate_accelerometer()

    global distance_y, yaw,last_time
    distance_y = 0.0
    yaw = 0.0
    last_time = time.monotonic()
    while True:
        distances = measure_distance(list)
        print(distances)
        if distances['13']<100 :
            stop_moving()
            print(f"  -> AUTOMATIC CRASH PREVENTION: Obstacle detected at {distances['13']} cm")
            print(f"  -> Final Yaw: {yaw:.2f} degrees")
            print(f"  -> Estimated Distance: {distance_y:.2f} meters")
            break
        if doorway_direction=="RIGHT" and distances['5']>=dorway_distance :
            stop_moving()
            print("DOORWAY DETECTED(RIGHT)")

            print(f"  -> Final Yaw: {yaw:.2f} degrees")
            print(f"  -> Estimated Distance: {distance_y:.2f} meters")
            break
        if doorway_direction=="LEFT" and distances['19']>=dorway_distance :
            stop_moving()
            print("DOORWAY DETECTED(LEFT)")
            print(f"  -> Final Yaw: {yaw:.2f} degrees")
            print(f"  -> Estimated Distance: {distance_y:.2f} meters")
            break
        else:
            drive_straight(BASE_SPEED)
            time.sleep(0.01)