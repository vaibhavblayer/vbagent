# MCP Server Configuration Guide

## Issue: API Key Not Found

If you're getting an error like:
```
The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
```

This means the MCP server doesn't have access to your API keys.

## Solution: Configure Environment Variables in MCP Client

When running vbagent as an MCP server through Kiro or other MCP clients, you need to explicitly pass environment variables in the MCP configuration.

### For Kiro (TOML Format)

Edit your MCP configuration file (usually `.kiro/settings/mcp.toml` or `~/.kiro/settings/mcp.toml`):

```toml
[mcpServers.vbagent]
command = "vbagent"
args = ["mcp"]

[mcpServers.vbagent.env]
OPENAI_API_KEY = "${OPENAI_API_KEY}"
XAI_API_KEY = "${XAI_API_KEY}"
GOOGLE_API_KEY = "${GOOGLE_API_KEY}"
```

The `${VARIABLE_NAME}` syntax tells Kiro to use the value from your shell environment.

### For Kiro (JSON Format - if using older version)

Edit your MCP configuration file (usually `.kiro/settings/mcp.json` or `~/.kiro/settings/mcp.json`):

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

### Alternative: Hardcode API Keys (Not Recommended)

If environment variable substitution doesn't work, you can hardcode the keys (but this is less secure):

**TOML:**
```toml
[mcpServers.vbagent]
command = "vbagent"
args = ["mcp"]

[mcpServers.vbagent.env]
OPENAI_API_KEY = "sk-proj-..."
```

**JSON:**
```json
{
  "mcpServers": {
    "vbagent": {
      "command": "vbagent",
      "args": ["mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-proj-..."
      }
    }
  }
}
```

### For Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "vbagent": {
      "command": "vbagent",
      "args": ["mcp"],
      "env": {
        "OPENAI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### For Cursor

Add to your Cursor MCP settings:

```json
{
  "vbagent": {
    "command": "vbagent",
    "args": ["mcp"],
    "env": {
      "OPENAI_API_KEY": "your-api-key-here"
    }
  }
}
```

## Verifying Configuration

After updating your MCP configuration:

1. **Restart the MCP client** (Kiro, Claude Desktop, etc.)
2. **Test the connection** by trying to use a vbagent tool
3. **Check logs** with `vbagent mcp --verbose` if running manually

## Using Different Providers

### OpenAI (Default)

**TOML:**
```toml
[mcpServers.vbagent.env]
OPENAI_API_KEY = "sk-..."
```

**JSON:**
```json
{
  "env": {
    "OPENAI_API_KEY": "sk-..."
  }
}
```

### xAI (Grok)

**TOML:**
```toml
[mcpServers.vbagent.env]
XAI_API_KEY = "xai-..."
OPENAI_API_KEY = "xai-..."
```

**JSON:**
```json
{
  "env": {
    "XAI_API_KEY": "xai-...",
    "OPENAI_API_KEY": "xai-..."
  }
}
```

Note: vbagent will automatically use `XAI_API_KEY` if the base_url is set to xAI in your config.

### Google (Gemini)

**TOML:**
```toml
[mcpServers.vbagent.env]
GOOGLE_API_KEY = "AIza..."
OPENAI_API_KEY = "AIza..."
```

**JSON:**
```json
{
  "env": {
    "GOOGLE_API_KEY": "AIza...",
    "OPENAI_API_KEY": "AIza..."
  }
}
```

## Workspace Configuration

If you have a workspace-specific configuration (`.vbagent.json`), make sure it includes the provider settings:

```json
{
  "subject": "physics",
  "base_url": "https://api.x.ai/v1",
  "agents": {
    "scanner": {
      "model": "grok-4-1-fast-reasoning",
      "reasoning_effort": "high"
    }
  }
}
```

The MCP server will automatically load this configuration when running in that workspace.

## Troubleshooting

### 1. Environment Variables Not Being Passed

**Symptom**: API key error even though env vars are set in your shell

**Solution**: MCP clients don't automatically inherit shell environment variables. You must explicitly configure them in the MCP client's configuration file.

### 2. Wrong API Key for Provider

**Symptom**: Authentication error with non-OpenAI providers

**Solution**: Make sure you're using the correct API key for your configured provider:
- OpenAI: `OPENAI_API_KEY=sk-...`
- xAI: `XAI_API_KEY=xai-...`
- Google: `GOOGLE_API_KEY=AIza...`

### 3. Base URL Not Set

**Symptom**: Requests going to wrong endpoint

**Solution**: Check your `.vbagent.json` or global config has the correct `base_url`:
```json
{
  "base_url": "https://api.x.ai/v1"  // for xAI
}
```

### 4. MCP Server Not Starting

**Symptom**: MCP client can't connect to vbagent

**Solution**: 
1. Verify vbagent is installed: `vbagent --version`
2. Test manually: `vbagent mcp --verbose`
3. Check MCP client logs for connection errors

## Testing MCP Server Manually

To test the MCP server without a client:

```bash
# Start server with verbose logging
vbagent mcp --verbose

# In another terminal, send a test message
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | vbagent mcp
```

## Example: Complete Kiro Configuration

Here's a complete example for Kiro with all environment variables:

**TOML Format (Recommended):**
```toml
[mcpServers.vbagent]
command = "vbagent"
args = ["mcp"]
disabled = false
autoApprove = []

[mcpServers.vbagent.env]
OPENAI_API_KEY = "${OPENAI_API_KEY}"
XAI_API_KEY = "${XAI_API_KEY}"
GOOGLE_API_KEY = "${GOOGLE_API_KEY}"
PATH = "${PATH}"
```

**JSON Format (Alternative):**
```json
{
  "mcpServers": {
    "vbagent": {
      "command": "vbagent",
      "args": ["mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "XAI_API_KEY": "${XAI_API_KEY}",
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
        "PATH": "${PATH}"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Next Steps

After configuring your MCP client:

1. Restart the MCP client application
2. Try using a vbagent tool (e.g., `scan`, `classify`, `tikz`)
3. If issues persist, run `vbagent mcp --verbose` to see detailed logs
4. Check that your API keys are valid and have sufficient credits

## Support

If you continue to have issues:
1. Check that environment variables are set: `echo $OPENAI_API_KEY`
2. Verify vbagent config: `vbagent config show`
3. Test tools directly: `vbagent scan image.png`
4. Review MCP client documentation for environment variable syntax
