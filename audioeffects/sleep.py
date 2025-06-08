import math
import time
import pygame
from pygame.locals import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import sys
sys.path.insert(1, '/home/pi/emo_v3/kiki-2025-03-06/memory')
from memory import Memory
m = Memory()
import subprocess
m.update_data('currentmode', 'sleepy')
m.save()
# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen_width, screen_height = screen.get_rect().size
pygame.display.set_caption("ROBOTIC EYES")

# Original OLED dimensions
width = 128
height = 32

# Create PIL image and drawing context
image = Image.new("RGB", (width, height), (0, 0, 0))  # Use RGB mode for color
draw = ImageDraw.Draw(image)
color_light = (170,170,170)
# Eye color (blue)
eye_color = (0, 0, 255)  # RGB: blue

# Add stop button variables
button_font = pygame.font.Font(None, 36)
button_color = (200, 50, 50)
button_hover_color = (220, 80, 80)
button_rect = pygame.Rect(screen_width - 150, screen_height - 50, 140, 40)
button_text = button_font.render("Stop Audio", True, (255, 255, 255))
button_hover = False

# Main rendering function
def sleepy():

    # Clear the image with black background
    draw.rectangle((0, 0, width, height), outline=(0, 0, 0), fill=(0, 0, 0))
    
    # Draw shapes
    padding = 1
    shape_width = 32
    top = padding
    bottom = height - padding - 20
    
    # First rectangle (eye)
    x = 20
    draw.rectangle((x, top + 10, x + shape_width, bottom), 
                   outline=eye_color, fill=eye_color)  # Blue eye
    
    # Second rectangle (eye)
    x = 80
    draw.rectangle((x, top + 10, x + shape_width, bottom), 
                   outline=eye_color, fill=eye_color)  # Blue eye
    
    # Convert PIL image to Pygame surface
    pil_str = image.tobytes()
    pygame_surface = pygame.image.fromstring(pil_str, (width, height), "RGB")
    
    # Scale to fullscreen while maintaining aspect ratio
    scale_factor = min(screen_width / width, screen_height / height)
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    pos_x = (screen_width - new_width) // 2
    pos_y = (screen_height - new_height) // 2
    
    scaled_surface = pygame.transform.scale(
        pygame_surface, 
        (new_width, new_height)
    )
    
    # Render to screen
    screen.fill((0, 0, 0))  # Black background
    screen.blit(scaled_surface, (pos_x, pos_y))
    pygame.display.flip()

# Main loop
running = True
start_time = time.time()

def awake():
    # Clear the image with black background
    draw.rectangle((0, 0, width, height), outline=(0, 0, 0), fill=(0, 0, 0))
    
    # Draw shapes
    padding = 1
    shape_width = 32
    eye_height = 20  # Increased height for more visible eyes
    
    # Calculate vertical position to center the eyes
    top = (height - eye_height) // 2
    
    # First rectangle (eye)
    x = 20
    draw.rectangle((x, top, x + shape_width, top + eye_height), 
                   outline=eye_color, fill=eye_color)  # Blue eye
    
    # Second rectangle (eye)
    x = 80
    draw.rectangle((x, top, x + shape_width, top + eye_height), 
                   outline=eye_color, fill=eye_color)  # Blue eye
    
    # Convert PIL image to Pygame surface
    pil_str = image.tobytes()
    pygame_surface = pygame.image.fromstring(pil_str, (width, height), "RGB")
    
    # Scale to fullscreen while maintaining aspect ratio
    scale_factor = min(screen_width / width, screen_height / height)
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    pos_x = (screen_width - new_width) // 2
    pos_y = (screen_height - new_height) // 2
    
    scaled_surface = pygame.transform.scale(
        pygame_surface, 
        (new_width, new_height)
    )
    
    # Render to screen
    screen.fill((0, 0, 0))  # Black background
    screen.blit(scaled_surface, (pos_x, pos_y))
    pygame.display.flip()

    
while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
            running = False
        # Handle mouse events for stop button
        elif event.type == MOUSEMOTION:
            button_hover = button_rect.collidepoint(event.pos)
        elif event.type == MOUSEBUTTONDOWN:
            if button_rect.collidepoint(event.pos):
                subprocess.Popen("sudo pkill mpv",shell=True)
                m.update_data('song', 'false')
                m.save()
    
    # Render display
    time.sleep(1)
    m = Memory()

    if m.get_data('currentmode') == 'sleepy':
        sleepy()
        print("sleepy")
    elif m.get_data('currentmode') == 'awake':
        awake()
        print("awake")
    
    # Draw stop button (always on bottom right)
    if m.get_data('song')== 'true':
        button_color_current = button_hover_color if button_hover else button_color
        pygame.draw.rect(screen, button_color_current, button_rect, border_radius=8)
        pygame.draw.rect(screen, (150, 30, 30), button_rect, 2, border_radius=8)  # Darker border
        text_rect = button_text.get_rect(center=button_rect.center)
        screen.blit(button_text, text_rect)

    pygame.display.flip()

pygame.quit()