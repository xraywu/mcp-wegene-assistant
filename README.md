# wegene-assistant MCP server

[![smithery badge](https://smithery.ai/badge/@xraywu/mcp-wegene-assistant)](https://smithery.ai/server/@xraywu/mcp-wegene-assistant)

MCP server for WeGene Assistant, using LLM to analyze a user's WeGene genetic testing report.

## Components

### Resources

Once a user is authorized, all the reports under his/her account will be exposed as a resource:
- Custom wegene:// URI scheme for accessing each individual report
- A report resource has a name, description and application/json mimetype


### Tools

The server implements one tool:
- **wegene-oauth:** Start a WeGene Open API oAuth process in the browser
  - The user should complete the authorization in 120 seconds so LLM will be able to further access the reports.
- **wegene-get-profiles:** Read the profile list under a user's WeGene account
  - Profiles' name and id will be returned for LLM to use.
- **wegene-get-report-info:** Return the report meta info so LLM will know what reports are available.
  - A list of report names, descriptions, endpoints, etc. will be returned
- **wegene-get-report:** Read the results of a single report under a profile
  - Returns the result JSON specified in [WeGene's Open API platform](https://api.wegene.com)
  - Arguements 
    - report_endpoint: The report's endpoint to be retrieved from
    - report_id: The report's id to be retrieved
    - profile_id: The profile id to retrieve report from

## Configuration

- You will need WeGene Open API key/secret to use this project.
- Copy `.env.example` as `.env` and update the key and secret in the file.

## Quickstart

### Install

#### Installing via Smithery

To install WeGene Assistant for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@xraywu/mcp-wegene-assistant):

```bash
npx -y @smithery/cli install @xraywu/mcp-wegene-assistant --client claude
```

#### Insall Locally

##### Prepare MCP Server

1. Clone this project
2. Run `uv sync --dev --all-extras` under the project's root folder

##### Claude Desktop Configuration

- On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
- On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

Add below contents in the configuration file:

```
{
  "mcpServers": {
    "wegene-assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/wegene-assistant",
        "run",
        "wegene-assistant"
      ]
    }
  }
}
```
