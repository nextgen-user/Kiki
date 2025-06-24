# import asyncio
# from typing import Optional
# from contextlib import AsyncExitStack

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client

# import json


# class MCPClient:
#     def __init__(self):
#         # Initialize session and client objects
#         self.session: Optional[ClientSession] = None
#         self.exit_stack = AsyncExitStack()
        
#         self.messages = []

#     async def connect_to_server(self):
#         """
#         Connect to all MCP servers
#         """
#         with open('/home/pi/emo_v3/kiki-2025-03-06/mcp_handlers/mcp_config.json') as f:
#             mcp_servers = json.load(f)['mcpServers']

#         server='sysinfo'
        
#         server_params = StdioServerParameters(
#             command=mcp_servers[server]['command'],
#             args=mcp_servers[server]['args'],
#             env=None
#         )
        
#         stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
#         self.stdio, self.write = stdio_transport
#         self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
#         await self.session.initialize()
        
        
#         # List available tools
#         response = await self.session.list_tools()
#         tools = response.tools
        
#         # available_tools = [{ 
#         #     "name": tool.name,
#         #     "description": tool.description,
#         #     "input_schema": tool.inputSchema
#         # } for tool in response.tools]
        
#         print("\nConnected to server with tools:", [tool.name for tool in tools])

import asyncio
from typing import Dict
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import json


class MCPClient:
    def __init__(self):
        """
        Initialize the MCPClient.
        """
        # A dictionary to hold named session objects
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.messages = []

    async def connect_to_server(self):
        """
        Connect to all MCP servers defined in the configuration file.
        """
        try:
            with open('/home/pi/emo_v3/kiki-2025-03-06/mcp_handlers/mcp_config.json') as f:
                mcp_servers = json.load(f)['mcpServers']
        except FileNotFoundError:
            print("Error: mcp_config.json not found. Cannot connect to servers.")
            return
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing mcp_config.json: {e}")
            return

        print(f"Found {len(mcp_servers)} servers to connect to.")

        for server_name, config in mcp_servers.items():
            print(f"\n--- Connecting to '{server_name}' ---")
            try:
                server_params = StdioServerParameters(
                    command=config['command'],
                    args=config.get('args', []), # Use .get for optional args
                    env=config.get('env', None)     # Use .get for optional env
                )

                # Each server gets its own transport context managed by the exit stack
                stdio, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
                
                # Create a new client session for the server
                session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
                
                # Initialize the session and store it in our dictionary
                await session.initialize()
                self.sessions[server_name] = session

                # List available tools for the newly connected server
                response = await session.list_tools()
                tools = response.tools
                
                print(f"Successfully connected to '{server_name}'.")
                print(f"Available tools: {[tool.name for tool in tools]}")

            except Exception as e:
                print(f"Failed to connect to server '{server_name}': {e}")
        
        print("\n--- Connection process finished ---")
        print(f"Successfully connected to {len(self.sessions)} out of {len(mcp_servers)} servers.")


    async def disconnect(self):
        """
        Disconnects from all servers and cleans up resources.
        """
        print("Disconnecting from all servers...")
        await self.exit_stack.aclose()
        self.sessions.clear()
        print("All connections closed.")

# Example of how you might run this
async def main():
    client = MCPClient()
    await client.connect_to_all_servers()
    
    # You can now access sessions like this:
    # if 'sysinfo' in client.sessions:
    #     sysinfo_session = client.sessions['sysinfo']
    #     # ... use the session
    
    print("\nAll connected sessions:", list(client.sessions.keys()))
    
    # Disconnect when done
    await client.disconnect()

# To run the main function (optional, for demonstration)
# if __name__ == "__main__":
#     asyncio.run(main())