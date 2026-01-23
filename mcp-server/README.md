# LLM Council MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that lets AI assistants like Claude query the LLM Council directly.

## What is this?

This MCP server exposes the LLM Council as a set of tools that AI assistants can use. When you ask Claude a question, it can consult the council of AI models (GPT-4, Gemini, Grok, etc.) and get a synthesized answer.

## Available Tools

| Tool | Description |
|------|-------------|
| `council_query` | Full council deliberation with all 3 stages |
| `council_quick` | Quick answer (just the synthesis) |
| `council_search` | Web search for current information |
| `council_execute` | Execute Python/JavaScript code |
| `council_memory` | Store/retrieve facts and decisions |
| `council_config` | View/update council configuration |
| `council_features` | Toggle web search, code execution, memory |
| `council_usage` | View token usage and costs |
| `council_models` | List all available models |
| `council_refresh_models` | Refresh model list from OpenRouter |

## Installation

### Prerequisites

- LLM Council backend running (default: `http://localhost:8001`)
- Node.js 18+

### Setup

```bash
cd mcp-server
npm install
```

### Configure Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "llm-council": {
      "command": "node",
      "args": ["/path/to/llm-council/mcp-server/index.js"],
      "env": {
        "LLM_COUNCIL_API": "http://localhost:8001"
      }
    }
  }
}
```

### Configure for Other MCP Clients

The server uses stdio transport, so it works with any MCP-compatible client:

```bash
# Run directly
LLM_COUNCIL_API=http://localhost:8001 node index.js

# Or use npm
npm start
```

## Usage Examples

Once configured, you can ask Claude things like:

- "Ask the council: What's the best approach to implement a caching layer?"
- "Use council_quick to get a fast answer about React hooks"
- "Search the web for the latest news on AI"
- "Execute this Python code: `print(sum(range(100)))`"
- "Remember that I prefer TypeScript over JavaScript"
- "What's the council's current configuration?"

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_COUNCIL_API` | `http://localhost:8001` | Backend API URL |

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Claude    │────▶│ MCP Server  │────▶│  Backend    │
│  (Client)   │◀────│  (stdio)    │◀────│  (FastAPI)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ OpenRouter  │
                    │    API      │
                    └─────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       ┌────────┐    ┌────────┐    ┌────────┐
       │ GPT-4  │    │ Claude │    │ Gemini │
       └────────┘    └────────┘    └────────┘
```

## Development

```bash
# Run in development
npm start

# Debug MCP communication
DEBUG=* npm start
```

## Troubleshooting

### "API error: 404"
Make sure the LLM Council backend is running on the configured URL.

### "Connection refused"
Check that:
1. Backend is running: `curl http://localhost:8001/`
2. No firewall blocking the connection
3. Correct URL in `LLM_COUNCIL_API`

### Claude doesn't see the tools
1. Restart Claude Desktop after config changes
2. Check the config file syntax (valid JSON)
3. Verify the path to index.js is correct

## License

Same as the main LLM Council project.
