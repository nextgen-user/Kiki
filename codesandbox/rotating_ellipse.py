import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

# Create a figure and axis
fig, ax = plt.subplots()
ax.set_xlim(-1.5, 1.5)
ax.set_ylim(-1.5, 1.5)

# Initialize the ellipse
ellipse, = ax.plot([], [], 'b-')

# Function to update the ellipse for each frame
def animate(frame):
    theta = np.linspace(0, 2*np.pi, 100)
    x = np.cos(theta)
    y = np.sin(theta + frame/20)
    ellipse.set_data(x, y)
    return ellipse,

# Create the animation
ani = FuncAnimation(fig, animate, frames=100, interval=50, blit=True)

# Save the animation as a GIF
ani.save('/home/pi/emo_v3/kiki-2025-03-06/codesandbox/rotating_ellipse.gif', writer='pillow')