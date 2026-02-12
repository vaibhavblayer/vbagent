# VBAgent MCP Quick Start

## TL;DR - Fix API Key Error

If you're getting "api_key client option must be set" error, add this to your Kiro MCP config:

### TOML Format (`.kiro/settings/mcp.toml`)

```toml
[mcpServers.vbagent]
command = "vbagent"
args = ["mcp"]

[mcpServers.vbagent.env]
OPENAI_API_KEY = "${OPENAI_API_KEY}"
XAI_API_KEY = "${XAI_API_KEY}"
GOOGLE_API_KEY = "${GOOGLE_API_KEY}"
```

### JSON Format (`.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "vbagent": {
      "command": "vbagent",
      "args": ["mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "XAI_API_KEY": "${XAI_API_KEY}",
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}"
      }
    }
  }
}
```

Then **restart Kiro** and try again!

## Available Tools

Once configured, you can use these vbagent tools through Kiro:

- **scan** - Extract LaTeX from physics question images
- **classify** - Classify question type, difficulty, topic
- **tikz** - Generate TikZ diagrams
- **process** - Full pipeline: scan → classify → extract → compile
- **dpp_create** - Create Daily Practice Problems
- **metadata_query** - Query question metadata database

## Testing

Test if it's working:

```bash
# In Kiro, try:
vbagent.scan({"image": "path/to/question.png"})
```

## More Info

See `MCP_CONFIGURATION_GUIDE.md` for detailed troubleshooting and configuration options.
