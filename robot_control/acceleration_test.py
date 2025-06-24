import time
import board
from adafruit_motorkit import MotorKit
import smbus3 as smbus  # Use smbus3 as per your example
from robot_control import turn_left,turn_right,forward,backward,stop,activate,deactivate,send_action

# --- 1. MPU6050 CONFIGURATION (UPDATED) ---

# MPU6050 Registers
PWR_MGMT_1   = 0x6B
GYRO_CONFIG  = 0x1B
GYRO_ZOUT_H  = 0x47 # Z-axis gyro high byte
# Add Accelerometer registers (assuming Y-axis is the robot's forward direction)
ACCEL_YOUT_H = 0x3D

# I2C Communication
DEVICE_ADDRESS = 0x68  # MPU6050 device address

# Sensitivity Constants (from datasheets)
# Gyro: For +/- 250 deg/s range (set in mpu_init)
GYRO_SENSITIVITY = 131.0
# Accel: For +/- 2g range (default setting)
ACCEL_SENSITIVITY = 16384.0
G_FORCE = 9.81  # Acceleration due to gravity in m/s^2

# Initialize SMBus
# Use bus 1 for modern Raspberry Pi models
bus = smbus.SMBus(1)

# --- 2. ROBOT CONFIGURATION & STATE VARIABLES (UPDATED) ---

# Proportional Control Constant (tune this for your robot)
KP = 15.0 # Starting with the value from the original Arduino code

# Motor speed settings (throttle is from -1.0 to 1.0)
BASE_SPEED = 0.6
MAX_SPEED = 1.0
MIN_SPEED = 0.2

# Gyro and Yaw variables
gyro_z_offset = 0.0
yaw = 0.0  # Yaw will be stored in degrees
last_time = 0.0

# Accelerometer and Kinematics variables for distance tracking
accel_y_offset = 0.0
velocity_y = 0.0  # Velocity in m/s
distance_y = 0.0  # Distance in meters

# Initialize MotorKit
kit = MotorKit(address = 0x6F)

# --- 3. HELPER FUNCTIONS (UPDATED) ---

# --- MPU6050 SMBus Functions ---

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
    # The accelerometer is set to +/- 2g by default, which is what we want.
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

# --- Robot Control Functions ---

def set_motor_speeds(left_speed, right_speed):
    """Controls the two left and two right motors together."""
    left_speed = max(-1.0, min(1.0, left_speed))
    right_speed = max(-1.0, min(1.0, right_speed))
    # print(left_speed,right_speed) # Optional: uncomment for debugging
    
    kit.motor1.throttle = right_speed
    kit.motor2.throttle = -right_speed
    kit.motor3.throttle = left_speed
    kit.motor4.throttle = -left_speed

def halt():
    """Stops all motors."""
    set_motor_speeds(0, 0)
    print("Motors stopped.")

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
    update_pose() # This now calculates yaw, velocity, and distance
    
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

# --- 4. MAIN EXECUTION LOOP (UPDATED) ---

if __name__ == "__main__":
    try:
        # Initialize hardware
        mpu_init()

        if True:
            # Perform calibrations
            calibrate_gyro()
            calibrate_accelerometer()
            
            # Reset pose and timer before starting the main loop
            yaw = 0.0
            velocity_y = 0.0
            distance_y = 0.0
            last_time = time.monotonic()
            
            print("\n*** Starting straight line test ***")
            
            # --- Go Forward for 3 seconds ---
            print("Moving FORWARD for 3 seconds...")
            start_time = time.monotonic()
            while time.monotonic() - start_time < 10:
                drive_straight(BASE_SPEED)
                time.sleep(0.01)

            # Halt for a moment to see the stop
            halt()
            
            print("-" * 20)
            print(f"  -> Final Yaw: {yaw:.2f} degrees")
            print(f"  -> Estimated Distance: {distance_y:.2f} meters")
            print("-" * 20)
            
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    finally:
        # IMPORTANT: Stop the motors on exit
        send_action("7")
        halt()