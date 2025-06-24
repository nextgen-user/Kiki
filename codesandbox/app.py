import pygame
import sys

# Initialize Pygame
pygame.init()

# Set up display
width, height = 400, 300
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Rotating Ellipse")

# Colors
white = (255, 255, 255)
black = (0, 0, 0)

# Ellipse parameters
ellipse_rect = pygame.Rect(100, 50, 200, 100)
angle = 0

# Animation loop
clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Rotate the ellipse
    rotated_image = pygame.Surface((ellipse_rect.width, ellipse_rect.height), pygame.SRCALPHA)
    pygame.draw.ellipse(rotated_image, black, (0, 0, ellipse_rect.width, ellipse_rect.height))
    rotated_image = pygame.transform.rotate(rotated_image, angle)
    angle += 1  # Increment angle for rotation

    # Clear the screen
    screen.fill(white)

    # Draw the rotated ellipse
    new_rect = rotated_image.get_rect(center=ellipse_rect.center)
    screen.blit(rotated_image, new_rect)

    # Update display
    pygame.display.flip()

    # Control the frame rate
    clock.tick(60)

# Quit Pygame
pygame.quit()
sys.exit()