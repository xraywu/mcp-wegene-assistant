import os
import json
import redislite
import httpx


async def get_wegene_report(report_endpoint: str, report_id: str, profile_id: str) -> str:
    """
    Read report from WeGene Open API
    :param uri: resource uri, wegene://{report_endpoint}/{report_id}/{profile_id}
    :return: JSON string of the results
    """

    # Get WeGene access token
    access_token = redislite.Redis(os.getenv('REDIS_DB_PATH')).get('wegene_access_token')
    if not access_token:
        raise ValueError("No valid user access token. Please use wegene-oauth tool first.")
    
    # Prepare request
    url = f"https://api.wegene.com/{report_endpoint}/{profile_id}"
    headers = {
        "Authorization": f"Bearer {access_token.decode('utf-8')}",
        "Content-Type": "application/json"
    }
    data = {
        "report_id": report_id
    }
    
    # Call WeGene API
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise ValueError(f"Failed to retrieve report: {response.status_code} {response.text}")
        
        return response.text


def get_report_info() -> str:
    """
    Retrieve all report info. Since WeGene does not have a report list API, prebuild with config file.
    :return: JSON string of all reports
    """
    # Read config file
    reports_path = "config/reports.json"
    with open(reports_path, "r", encoding="utf-8") as f:
        reports = json.load(f)
    return json.dumps(reports, ensure_ascii=False)