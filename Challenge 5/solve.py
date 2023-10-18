import discord
import requests

DISCORD_client_TOKEN = False # "MTEyNTk4MjE2NjM3MTc5NDk5NQ.Gw2dOT.CO8udIgmPB9eHvv9VveZeYVBG9U0Td_b1iTnco"
DISCORD_client_TOKEN_GEN_URL = "http://chals.tisc23.ctf.sg:45938/check"

def get_token():
    global DISCORD_client_TOKEN
    data = {"password": ':dIcH:..uU9gp1<@<3Q"DBM5F<)64S<(01tF(Jj%ATV@$Gl'}
    req = requests.post(DISCORD_client_TOKEN_GEN_URL, data=data)
    if req.status_code == 200:
        DISCORD_client_TOKEN = req.text.split(" ")[2]
        print(f">>> Discord client Token: {DISCORD_client_TOKEN} <<<")

if not DISCORD_client_TOKEN:
    get_token()

# Discord client

# Create a Discord client
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.guilds = True  # Add guilds intent to access audit logs
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name} ({client.user.id})')
    print('------')

    
    for guild in client.guilds:
        print(f'Checking permissions in Guild: {guild.name}')
        
        if guild:
            print(f'Permissions for Server: {guild.name}')
        
        async for entry in guild.audit_logs(limit=100000):  # You can adjust the limit as needed
            print(f'Action: {entry.action}')
            print(f'Target: {entry.target}')
            print(f'User: {entry.user}')
            print(f'Reason: {entry.reason}')
            print(" --- ")


# Start the client
client.run(DISCORD_client_TOKEN)
on_ready()