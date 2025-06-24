import time
from mcp.server.fastmcp import FastMCP
import subprocess 
mcp = FastMCP("My App")
import pexpect
from robot_control.robot_control import turn_left,turn_right,send_action,send_move_command
Parent=pexpect.spawn('bash')
from exa_py import Exa
import pexpect
exa = Exa(api_key = "e4399980-1016-44ab-8789-1ef7f967a281")
import os
import glob
import requests


destination_dir="/home/pi/emo_v3/kiki-2025-03-06/codesandbox"
files_list=[]

def upload_file(file_path, upload_url):
    """Uploads a file to the specified server endpoint."""

    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Prepare the file for upload
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file)}  #  Important: Provide filename

            # Send the POST request
            response = requests.post(upload_url, files=files)

            # Check the response status code
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            # Parse and print the response
            if response.status_code == 200:
                print(f"File uploaded successfully.  Filename returned by server: {response.text}")
                return response.text # Return the filename returned by the server
            else:
                print(f"Upload failed. Status code: {response.status_code}, Response: {response.text}")
                return None

    except FileNotFoundError as e:
        print(e)
        return None  # or re-raise the exception if you want the program to halt
    except requests.exceptions.RequestException as e:
        print(f"Upload failed. Network error: {e}")
        return None
def run(cmd, timeout_sec,forever_cmd):
    global Parent
    if forever_cmd == 'true':
        Parent.close()
        Parent = pexpect.spawn("bash")
        command="cd /home/pi/emo_v3/kiki-2025-03-06/codesandbox && "+cmd

        Parent.sendline(command)
        Parent.readline().decode()
        return str(Parent.readline().decode())    
    t=time.time()
    child = pexpect.spawn("bash")
    output=""
    command="cd /home/pi/emo_v3/kiki-2025-03-06/codesandbox && "+cmd

    child.sendline('PROMPT_COMMAND="echo END"')
    child.readline().decode()
    child.readline().decode()

    child.sendline(command)
    count=0

    while (not child.eof() ) and (time.time()-t<timeout_sec):
        x=child.readline().decode()
        output=output+x
        print(x)
        if "END" in x :
            output=output.replace("END","")
            count+=1
            if count>1:
                child.close()
                break
        if "true" in forever_cmd:
            break
    return output

@mcp.tool()
def set_timer(timer_duration: int) -> str:
    """Timer duration in seconds"""
    subprocess.Popen(f"sleep {timer_duration} ; exec play /home/pi/Inta_Robo2/soundeffects/timer.mp3",shell=True)
    return "Timer set for {} seconds!".format(timer_duration)

@mcp.tool()
def play_music(song) -> str:
    """Plays a song from youtube.Can be a a specific song name or a general name such as soft insturmental music"""
    return "Playing the Music"


@mcp.tool()
def run_code(language:str,packages:str,filename: str, code: str,start_cmd:str,forever_cmd:str) -> dict:
    """  
    Execute code in a controlled environment with package installation and file handling.
    Args:
        language:Programming language of the code (eg:"python", "nodejs", "bash","html",etc).
        packages: Space-separated list of packages to install.(python packages are installed if language set to python and npm packages are installed if language set to nodejs).
                  Preinstalled python packages: gradio, XlsxWriter, openpyxl , mpxj , jpype1.
                  Preinstalled npm packages: express, ejs, chart.js.
        filename:Name of the file to create (stored in /home/pi/emo_v3/kiki-2025-03-06/codesandbox/).
        code:Full code to write to the file.
        start_cmd:Command to execute the file (e.g., "python /home/pi/emo_v3/kiki-2025-03-06/codesandbox/app.py" 
                  or "bash /home/pi/emo_v3/kiki-2025-03-06/codesandbox/app.sh").
                  Leave blank ('') if only file creation is needed / start_cmd not required.
        forever_cmd:If 'true', the command will run indefinitely.Set to 'true', when runnig a website/server.Run all servers/website on port 1337. If 'false', the command will time out after 300 second and the result will be returned.
    Notes:
        - All user-uploaded files are in /home/pi/emo_v3/kiki-2025-03-06/codesandbox/.
        - When editing and subsequently re-executing the server with the forever_cmd='true' setting, the previous server instance will be automatically terminated, and the updated server will commence operation. This functionality negates the requirement for manual process termination commands such as pkill node.    
        - The opened ports can be externally accessed at https://suitable-liked-ibex.ngrok-free.app/ (ONLY if the website is running successfully)
        - Do not use `plt.show()` in this headless environment. Save visualizations directly (e.g., `plt.savefig("happiness_img.png")` or export GIFs/videos).User-Interactive libraries and programs like `pygame` are also not supported.Try to create a website to accomplish the same task instead.
    """
    global destination_dir
    package_names = packages.strip()
    if "python" in language:
        command="pip install   "
    elif "node" in language:
        command="npm install "
    else:
        command="ls"
    if  packages != "" and packages != " ":
        package_logs=run(
            f"{command} {package_names}", timeout_sec=300,forever_cmd= 'false' 
        )
        if "ERROR" in package_logs:
            return {"package_installation_log":package_logs,"info":"Package installation failed. Please check the package names. Tip:Try using another package/method to accomplish the task."}
    f = open(os.path.join(destination_dir, filename), "w")
    f.write(code)
    f.close()
    global files_list
    if start_cmd != "" and start_cmd != " ":
        stdot=run(start_cmd, 120,forever_cmd)
    else:
        stdot="File created successfully."
    onlyfiles = glob.glob("/home/pi/emo_v3/kiki-2025-03-06/codesandbox/*")
    onlyfiles=list(set(onlyfiles)-set(files_list))
    uploaded_filenames=[]
    for files in onlyfiles:
        try:
            uploaded_filename = upload_file(files, "https://opengpt-4ik5.onrender.com/upload")
            uploaded_filenames.append(f"https://opengpt-4ik5.onrender.com/static/{uploaded_filename}")
        except:
            pass
    files_list=onlyfiles
    return {"output":stdot,"Files_download_link":uploaded_filenames}

@mcp.tool()
def take_photo() -> str:
    """Take a photo of the present webcam view."""
    run("ffmpeg -i 'http://localhost:5000/mjpeg' -frames:v 1 -f image2 /home/pi/emo_v3/kiki-2025-03-06/media/selfie.jpeg -y",120,"false")
    upload_file("/home/pi/emo_v3/kiki-2025-03-06/media/selfie.jpeg", "https://opengpt-4ik5.onrender.com/upload")
    return "Photo taken!"

@mcp.tool()
def stay_silent() -> str:
    """Stay silent and stop listening : switch to hotword detection.Useful when the user gets annoyed , or tells to shut up/stay silent."""

    return "DONE"
# @mcp.tool()
# def search_web(query: str) -> str:
#     """Search the web for a query. Can Also be used to check the current time in a specific location, check the weather and get other realtime info."""
#     result = exa.search_and_contents(query, livecrawl="auto", num_results=2)
#     return result

@mcp.tool()
def turn(direction:str,degree:str) -> str:
    """Turn the robot left or right in degree.
       direction : ("left","right")
       degree: [0,180]
    """
    send_action("5")
    if direction=="left":
        turn_left(int(degree))
    elif direction == "right":
        turn_right(int(degree))
    send_action("1")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')