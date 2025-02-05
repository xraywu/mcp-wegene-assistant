from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

import json
from threading import Thread
from dotenv import load_dotenv
import os
import redislite
from pydantic import AnyUrl

from .tools.oauth_tool import wegene_oauth
from .tools.profile_tool import wegene_get_profiles
from .tools.report_tool import get_wegene_report, get_report_info
from .flask_server import run_flask
from .models import Profile, Report


# Load environment variables
load_dotenv()

# Initialize RedisLite
redis_db = redislite.Redis(os.getenv('REDIS_DB_PATH'))

# WeGene OAuth configuration
WEGENE_CLIENT_ID = os.getenv('WEGENE_CLIENT_ID')
WEGENE_CLIENT_SECRET = os.getenv('WEGENE_CLIENT_SECRET')
WEGENE_AUTH_URL = "https://api.wegene.com/authorize/"
WEGENE_TOKEN_URL = "https://api.wegene.com/token/"
REDIRECT_URI = "http://localhost:8787/oauth/callback"


# Store the profiles of current account
profiles: list[Profile] = []


# Available reports from WeGene
with open('config/reports.json') as f:
    reports = [Report(**report) for report in json.load(f)]


# Create MCP server
server = Server("wegene-assistant")


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:

    """
    A user can have multiple "profiles（检测报告）" under his/her WeGene account. 
    Each profile（检测报告）represeting the results of a person's single genetic test, consists of multiple reports（检测结果） for difference phenotypes.
    Here we list all the available reports under the user's account, possibly from multiple profiles.
    Each report（检测结果） is exposed as a resource with a custom wegene:// URI scheme.
    Each report（检测结果） represents the result of one single phenotype under one profile.
    """

    resources: list[types.Resource] = []
    
    for profile in profiles:
        for report in reports:
            if report.report_gender_category == '男' and profile.gender == '2':
                continue
            elif report.report_gender_category == '女' and profile.gender == '1':
                continue
            else:
                this_resource = types.Resource(
                    uri=AnyUrl(f"wegene://{report.report_endpoint}/{report.report_id}/{profile.profile_id}"),
                    name=f"Profile Name: {profile.name}; Gender: {profile.gender}; Report Category: {report.category}; Report Name: {report.report_name}",
                    description=f"Genetic test report of {report.report_name} for {profile.name}",
                    mimeType="application/json",
                )
                resources.append(this_resource)
    
    return resources


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:

    """
    Read a specific phenotype result report under a profile.
    The profile id and the phenotype is extracted from the URI.
    Report result and details returned in JSON format.
    Example result format:
    '''json
        {
            "score" : 60, # 0-100, relative score among the population for athletigen, skin, psychology, metabolism
            "genotypes" : [ # The list of the user's SNPs related to this phenotype report
                {
                    "tsummary" : "抗晒黑能力中等", # Effect of this SNP's genotype
                    "genotype" : "CT",  # Genotype of the SNP
                    "rsid" : "RS1015362" # SNP RSID
                },
                {
                    "genotype" : "CC",
                    "tsummary" : "抗晒黑能力弱",
                    "gene" : "IRF4",
                    "rsid" : "RS12203592"
                }
            ],
            "description" : "抗晒黑反应能力", # The report name
            "tsummary" : "喝酒不脸红", # The overall result for drug, traits,
            "rank" : "强", # The overall result for athletigen, skin, psychology, metabolism
            "risk": 0.31 # The overall result for health risk, the relative risk comparing to the average population
            "caseid" : "1522"  # The report ID
        }
    '''
    """

    if uri.scheme != "wegene":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")
    
    parts = [uri.host]
    parts.extend(uri.path.lstrip('/').split('/'))
    report_endpoint = '/'.join(parts[:-2])
    report_id = parts[-2]
    profile_id = parts[-1]

    if not (report_endpoint and report_id and profile_id):
        raise ValueError("Invalid URL schema")

    return await get_wegene_report(report_endpoint, report_id, profile_id)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:

    """
    A user can have multiple "profiles（检测报告）" under his/her WeGene account. 
    Each profile（检测报告）represeting the results of a person's single genetic test, consists of multiple reports（检测结果） for difference phenotypes.
    First, use wegene-oauth tool to authorize the user's account and set a valid access token for further use.
    Then, use wegene-get-profiles tool to retrieve the list of profiles under this user's account. Resource list will be updated according to all the profiles.
    Then, get the report info from wegene-get-report-info tool to retrieve the report IDs and categories.
    Finally, use wegene-get-report tool to retrieve the testing results from a profile.
    """
    
    return [
        types.Tool(
            name="wegene-oauth",
            description="Authorizing a user's account using WeGene Open API with oAuth2 protocol and retrieve a valid access token for further use",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="wegene-get-profiles",
            description="Retrieve all the profiles under the current account",
            inputSchema={
                "type": "object",
                "properties": {}
            },
        ),
        types.Tool(
            name="wegene-get-report-info",
            description="Get all available report information",
            inputSchema={
                "type": "object",
                "properties": {}
            },
        ),
        types.Tool(
            name="wegene-get-report",
            description="Get a specific genetic test report from a profile",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_endpoint": {
                        "type": "string",
                        "description": "The endpoint of the report"
                    },
                    "report_id": {
                        "type": "string",
                        "description": "The ID of the report"
                    },
                    "profile_id": {
                        "type": "string",
                        "description": "The ID of the profile"
                    }
                },
                "required": ["report_endpoint", "report_id", "profile_id"]
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    
    """
    Tools to retrieve genetic testing reports from WeGene.
    wegene-oauth: Start an OAuth Web procress and retireve the access token for further use. The tool will wait for 120 seconds for the user to complete the authorization process. If not completed, the tool will fail.
    wegene-get-profiles: Get all the profiles under the user's account and build resources accordingly.
    wegene-get-report-info: Get all the report information and metadata, including report ID, cegtagory, name, etc.
    wegene-get-report: Get the genetic testing report for a specific phenotype from a profile. Result return in JSON format.
        Example result format:
        ```json
            {
                "score" : 60, # 0-100, relative score among the population for athletigen, skin, psychology, metabolism
                "genotypes" : [ # The list of the user's SNPs related to this phenotype report
                    {
                        "tsummary" : "抗晒黑能力中等", # Effect of this SNP's genotype
                        "genotype" : "CT",  # Genotype of the SNP
                        "rsid" : "RS1015362" # SNP RSID
                    },
                    {
                        "genotype" : "CC",
                        "tsummary" : "抗晒黑能力弱",
                        "gene" : "IRF4",
                        "rsid" : "RS12203592"
                    }
                ],
                "description" : "抗晒黑反应能力", # The report name
                "tsummary" : "喝酒不脸红", # The overall result for drug, traits,
                "rank" : "强", # The overall result for athletigen, skin, psychology, metabolism
                "risk": 0.31 # The overall result for health risk, the relative risk comparing to the average population
                "caseid" : "1522"  # The report ID
            }
        ```
    """
    
    if name == "wegene-oauth":
        return await wegene_oauth()
    
    elif name == "wegene-get-profiles":
        result, new_profiles = await wegene_get_profiles()
        if new_profiles:
            profiles.clear()
            profiles.extend(new_profiles)
            await server.request_context.session.send_resource_list_changed()
        return result
    
    elif name == "wegene-get-report-info":
        return [
            types.TextContent(
                type="text",
                text=get_report_info()
            )
        ]
    
    elif name == "wegene-get-report":
        if not arguments:
            raise ValueError("Missing arguments")
        return [
            types.TextContent(
                type="text",
                text=await get_wegene_report(
                    arguments["report_endpoint"],
                    arguments["report_id"],
                    arguments["profile_id"]
                )
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")



async def main():
    # Start Flask server in a separate thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="wegene-assistant",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )