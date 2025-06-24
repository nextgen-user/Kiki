import RPi.GPIO as GPIO
import time

# --- Configuration ---
# Use BCM GPIO pin numbering
GPIO.setmode(GPIO.BCM)

# GPIO pin assignments
TRIG_PIN = 26
# A list of all ECHO pins
ECHO_PINS = [13, 5, 6, 19]

# Speed of sound in cm/s
SPEED_OF_SOUND = 34300

# --- GPIO Setup ---
# Set TRIG as an output pin
GPIO.setup(TRIG_PIN, GPIO.OUT)
# Set all ECHO pins as input pins
for pin in ECHO_PINS:
    GPIO.setup(pin, GPIO.IN)

def measure_all_distances():
    """
    Triggers all sensors at once and measures the distance for each.
    This is much faster than measuring sequentially.
    """
    distances = {}
    
    # 1. Send a single trigger pulse for all sensors
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)  # 10 microsecond pulse
    GPIO.output(TRIG_PIN, False)

    # Record the time the pulse was sent
    trigger_time = time.time()

    # 2. For each sensor, wait for its echo to start and end
    for pin in ECHO_PINS:
        pulse_start_time = trigger_time
        pulse_end_time = trigger_time

        # --- Wait for the echo to start (pin goes HIGH) ---
        # We use a timeout to prevent the script from freezing if no echo is received.
        # The loop will break after 0.03 seconds (corresponds to ~5m range)
        while GPIO.input(pin) == 0:
            pulse_start_time = time.time()
            if pulse_start_time - trigger_time > 0.03:
                # No echo received, mark as timeout
                break
        
        # If we broke the loop due to a timeout, continue to the next sensor
        if pulse_start_time - trigger_time > 0.03:
            distances[str(pin)] = -1 # Use -1 or None to indicate a timeout
            continue

        # --- Wait for the echo to end (pin goes LOW) ---
        while GPIO.input(pin) == 1:
            pulse_end_time = time.time()
            if pulse_end_time - pulse_start_time > 0.03:
                # Echo took too long, probably an error
                break

        # 3. Calculate distance from the pulse duration
        pulse_duration = pulse_end_time - pulse_start_time
        # Distance = (Time * Speed of Sound) / 2 (for round trip)
        distance = (pulse_duration * SPEED_OF_SOUND) / 2
        
        distances[str(pin)] = round(distance, 2)

    return distances

# --- Main Loop ---
try:
    print("Starting distance measurement... Press Ctrl+C to stop.")
    while True:
        # Get distances from all sensors
        all_distances = measure_all_distances()
        print(f"Distances (cm): {all_distances}")
        
        # A short delay between measurement cycles.
        # This allows echoes from the previous cycle to fade away and prevents
        # interference. 60ms is a safe value.
        time.sleep(0.06)

finally:
    # This block will run when the script is stopped (e.g., Ctrl+C)
    print("\nCleaning up GPIO pins.")
    GPIO.cleanup()