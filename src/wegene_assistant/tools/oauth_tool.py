import asyncio
import time
import webbrowser
from oauthlib.oauth2 import WebApplicationClient
import redislite
import os
from dotenv import load_dotenv
from mcp.types import TextContent

load_dotenv()

# Initialize RedisLite
redis_db = redislite.Redis(os.getenv('REDIS_DB_PATH'))

# WeGene OAuth configuration
WEGENE_CLIENT_ID = os.getenv('WEGENE_CLIENT_ID')
WEGENE_CLIENT_SECRET = os.getenv('WEGENE_CLIENT_SECRET')
WEGENE_AUTH_URL = "https://api.wegene.com/authorize/"
REDIRECT_URI = "http://localhost:8787/oauth/callback"

async def wegene_oauth():

    redis_db.delete('wegene_access_token')

    # Initialize OAuth2 client
    client = WebApplicationClient(WEGENE_CLIENT_ID)
    
    # Prepare authorization URL
    authorization_url = client.prepare_request_uri(
        WEGENE_AUTH_URL,
        redirect_uri=REDIRECT_URI,
        scope="basic names athletigen skin psychology risk health"
    )

    webbrowser.open(authorization_url)
    
    # Poll for access token for 120 seconds
    start_time = time.time()
    while time.time() - start_time < 120:
        if redis_db.exists('wegene_access_token'):
            return [
                TextContent(
                    type="text",
                    text="User authorization succeeded and access token retrieved. Continue to retrieve user profiles.",
                )
            ]
        await asyncio.sleep(1)
    
    return [
        TextContent(
            type="text",
            text="Error: User authorization failed in 120 seconds. Please try again."
        )
    ]