import py_qmc5883l
import time

def get_direction(bearing):
    """Converts a bearing in degrees to a cardinal direction."""
    if 45 <= bearing < 135:
        return "East"
    elif 135 <= bearing < 225:
        return "South"
    elif 225 <= bearing < 315:
        return "West"
    else:
        return "North"

# --- FIX APPLIED HERE ---
# Initialize the sensor with an extended range of +/-8 Gauss to prevent saturation.
# This is the most likely fix for your issue.
sensor = py_qmc5883l.QMC5883L(output_range=py_qmc5883l.RNG_8G)

# Set the magnetic declination for your location
sensor.declination = 1.3

print("Starting readings. Rotate the sensor slowly in all directions.")
print("Press Ctrl+C to exit.")

try:
    while True:
        m = sensor.get_magnet()
        bearing = sensor.get_bearing()
        direction = get_direction(bearing)
        
        # The f-string formatting provides a clean, readable output.
        print(f"Raw Magnetometer (X, Y, Z): {m} | Bearing: {bearing:.2f}° | Direction: {direction}")
        
        time.sleep(0.2) # Wait a moment before the next reading

except KeyboardInterrupt:
    print("\nProgram stopped.")