import RPi.GPIO as GPIO
import time
import board
import smbus3 as smbus
import numpy as np
import matplotlib.pyplot as plt
import math

from adafruit_motorkit import MotorKit

# --- Constants ---
# MPU6050 Registers
PWR_MGMT_1   = 0x6B
GYRO_CONFIG  = 0x1B
GYRO_ZOUT_H  = 0x47
ACCEL_YOUT_H = 0x3D
# I2C Communication
DEVICE_ADDRESS = 0x68
# Sensor Sensitivity
GYRO_SENSITIVITY = 131.0
ACCEL_SENSITIVITY = 16384.0 # LSB/g
G_FORCE = 9.81
# GPIO Pins
TRIG_PIN = 26
ULTRASONIC_PINS = {"front": 13, "right": 5, "back": 6, "left": 19}
TURN_MOTOR_PINS = {"left": 21, "right": 20} # Your 5th motor GPIOs

class Robot:
    def __init__(self):
        # --- Robot Control Parameters ---
        self.KP = 15.0
        self.BASE_SPEED = 0.5
        
        # --- Robot State (Pose) ---
        self.x = 0.0  # meters
        self.y = 0.0  # meters
        self.yaw = 0.0 # radians
        self.velocity_y_local = 0.0 # <<< NEW: Velocity in robot's forward direction
        self.gyro_z_offset = 0.0
        self.accel_y_offset = 0.0 # <<< NEW: Accelerometer bias
        self.last_update_time = 0.0

        # --- Hardware Initialization ---
        self.kit = MotorKit(address=0x6F)
        self.bus = smbus.SMBus(1)
        self.setup_gpio()
        
        print("Robot Initializing...")
        self.mpu_init()
        self.calibrate_gyro()
        self.calibrate_accelerometer() # <<< NEW: Calibrate accelerometer at start
        self.last_update_time = time.monotonic()
        print("Robot Ready.")

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(TRIG_PIN, GPIO.OUT)
        for pin in ULTRASONIC_PINS.values():
            GPIO.setup(pin, GPIO.IN)
        for pin in TURN_MOTOR_PINS.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

    def cleanup(self):
        print("Cleaning up GPIO...")
        self.stop()
        GPIO.cleanup()

    # --- Low-Level Sensor/Motor Functions ---
    def mpu_init(self):
        self.bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 0)
        time.sleep(0.1)
        self.bus.write_byte_data(DEVICE_ADDRESS, GYRO_CONFIG, 0)
        time.sleep(0.1)

    def read_raw_data(self, addr):
        high = self.bus.read_byte_data(DEVICE_ADDRESS, addr)
        low = self.bus.read_byte_data(DEVICE_ADDRESS, addr + 1)
        value = (high << 8) | low
        return value - 65536 if value > 32768 else value

    def calibrate_gyro(self):
        print("Calibrating gyroscope... Keep robot still.")
        num_samples = 200
        gyro_z_sum = sum(self.read_raw_data(GYRO_ZOUT_H) for _ in range(num_samples))
        self.gyro_z_offset = gyro_z_sum / num_samples
        print(f"Gyro Z-axis offset: {self.gyro_z_offset:.2f}")

    # <<< NEW: Function to calibrate accelerometer bias
    def calibrate_accelerometer(self):
        """Reads the accelerometer to determine the Y-axis offset (bias)."""
        print("Calibrating accelerometer... Keep robot still and level.")
        num_samples = 200
        accel_y_sum = sum(self.read_raw_data(ACCEL_YOUT_H) for _ in range(num_samples))
        self.accel_y_offset = accel_y_sum / num_samples
        print(f"Accel Y-axis offset: {self.accel_y_offset:.2f}")

    # <<< NEW FUNCTION: Re-estimates gyro bias when the robot is stationary (ZUPT)
    def dynamic_gyro_recalibration(self):
        """Performs a quick gyro recalibration when the robot is known to be still."""
        print("Performing dynamic gyro recalibration (ZUPT)...")
        num_samples = 50
        gyro_z_sum = 0
        for _ in range(num_samples):
            gyro_z_sum += self.read_raw_data(GYRO_ZOUT_H)
            time.sleep(0.01)
        
        new_offset = gyro_z_sum / num_samples
        # Use a weighted average to smoothly update the offset, preventing sudden jumps
        self.gyro_z_offset = (0.95 * self.gyro_z_offset) + (0.05 * new_offset)
        print(f"New gyro offset: {self.gyro_z_offset:.2f}")

    # <<< MODIFIED: This function now performs double integration for position
    def update_pose(self):
        """Updates yaw from gyro and estimates X, Y position from accelerometer."""
        current_time = time.monotonic()
        dt = current_time - self.last_update_time
        if dt <= 0: return # Avoid division by zero
        self.last_update_time = current_time
        
        # 1. Update Yaw (Angle) from Gyroscope
        raw_gyro_z = self.read_raw_data(GYRO_ZOUT_H)
        angular_velocity_z = (raw_gyro_z - self.gyro_z_offset) / GYRO_SENSITIVITY
        if abs(angular_velocity_z) < 0.1: angular_velocity_z = 0.0
        self.yaw += math.radians(angular_velocity_z * dt)
        self.yaw = (self.yaw + math.pi) % (2 * math.pi) - math.pi # Normalize

        # 2. Update X, Y Position using Accelerometer (PRONE TO SEVERE DRIFT)
        # Read raw acceleration in the robot's forward (Y) direction
        raw_accel_y = self.read_raw_data(ACCEL_YOUT_H)
        
        # Calculate acceleration in m/s^2, removing calibrated bias
        accel_y = ((raw_accel_y - self.accel_y_offset) / ACCEL_SENSITIVITY) * G_FORCE
        
        # Deadband to reduce noise integration when stationary
        if abs(accel_y) < 0.15: # Tune this threshold
             accel_y = 0.0
             self.velocity_y_local *= 0.5 # Apply damping if no acceleration

        # First Integration: Acceleration -> Velocity (v = v_0 + a*t)
        self.velocity_y_local += accel_y * dt
        
        # Second Integration: Velocity -> Distance moved in this time step
        distance_moved = self.velocity_y_local * dt
        
        # Project the local forward movement onto the global X and Y axes
        self.x += distance_moved * math.cos(self.yaw)
        self.y += distance_moved * math.sin(self.yaw)

    def set_drive_motor_speeds(self, left_speed, right_speed):
        left_speed = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))
        self.kit.motor1.throttle = right_speed
        self.kit.motor2.throttle = -right_speed
        self.kit.motor3.throttle = left_speed
        self.kit.motor4.throttle = -left_speed

    def stop(self):
        self.set_drive_motor_speeds(0, 0)
        GPIO.output(TURN_MOTOR_PINS['left'], GPIO.LOW)
        GPIO.output(TURN_MOTOR_PINS['right'], GPIO.LOW)
        self.velocity_y_local = 0.0 # <<< CRITICAL: Reset velocity when stopped

    # <<< MODIFIED: Loop now calls update_pose continuously
    def drive_straight(self, speed):
        """Drives forward using gyro for correction."""
        self.update_pose()
        error_deg = math.degrees(self.yaw)
        correction = (self.KP / 100.0) * error_deg
        self.set_drive_motor_speeds(speed - correction, speed + correction)

    # <<< MODIFIED: Loop now calls update_pose continuously
    def turn_by_angle(self, angle_deg):
        """Turns the robot by a specific angle using the 5th motor."""
        print(f"Turning by {angle_deg} degrees...")
        initial_yaw = self.yaw
        target_yaw_rad = initial_yaw + math.radians(angle_deg)
        
        if angle_deg > 0: # Turn Right
            GPIO.output(TURN_MOTOR_PINS['right'], GPIO.HIGH)
            while self.yaw < target_yaw_rad:
                self.update_pose()
                time.sleep(0.01)
        else: # Turn Left
            GPIO.output(TURN_MOTOR_PINS['left'], GPIO.HIGH)
            while self.yaw > target_yaw_rad:
                self.update_pose()
                time.sleep(0.01)
                
        self.stop()
        print(f"Turn complete. Final Yaw: {math.degrees(self.yaw):.2f} degrees")
        
    def measure_all_distances(self):
        # ... (This function remains unchanged)
        distances = {}
        for name, pin in ULTRASONIC_PINS.items():
            time.sleep(0.05)
            GPIO.output(TRIG_PIN, True)
            time.sleep(0.00001)
            GPIO.output(TRIG_PIN, False)
            pulse_start = time.time()
            timeout_start = time.time()
            while GPIO.input(pin) == 0:
                pulse_start = time.time()
                if time.time() - timeout_start > 0.1: break
            pulse_end = time.time()
            while GPIO.input(pin) == 1:
                pulse_end = time.time()
                if time.time() - timeout_start > 0.1: break
            distance = round((pulse_end - pulse_start) * 171.50, 2)
            distances[name] = -1 if distance > 4.0 or distance < 0.02 else distance
        return distances

# --- Mapper and Visualizer Classes (Unchanged) ---
class OccupancyGridMapper:
    # ... (This class is the same as before)
    def __init__(self, map_size_m, resolution):
        self.map_size_m = map_size_m
        self.resolution = resolution
        self.map_size_cells = int(map_size_m / resolution)
        self.grid = np.zeros((self.map_size_cells, self.map_size_cells), dtype=np.int8)
        self.origin_offset = self.map_size_cells // 2
    def world_to_map(self, x, y):
        mx = int(x / self.resolution) + self.origin_offset
        my = int(y / self.resolution) + self.origin_offset
        if 0 <= mx < self.map_size_cells and 0 <= my < self.map_size_cells:
            return mx, my
        return None, None
    def update_map(self, robot_pose, sensor_readings):
        rx, ry, r_yaw = robot_pose
        sensor_angles = {"front": 0, "right": -math.pi/2, "left": math.pi/2, "back": math.pi}
        for name, dist in sensor_readings.items():
            if dist == -1: continue
            sensor_yaw = r_yaw + sensor_angles[name]
            ox = rx + dist * math.cos(sensor_yaw)
            oy = ry + dist * math.sin(sensor_yaw)
            mx, my = self.world_to_map(ox, oy)
            if mx is not None:
                self.grid[mx, my] = 1

class Visualizer:
    # ... (This class is the same as before)
    def __init__(self, map_size_m):
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.map_im = self.ax.imshow(np.zeros((1,1)), cmap='gray_r', vmin=-1, vmax=1)
        self.robot_path, = self.ax.plot([], [], 'b-')
        self.robot_marker, = self.ax.plot([], [], 'ro')
        self.ax.set_xlim(0, map_size_m)
        self.ax.set_ylim(0, map_size_m)
    def update_plot(self, mapper, robot_path_history):
        self.map_im.set_data(np.flipud(mapper.grid.T))
        self.map_im.set_extent((0, mapper.map_size_cells, 0, mapper.map_size_cells))
        path_x = [(p[0] / mapper.resolution + mapper.origin_offset) for p in robot_path_history]
        path_y = [(p[1] / mapper.resolution + mapper.origin_offset) for p in robot_path_history]
        self.robot_path.set_data(path_x, path_y)
        self.robot_marker.set_data(path_x[-1], path_y[-1])
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.01)

# --- Main Execution Block ---
if __name__ == "__main__":
    robot = Robot()
    mapper = OccupancyGridMapper(map_size_m=10, resolution=0.05)
    visualizer = Visualizer(mapper.map_size_cells)
    robot_path = []
    
    try:
        print("Starting wall following exploration with accelerometer-based positioning...")
        
        while True:
            # <<< MODIFIED LOGIC: We need a continuous loop to integrate acceleration
            
            # --- Decision Phase (based on latest sensor data) ---
            distances = robot.measure_all_distances()
            front_dist = distances.get('front', -1)
            right_dist = distances.get('right', -1)
            
            # --- Action Phase ---
            if 0 < front_dist < 0.30: # Obstacle ahead
                robot.stop()
                robot.dynamic_gyro_recalibration() # <<< ZUPT
                print("Obstacle ahead! Turning left.")
                robot.turn_by_angle(-90)
                robot.stop()
                robot.dynamic_gyro_recalibration() # <<< ZUPT after turn
            
            elif right_dist > 0.6 and right_dist != -1: # Lost wall
                robot.stop()
                robot.dynamic_gyro_recalibration() # <<< ZUPT
                print("Lost wall. Turning right.")
                robot.turn_by_angle(45)
                robot.stop()
                robot.dynamic_gyro_recalibration() # <<< ZUPT after turn

            elif 0 < right_dist < 0.2: # Too close to wall
                robot.stop()
                robot.dynamic_gyro_recalibration() # <<< ZUPT
                print("Too close to wall. Turning left.")
                robot.turn_by_angle(-20)
                robot.stop()
                robot.dynamic_gyro_recalibration() # <<< ZUPT after turn
            
            else: # Ideal state: drive forward
                print("Following wall. Driving forward.")
                robot.drive_straight(robot.BASE_SPEED)

            # --- Continuous Update and Visualization Phase ---
            robot.update_pose()
            current_pose = (robot.x, robot.y, robot.yaw)
            mapper.update_map(current_pose, distances)
            
            # To avoid flooding the path history, add a point every so often
            if not robot_path or (time.time() - robot_path[-1]['time'] > 0.2):
                 robot_path.append({'pose': current_pose, 'time': time.time()})

            visualizer.update_plot(mapper, [p['pose'] for p in robot_path])

            print(f"Pose: (x={robot.x:.2f}, y={robot.y:.2f}, yaw={math.degrees(robot.yaw):.1f}) | Vel: {robot.velocity_y_local:.2f} m/s")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        robot.cleanup()
        plt.ioff()
        plt.show()