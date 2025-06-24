from google.genai import types
def clean_schema(schema):
    if isinstance(schema, dict):
        schema_copy = schema.copy()
        if 'additionalProperties' in schema_copy:
            del schema_copy['additionalProperties']
        if '$schema' in schema_copy:
            del schema_copy['$schema']
        
        # Recursively clean nested properties
        for key, value in schema_copy.items():
            if isinstance(value, (dict, list)):
                schema_copy[key] = clean_schema(value)
        return schema_copy
    elif isinstance(schema, list):
        return [clean_schema(item) for item in schema]
    else:
        return schema
                
def generate_config(tools,system_prompt):
    CONFIG = types.LiveConnectConfig(
            tools= tools,
            response_modalities= ["AUDIO",],
            system_instruction= types.Content(
                parts=[
                    types.Part(
                        text=system_prompt
                    )
                ]
            ),
            speech_config= types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Fenrir")
                ),
                # ),language_code="en-IN"
            ),
        realtime_input_config=  types.RealtimeInputConfig(automatic_activity_detection=types.AutomaticActivityDetection(disabled=False,start_of_speech_sensitivity= types.StartSensitivity.START_SENSITIVITY_HIGH,end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,silenceDurationMs=1000,prefix_padding_ms=300)),
        proactivity= { "proactiveAudio": False },
        enable_affective_dialog=True,
        # input_audio_transcription= {},
        # output_audio_transcription= {},

        )
    return CONFIG


async def configure(self):
    await self.mcp_client.connect_to_server()
    functional_tools = []

    for key in list(self.mcp_client.sessions.keys()):

        available_tools = await self.mcp_client.sessions[key].list_tools()
        print(available_tools)
        print("mcp tools initialised")
        python_tools = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": clean_schema(tool.inputSchema),
                        }
                        for tool in available_tools.tools
                    ]

        functional_tools = functional_tools+python_tools
    print(functional_tools)
    return  [
            {'function_declarations': functional_tools},
            {'google_search': {}},
            # {'code_execution': {}},
        ]