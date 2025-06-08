import gtts
import playsound
import subprocess
import smtplib
from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import time
from googletrans import Translator
from requests_futures.sessions import FuturesSession
TOKEN = "5182224145:AAEjkSlPqV-Q3rH8A9X8HfCDYYEQ44v_qy0"
chat_id = "5075390513"
session = FuturesSession()
import pyaudio
import subprocess
language = "english"
hotword = "None"
TOKEN = "5182224145:AAEjkSlPqV-Q3rH8A9X8HfCDYYEQ44v_qy0"
chat_id = "5075390513"
class basics:
    
    global language
    
    # The init method or constructor
    def __init__(self, default):
           
        # Instance Variable
        self.default = default            
    def changelang(self,lang):  
        global language 
        language = lang
        
    

    # Adds an instance variable 
    def speak(self,audio):  
        t = time.time()
        global language
        translator = Translator()
        
        if language == "english":
            t1 = gtts.gTTS(audio,slow=True)
            print(time.time()-t)
            t1.save("/home/pi/welcome.mp3") 
            print(time.time()-t)
    
        else:
            k = translator.translate(audio, dest='hi')
            t1 = gtts.gTTS(k.text,slow=True,lang="hi")
            t1.save("/home/pi/welcome.mp3")     
        
        subprocess.call("sox /home/pi/welcome.mp3 /home/pi/effect.mp3  pitch +500 ",shell = True)
        print(time.time()-t)
        playsound.playsound("/home/pi/effect.mp3")
        print(time.time()-t)



    def quack(self,thinking,audio):  
        global TOKEN
        global chat_id
        global language
        translator = Translator()
        session.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text=The answer is👇\n{audio}")

        if language == "english":
            t1 = gtts.gTTS(audio,slow=True)
            t1.save("/home/pi/welcome.mp3")     
        else:
            k = translator.translate(audio, dest='hi')
            t1 = gtts.gTTS(k.text,slow=True,lang="hi")
            t1.save("/home/pi/welcome.mp3")      
        subprocess.call("sox /home/pi/welcome.mp3 /home/pi/effect.mp3  pitch +500 ",shell = True)
        try:
            thinking.kill()
        except:
            pass
        subprocess.Popen("kill $(pgrep -f thinking.mp3)",shell = True)

        playsound.playsound("/home/pi/effect.mp3")


    # Retrieves instance variable    
    def sendEmail(self,to, content):
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            
            # Enable low security in gmail
            server.login('vaibhavarduino@gmail.com', 'techi@721')
            server.sendmail('vaibhavarduino@gmail.com', to, content)
            server.close()
            return "Email Sent"
        except Exception as e:
            print(e)
            return "Error"

    def bsquare(self):
        i2c = busio.I2C(SCL, SDA)
        disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
        disp.fill(0)
        disp.show()
        width = disp.width
        height = disp.height
        image = Image.new("1", (width, height))
        draw = ImageDraw.Draw(image)
        if True:
            # Draw a black filled box to clear the image.
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            disp.image(image)
            disp.show()
            # Draw some shapes.
            # First define some constants to allow easy resizing of shapes.
            padding = 1
            shape_width = 32
            top = padding
            bottom = height - padding - 20

            # Move left to right keeping track of the current x position for drawing shapes.
            x = 20
            # Draw an ellipse.
            # draw.ellipse((x, top, x + shape_width, bottom), outline=255, fill=0)
            # x += shape_width + padding
            # Draw a rectangle.
            draw.rectangle((x, top + 20, x + shape_width, bottom), outline=255, fill=1)

            # Draw a triangle.

            padding = 1
            shape_width = 32
            top = padding
            bottom = height - padding - 20
            # Move left to right keeping track of the current x position for drawing shapes.
            x = 80
            # Draw an ellipse.
            # draw.ellipse((x, top, x + shape_width, bottom), outline=255, fill=0)
            # x += shape_width + padding
            # Draw a rectangle.
            draw.rectangle((x, top + 20, x + shape_width, bottom), outline=255, fill=1)
            x += shape_width + padding
            x += shape_width + padding
            # Draw an X.
            # draw.line((x, bottom, x + shape_width, top), fill=255)
            # draw.line((x, top, x + shape_width, bottom), fill=255)
            # x += shape_width + padding

            # Load default font.
            font = ImageFont.load_default()

            # Alternatively load a TTF font.  Make sure the .ttf font file is in the
            # same directory as the python script!
            # Some other nice fonts to try: http://www.dafont.com/bitmap.php
            # font = ImageFont.truetype('Minecraftia.ttf', 8)

            # # Write two lines of text.
            # draw.text((x, top), "Hello", font=font, fill=255)
            # draw.text((x, top + 20), "World!", font=font, fill=255)

            # Display image.
            disp.image(image)
            disp.show()
            time.sleep(1.5)
    def sleepy(self):
        i2c = busio.I2C(SCL, SDA)
        disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
        disp.fill(0)
        disp.show()
        width = disp.width
        height = disp.height
        image = Image.new("1", (width, height))
        draw = ImageDraw.Draw(image)
        if True:
            # Draw a black filled box to clear the image.
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            disp.image(image)
            disp.show()
            # Draw some shapes.
            # First define some constants to allow easy resizing of shapes.
            padding = 1
            shape_width = 32
            top = padding
            bottom = height - padding - 20

            # Move left to right keeping track of the current x position for drawing shapes.
            x = 20
            # Draw an ellipse.
            # draw.ellipse((x, top, x + shape_width, bottom), outline=255, fill=0)
            # x += shape_width + padding
            # Draw a rectangle.
            draw.rectangle((x, top + 10, x + shape_width, bottom), outline=255, fill=1)

            # Draw a triangle.

            padding = 1
            shape_width = 32
            top = padding
            bottom = height - padding - 20
            # Move left to right keeping track of the current x position for drawing shapes.
            x = 80
            # Draw an ellipse.
            # draw.ellipse((x, top, x + shape_width, bottom), outline=255, fill=0)
            # x += shape_width + padding
            # Draw a rectangle.
            draw.rectangle((x, top + 10, x + shape_width, bottom), outline=255, fill=1)
            x += shape_width + padding
            x += shape_width + padding
            # Draw an X.
            # draw.line((x, bottom, x + shape_width, top), fill=255)
            # draw.line((x, top, x + shape_width, bottom), fill=255)
            # x += shape_width + padding

            # Load default font.
            font = ImageFont.load_default()

            # Alternatively load a TTF font.  Make sure the .ttf font file is in the
            # same directory as the python script!
            # Some other nice fonts to try: http://www.dafont.com/bitmap.php
            # font = ImageFont.truetype('Minecraftia.ttf', 8)

            # # Write two lines of text.
            # draw.text((x, top), "Hello", font=font, fill=255)
            # draw.text((x, top + 20), "World!", font=font, fill=255)

            # Display image.
            disp.image(image)
            disp.show()
            time.sleep(1.5)
    
    def thinking(self):
        import board
        import busio
        import adafruit_ssd1306
        i2c = busio.I2C(board.SCL, board.SDA)
        width=128
        height=32
        oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
        oled.fill(0) 
        def draw_ball(x,y, size, state):
            if size == 1:
                oled.pixel(x, y, state) # draw a single pixel
            else:
                for i in range(0,size): # draw a box of pixels of the right size
                    for j in range(0,size):
                        oled.pixel(x + i, y + j, state)

        ball_size = 20
        # start in the middle of the screen
        current_x = int(width / 2)
        current_y = int(height / 2)
        curren_x = int(width / 2)
        curren_y = int(height / 2)
        direction_x = 1
        direction_y = 4
        directio_x = 1
        directio_y = 4

        for i in range(1,100,1):
            draw_ball(current_x,current_y, ball_size,1)
            draw_ball(curren_x,curren_y,20 ,1)
            oled.show()
            # utime.sleep(delay_time)
            draw_ball(current_x,current_y,ball_size,0)
            draw_ball(curren_x,curren_y, 20,0)
            # reverse at the edges
            # left edge test
            if current_x < 60:
                direction_x = 2

            if curren_x < 2:
                directio_x = 2
            # right edge test
            if current_x > width - ball_size - 2:
                direction_x = -1

            if curren_x > width - ball_size - 70:
                directio_x = -1
            # top edge test
            # if current_y < 2:
            #     direction_y = 2

            # if curren_y < 2:
            #     directio_y = 2
            # bottom edge test
            # if current_y > height - ball_size - 2:
            #     direction_y = -2

            # if curren_y > height - ball_size - 2:
            #     directio_y = -2
            # update the ball
            current_x = current_x + direction_x
            # current_y = current_y + direction_y
            curren_x = curren_x + directio_x
            # curren_y = curren_y + directio_y
        quit()

    def angry(self):
        import math
        from board import SCL, SDA
        import busio
        from PIL import Image, ImageDraw, ImageFont
        import adafruit_ssd1306

        # Create the I2C interface.
        i2c = busio.I2C(SCL, SDA)

        # Create the SSD1306 OLED class.
        # The first two parameters are the pixel width and pixel height.  Change these
        # to the right size for your display!
        disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

        # Note you can change the I2C address, or add a reset pin:
        # disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c, reset=reset_pin)

        # Clear display.
        disp.fill(0)
        disp.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        width = disp.width
        height = disp.height
        image = Image.new("1", (width, height))

        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 2
        shape_width = 30
        top = padding
        bottom = height - padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = padding
        # Draw an ellipse.
        x += shape_width + padding
        # Draw a triangle.
        print(bottom - 10)
        draw.polygon(
            [(x, bottom - 10), (x + shape_width / 2, 2), (x + shape_width, bottom - 10)],
            outline=255,
            fill=1,
        )
        x += shape_width + padding
        # Draw an X.
        padding = 2
        shape_width = 30
        top = padding
        bottom = height - padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 49
        # Draw an ellipse.
        x += shape_width + padding
        # Draw a triangle.
        print(bottom - 10)
        draw.polygon(
            [(x, bottom - 10), (x + shape_width / 2, 2), (x + shape_width, bottom - 10)],
            outline=255,
            fill=1,
        )
        x += shape_width + padding

        # Display image.
        disp.image(image)
        disp.show()
 
                    
    # def getcmd(self):
    #     global cotword
    #     return cotword




        

    