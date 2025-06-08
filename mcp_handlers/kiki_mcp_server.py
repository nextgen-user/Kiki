import httpx
from mcp.server.fastmcp import FastMCP
import subprocess 
mcp = FastMCP("My App")
import pexpect
Parent=pexpect.spawn('bash')
from exa_py import Exa
exa = Exa(api_key = "e4399980-1016-44ab-8789-1ef7f967a281")


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
def search_web(query: str) -> str:
    """Search the web for a query. Can Also be used to check the current time in a specific location, check the weather and get other realtime info."""
    result = exa.search_and_contents(query, livecrawl="auto", num_results=2)
    return result



if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')