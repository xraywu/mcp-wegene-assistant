import httpx
import redislite
import os
from dotenv import load_dotenv
from mcp.types import TextContent
from ..models import Profile

load_dotenv()

# Initialize RedisLite
redis_db = redislite.Redis(os.getenv('REDIS_DB_PATH'))

async def wegene_get_profiles() -> tuple[list[TextContent], list[Profile] | None]:
    # Get access token from Redis
    access_token = redis_db.get('wegene_access_token')
    if not access_token:
        return [
            TextContent(
                type="text",
                text="Error: No valid user access token. Please use wegene-oauth tool first."
            )
        ], None

    # Make API request to get profiles
    try:
        headers = {
            "Authorization": f"Bearer {access_token.decode('utf-8')}"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.wegene.com/user/",
                headers=headers
            )
            response.raise_for_status()
            
            # Parse response and create new profiles list
            data = response.json()
            new_profiles = [
                Profile(
                    name=profile["name"],
                    gender=str(profile["sex"]),
                    profile_id=profile["id"]
                )
                for profile in data["profiles"]
            ]

            profile_info = "\n".join(
                f"Profile {i+1}: ID={profile.profile_id}, Name={profile.name}"
                for i, profile in enumerate(new_profiles)
            )
            return [
                TextContent(
                    type="text",
                    text=f"Successfully retrieved {len(new_profiles)} profiles(s):\n{profile_info}"
                )
            ], new_profiles
    except httpx.HTTPStatusError as e:
        return [
            TextContent(
                type="text",
                text=f"Error: Failed to get profile {str(e)}"
            )
        ], None