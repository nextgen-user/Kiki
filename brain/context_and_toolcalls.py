from google.genai import types
# from pathlib import Path
# from Misc.helper import parse_function_call_string
import asyncio
import subprocess
    
async def handle_server_content(self, server_content):

    model_turn = server_content.model_turn
    if model_turn:
        for part in model_turn.parts:
            executable_code = part.executable_code
            if executable_code is not None:
                print('-------------------------------')
                print(f'``` python\n{executable_code.code}\n```')
                print('-------------------------------')
                # if "google_search" not in str(executable_code.code):
                #     if "print(" in str(executable_code.code):
                #         codee= str(executable_code.code).replace("print(","",1)
                #         if codee[-1]== ")":
                #             codee=codee[:-1]
                #         else:
                #             codee=codee[:-2]

                #         print(codee)
                #     else:
                #         codee=str(executable_code.code)



                #     name1,arg1= parse_function_call_string(codee)
                #     if name1 == "keep_listening_for_follow_up":
                #         print("AI requested to keep listening for follow-up. No tool response sent.")
                #         self.follow_up=True
                #         break
                #     if name1=="play_music":
                #         subprocess.Popen(f"mpv $(yt-dlp -f ba 'ytsearch:{arg1["song"]}' -g)",shell=True)
                #         # m.update_data('song', 'true')
                #         # m.save()
                #         break
                #     if name1=="set_timer":
                #         subprocess.Popen(f"sleep {arg1["timer_duration"]} ; exec play /home/pi/Inta_Robo2/soundeffects/timer.mp3",shell=True)
                #         break

                #     print(arg1)
                #     server=""
                #     for key in list(self.mcp_client.sessions.keys()):
                #         response = await self.mcp_client.sessions[key].list_tools()
                #         tools = response.tools
                #         for tool in tools:
                #             if tool.name==name1:
                #                 server=key
                #                 break
                        



                #     result = await self.mcp_client.sessions[server].call_tool(
                #         name=name1,
                #         arguments=arg1,
                #     )
                #     print(result)


                #     await self.session.send(input=f"Tool call {name1} returned response: {str(result)}.The user cannot see the tool response.Tell the user in your own words about what you found using the tools.", end_of_turn=True)
                #     print("FINALLY SUMMONING AI")
                    
                #     audio_bytes = Path("/home/pi/emo_v3/audioeffects/webs.wav").read_bytes()
                #     await self.session.send_realtime_input(
                #         audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                # )          
                #     print("AI_SUMMONED")
            code_execution_result = part.code_execution_result
            if code_execution_result is not None:
                print('-------------------------------')
                print(f'```\n{code_execution_result.output}\n```')
                print('-------------------------------')



    grounding_metadata = getattr(server_content, 'grounding_metadata', None)
    if grounding_metadata is not None:
        print(grounding_metadata.search_entry_point.rendered_content)

    if server_content.output_transcription:
        print("Transcript:", server_content.output_transcription.text)
        self.AI_answer=self.AI_answer+ server_content.output_transcription.text


    if server_content.input_transcription:
        print('Transcript:', server_content.input_transcription.text)
        self.USER_query=self.USER_query+ server_content.input_transcription.text
    return




async def handle_tool_call(self, tool_call):
    print(tool_call.function_calls)
    for fc in tool_call.function_calls:
        if fc.name == "stay_silent":
            print("AI requested to stay silent")
            self.listening_state="AWAITING_HOTWORD"
            self.stay_silent=True
            break

        if fc.name=="play_music":
            await asyncio.to_thread(self.song_on)
            subprocess.Popen(f"mpv $(yt-dlp -f ba 'ytsearch:{fc.args["song"]}' -g)",shell=True)
            self.listening_state="AWAITING_HOTWORD"
            self.stay_silent=True
            break
        if fc.name=="set_timer":
            subprocess.Popen(f"sleep {fc.args["timer_duration"]} ; exec play /home/pi/Inta_Robo2/soundeffects/timer.mp3",shell=True)
            break
        server=""
        for key in list(self.mcp_client.sessions.keys()):
            response = await self.mcp_client.sessions[key].list_tools()
            tools = response.tools
            for tool in tools:
                if tool.name==fc.name:
                    server=key
                    break
                        
        result = await self.mcp_client.sessions[server].call_tool(
            name=fc.name,
            arguments=fc.args,
        )
        print(result)

        tool_response = types.LiveClientToolResponse(
            function_responses=[types.FunctionResponse(
                name=fc.name,
                id=fc.id,
                response={'result':result},
            )]
        )

        print('\n>>> ', tool_response)
        await self.session.send(input="SYSTEM:You have only thought and not spoken anything. Please review your internal format instructions ." , end_of_turn=False)

        await self.session.send(input=tool_response)
