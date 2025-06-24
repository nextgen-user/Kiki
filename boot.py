import argparse
from brain import *

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google GenAI Live API with Hotword Detection and Tool Calling")
    parser.add_argument(
        "--mode", type=str, default=DEFAULT_MODE,
        help='Video mode: "camera", "screen", or "none". Default: %(default)s',
        choices=["camera", "screen", "none"]
    )
    args = parser.parse_args()




    audio_loop_instance = AudioLoop(
        video_mode=args.mode,
    )

    try:
        print("Starting AudioLoop...")
        asyncio.run(audio_loop_instance.run())
    except KeyboardInterrupt:
        print("\nProgram terminated by user (Ctrl+C).")
    except Exception as e:
        print(f"Unhandled exception in main execution: {type(e).__name__} - {e}")
        traceback.print_exc()

    finally:
        if pya:
            print("Terminating PyAudio in main finally.")
            pya.terminate()
        print("Application finished.")  