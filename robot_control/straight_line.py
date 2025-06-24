import time
import board
from adafruit_motorkit import MotorKit
import smbus3 as smbus  # Use smbus3 as per your example

# --- 1. MPU6050 CONFIGURATION (from your smbus example) ---

# MPU6050 Registers
PWR_MGMT_1   = 0x6B
GYRO_CONFIG  = 0x1B
GYRO_ZOUT_H  = 0x47 # Z-axis gyro high byte

# I2C Communication
DEVICE_ADDRESS = 0x68  # MPU6050 device address

# Gyro Sensitivity (from datasheet for +/- 250 deg/s range)
# This matches the original Arduino code's logic.
GYRO_SENSITIVITY = 131.0

# Initialize SMBus
# Use bus 1 for modern Raspberry Pi models
bus = smbus.SMBus(1)

# --- 2. ROBOT CONFIGURATION & STATE VARIABLES ---

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

# Initialize MotorKit
kit = MotorKit(address = 0x6F)

# --- 3. HELPER FUNCTIONS ---

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
    print(left_speed,right_speed)
    
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

def calc_yaw():
    """Calculates yaw in degrees by integrating the gyroscope's angular velocity."""
    global yaw, last_time
    
    current_time = time.monotonic()
    dt = current_time - last_time
    last_time = current_time
    
    # Read the raw Z-axis angular velocity
    raw_gyro_z = read_raw_data(GYRO_ZOUT_H)
    
    # Calculate the angular velocity in degrees per second
    # 1. Subtract the offset to remove drift
    # 2. Divide by sensitivity to convert LSB to deg/s
    angular_velocity_z = (raw_gyro_z - gyro_z_offset) / GYRO_SENSITIVITY
    
    # Hysteresis: Ignore very small values (similar to original Arduino code)
    if abs(angular_velocity_z) < 0.05:
        angular_velocity_z = 0.0
        
    # Integrate to get the angle (yaw) in degrees
    yaw += angular_velocity_z * dt

def drive_straight(speed):
    """Drives the robot and applies P-control correction to maintain a straight line."""
    calc_yaw()
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




# --- 4. MAIN EXECUTION LOOP ---

if __name__ == "__main__":
    try:
        # Initialize hardware
        mpu_init()

        if True:

            calibrate_gyro()
            
            # Reset yaw and timer before starting the main loop
            yaw = 0.0
            last_time = time.monotonic()
            
            print("\n*** Starting straight line test ***")

            
                # --- Go Forward for 2.5 seconds ---
            print("Moving FORWARD for 2.5 seconds...")
            start_time = time.monotonic()
            while time.monotonic() - start_time < 3:
                drive_straight(BASE_SPEED)
                time.sleep(0.01)

            print(f"  -> Final Yaw: {yaw:.2f} degrees")
            print("-" * 20)
            
            # Halt for a moment to see the stop
            halt()

            time.sleep(1.0)
            

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    finally:
        # IMPORTANT: Stop the motors on exit

        halt()