import time
import board
import math
from adafruit_motorkit import MotorKit
import smbus3 as smbus

# --- 1. ROBOT PHYSICAL PARAMETERS (ACTION REQUIRED) ---
# YOU MUST MEASURE AND SET THESE VALUES FOR YOUR ROBOT
WHEEL_DIAMETER_M = 0.065  # Wheel diameter in meters (e.g., 6.5 cm)
MAX_RPM = 220             # Motor's maximum Revolutions Per Minute at your battery voltage

# --- Calculated Constants (Do not change) ---
WHEEL_CIRCUMFERENCE_M = WHEEL_DIAMETER_M * math.pi
MAX_RPS = MAX_RPM / 60.0  # Maximum Revolutions Per Second
MAX_SPEED_MPS = WHEEL_CIRCUMFERENCE_M * MAX_RPS # Max speed in Meters Per Second

print(f"Robot's calculated max speed: {MAX_SPEED_MPS:.2f} m/s")

# --- 2. MPU6050 CONFIGURATION ---
PWR_MGMT_1   = 0x6B
GYRO_CONFIG  = 0x1B
GYRO_ZOUT_H  = 0x47
DEVICE_ADDRESS = 0x68
GYRO_SENSITIVITY = 131.0
bus = smbus.SMBus(1)

# --- 3. ROBOT CONFIGURATION & STATE VARIABLES ---
# Control
KP = 15.0
BASE_SPEED = 0.6
MAX_SPEED = 1.0
MIN_SPEED = 0.2

# Gyro and Yaw State
gyro_z_offset = 0.0
yaw = 0.0  # Yaw in degrees
last_time = 0.0

# --- NEW: Distance Tracking State Variables ---
forward_distance = 0.0  # Total distance traveled along the intended path (Y-axis)
lateral_distance = 0.0  # Total drift from the path (X-axis, left/right)

# Initialize MotorKit
kit = MotorKit(address = 0x6F)

# --- 4. HELPER FUNCTIONS ---

def mpu_init():
    bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
    time.sleep(0.1)
    bus.write_byte_data(DEVICE_ADDRESS, GYRO_CONFIG, 0)
    time.sleep(0.1)
    print("MPU6050 Initialized.")

def read_raw_data(addr):
    high = bus.read_byte_data(DEVICE_ADDRESS, addr)
    low = bus.read_byte_data(DEVICE_ADDRESS, addr + 1)
    value = (high << 8) | low
    if value > 32768:
        value = value - 65536
    return value

def set_motor_speeds(left_speed, right_speed):
    left_speed = max(-1.0, min(1.0, left_speed))
    right_speed = max(-1.0, min(1.0, right_speed))
    kit.motor1.throttle = right_speed
    kit.motor2.throttle = -right_speed
    kit.motor3.throttle = left_speed
    kit.motor4.throttle = -left_speed

def halt():
    set_motor_speeds(0, 0)
    print("Motors stopped.")

def calibrate_gyro():
    global gyro_z_offset
    print("Calibrating gyroscope...")
    num_samples = 200
    gyro_z_sum = 0
    for _ in range(num_samples):
        gyro_z_sum += read_raw_data(GYRO_ZOUT_H)
        time.sleep(0.01)
    gyro_z_offset = gyro_z_sum / num_samples
    print(f"Calibration complete. Gyro Z-axis offset: {gyro_z_offset:.2f}")

def update_pose(avg_throttle, dt):
    """
    NEW FUNCTION: Updates forward and lateral distance based on speed and heading.
    This is our dead reckoning calculation.
    """
    global forward_distance, lateral_distance

    # 1. Calculate current speed in m/s based on throttle
    #    (Assumes linear relationship between throttle and speed)
    current_speed_mps = avg_throttle * MAX_SPEED_MPS

    # 2. Calculate the distance moved in this small time step
    delta_distance = current_speed_mps * dt

    # 3. Convert current yaw from degrees to radians for trig functions
    yaw_rad = math.radians(yaw)

    # 4. Decompose the distance into forward (y) and lateral (x) components
    delta_forward = delta_distance * math.cos(yaw_rad)
    delta_lateral = delta_distance * math.sin(yaw_rad)

    # 5. Add the small changes to the total distance traveled
    forward_distance += delta_forward
    lateral_distance += delta_lateral

def calc_yaw_and_update_pose(left_throttle, right_throttle):
    """
    MODIFIED: Now calculates yaw AND updates distance traveled in one step.
    """
    global yaw, last_time
    
    current_time = time.monotonic()
    dt = current_time - last_time
    
    # Don't do calculations if dt is zero
    if dt == 0:
        return

    last_time = current_time
    
    # --- Yaw Calculation (same as before) ---
    raw_gyro_z = read_raw_data(GYRO_ZOUT_H)
    angular_velocity_z = (raw_gyro_z - gyro_z_offset) / GYRO_SENSITIVITY
    if abs(angular_velocity_z) < 0.05:
        angular_velocity_z = 0.0
    yaw += angular_velocity_z * dt

    # --- NEW: Pose Update ---
    avg_throttle = (left_throttle + right_throttle) / 2.0
    update_pose(avg_throttle, dt)

def drive_straight(speed):
    """Drives the robot and applies P-control correction."""
    error = yaw
    correction = (KP / 100.0) * error
    
    left_speed = speed - correction
    right_speed = speed + correction
    
    # Apply speed limits
    if speed > 0:
        left_speed = max(MIN_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(MIN_SPEED, min(MAX_SPEED, right_speed))
    else:
        left_speed = max(-MAX_SPEED, min(-MIN_SPEED, left_speed))
        right_speed = max(-MAX_SPEED, min(-MIN_SPEED, right_speed))

    set_motor_speeds(left_speed, right_speed)
    
    # This is the new, combined function call
    calc_yaw_and_update_pose(left_speed, right_speed)

# --- 5. MAIN EXECUTION LOOP ---

if __name__ == "__main__":
    try:
        mpu_init()
        calibrate_gyro()
        
        # Reset pose and timer before starting
        yaw = 0.0
        forward_distance = 0.0
        lateral_distance = 0.0
        last_time = time.monotonic()
        
        print("\n*** Starting straight line and distance test ***")
        
        if True:
            # --- Go Forward for 2.5 seconds ---
            print("Moving FORWARD for 2.5 seconds...")
            start_time = time.monotonic()
            while time.monotonic() - start_time < 10:
                drive_straight(BASE_SPEED)
                time.sleep(0.01)

            halt()
            print(f"  -> Final Yaw: {yaw:.2f} degrees")
            print(f"  -> Distance Forward: {forward_distance:.3f} meters")
            print(f"  -> Distance Lateral: {lateral_distance:.3f} meters")
            # print("-" * 30)
            # time.sleep(1.0)
            
            # # --- Go Backward for 2.5 seconds ---
            # print("Moving BACKWARD for 2.5 seconds...")
            # start_time = time.monotonic()
            # while time.monotonic() - start_time < 2.5:
            #     drive_straight(-BASE_SPEED)
            #     time.sleep(0.01)

            # halt()
            # print(f"  -> Final Yaw: {yaw:.2f} degrees")
            # print(f"  -> Distance Forward: {forward_distance:.3f} meters")
            # # print(f"  -> Distance Lateral: {lateral_distance:.3f} meters")
            # print("-" * 30)
            # time.sleep(2.0)

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    finally:
        halt()
        print("\nFinal Position Estimate:")
        print(f"  Forward: {forward_distance:.3f} m")
        print(f"  Lateral: {lateral_distance:.3f} m")