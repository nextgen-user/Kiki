# text_input_handler.py
import asyncio

async def send_text_external(assistant_instance):
    """
    Handles text input for the assistant.
    """
    print("Starting text input task. Type 'q' or 'quit' to exit.")
    while True:
        try:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )

            if text.lower() in ("q", "quit"):
                print("Quit command received from text input.")
                break

            # Now, use 'assistant_instance' instead of 'self'
            if assistant_instance.session:
                if assistant_instance.listening_state == "AWAITING_HOTWORD":
                    print("Text input received, switching to Gemini mode.")
                    assistant_instance.listening_state = "SENDING_TO_GEMINI"
                    # Call the internal method via the passed instance
                    await assistant_instance._close_porcupine_resources()

                await assistant_instance.session.send(input=text or ".", end_of_turn=True)
            else:
                print("Session not available for sending text.")
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("send_text_external task cancelled.")
            break
        except Exception as e:
            print(f"Error in send_text_external: {e}")
            break