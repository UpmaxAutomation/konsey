#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const API_BASE = process.env.LLM_COUNCIL_API || "http://localhost:8001";

// Helper to make API calls
async function apiCall(endpoint, method = "GET", body = null) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, options);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

// Create server
const server = new Server(
  {
    name: "llm-council",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "council_query",
        description:
          "Query the LLM Council with a question. Multiple AI models (GPT-4, Claude, Gemini, Grok) will answer, evaluate each other, and synthesize the best answer. Now with web search and memory context!",
        inputSchema: {
          type: "object",
          properties: {
            question: {
              type: "string",
              description: "The question to ask the LLM Council",
            },
          },
          required: ["question"],
        },
      },
      {
        name: "council_quick",
        description:
          "Get a quick synthesized answer from the LLM Council. Returns just the final answer without full deliberation details.",
        inputSchema: {
          type: "object",
          properties: {
            question: {
              type: "string",
              description: "The question to ask",
            },
          },
          required: ["question"],
        },
      },
      {
        name: "council_search",
        description: "Perform a web search and return results. Useful for finding current information.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query",
            },
            num_results: {
              type: "number",
              description: "Number of results (default 5)",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "council_execute",
        description: "Execute Python or JavaScript code and return the result. Useful for calculations, data processing, or testing code.",
        inputSchema: {
          type: "object",
          properties: {
            code: {
              type: "string",
              description: "Code to execute",
            },
            language: {
              type: "string",
              enum: ["python", "javascript"],
              description: "Programming language (python or javascript)",
            },
            timeout: {
              type: "number",
              description: "Timeout in seconds (default 30)",
            },
          },
          required: ["code", "language"],
        },
      },
      {
        name: "council_memory",
        description: "Store or retrieve information from the council's memory. Remember facts, decisions, or preferences.",
        inputSchema: {
          type: "object",
          properties: {
            action: {
              type: "string",
              enum: ["remember_fact", "remember_decision", "set_preference", "get_context", "clear", "stats"],
              description: "Memory action to perform",
            },
            content: {
              type: "string",
              description: "Fact to remember or query for context",
            },
            category: {
              type: "string",
              description: "Category for the fact (default: general)",
            },
            question: {
              type: "string",
              description: "Question for remember_decision",
            },
            decision: {
              type: "string",
              description: "Decision for remember_decision",
            },
            key: {
              type: "string",
              description: "Key for set_preference",
            },
            value: {
              type: "string",
              description: "Value for set_preference",
            },
          },
          required: ["action"],
        },
      },
      {
        name: "council_config",
        description: "View or update the LLM Council configuration (models, features)",
        inputSchema: {
          type: "object",
          properties: {
            action: {
              type: "string",
              enum: ["get", "set", "reset"],
              description: "Action: get config, set new config, or reset defaults",
            },
            council_models: {
              type: "array",
              items: { type: "string" },
              description: "Model IDs for the council (for 'set')",
            },
            chairman_model: {
              type: "string",
              description: "Model ID for chairman (for 'set')",
            },
          },
          required: ["action"],
        },
      },
      {
        name: "council_features",
        description: "Enable or disable enhanced features (web_search, code_execution, memory)",
        inputSchema: {
          type: "object",
          properties: {
            web_search: {
              type: "boolean",
              description: "Enable/disable web search",
            },
            code_execution: {
              type: "boolean",
              description: "Enable/disable code execution",
            },
            memory: {
              type: "boolean",
              description: "Enable/disable memory",
            },
          },
        },
      },
      {
        name: "council_usage",
        description: "Get session usage statistics (tokens, cost)",
        inputSchema: {
          type: "object",
          properties: {
            reset: {
              type: "boolean",
              description: "Reset usage stats if true",
            },
          },
        },
      },
      {
        name: "council_models",
        description: "List all available models with pricing, model count, and last sync time",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "council_refresh_models",
        description: "Force refresh models from OpenRouter API to get the latest available models",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "council_query": {
        const conv = await apiCall("/api/conversations", "POST", {});
        const result = await apiCall(
          `/api/conversations/${conv.id}/message`,
          "POST",
          { content: args.question }
        );

        let response = "# LLM Council Response\n\n";

        // Show context used
        if (result.metadata?.context_used) {
          const ctx = result.metadata.context_used;
          if (ctx.web_search || ctx.memory) {
            response += "**Context Used:** ";
            const used = [];
            if (ctx.web_search) used.push("Web Search");
            if (ctx.memory) used.push("Memory");
            response += used.join(", ") + "\n\n";
          }
        }

        // Stage 1
        response += "## Stage 1: Individual Responses\n\n";
        for (const r of result.stage1) {
          const modelName = r.model.split("/")[1] || r.model;
          response += `### ${modelName}\n${r.response}\n\n`;
        }

        // Stage 2
        response += "## Stage 2: Rankings\n\n";
        if (result.metadata?.aggregate_rankings) {
          response += "**Aggregate Rankings:**\n";
          for (let i = 0; i < result.metadata.aggregate_rankings.length; i++) {
            const rank = result.metadata.aggregate_rankings[i];
            const modelName = rank.model.split("/")[1] || rank.model;
            response += `${i + 1}. ${modelName} (avg: ${rank.average_rank})\n`;
          }
          response += "\n";
        }

        // Stage 3
        response += "## Stage 3: Final Synthesis\n\n";
        response += result.stage3.response;

        return { content: [{ type: "text", text: response }] };
      }

      case "council_quick": {
        const conv = await apiCall("/api/conversations", "POST", {});
        const result = await apiCall(
          `/api/conversations/${conv.id}/message`,
          "POST",
          { content: args.question }
        );

        return {
          content: [
            { type: "text", text: `**Council's Answer:**\n\n${result.stage3.response}` },
          ],
        };
      }

      case "council_search": {
        const result = await apiCall("/api/tools/search", "POST", {
          query: args.query,
          num_results: args.num_results || 5,
        });

        let response = `**Search Results for:** ${args.query}\n\n`;
        for (const r of result.results) {
          response += `**${r.title}**\n${r.url}\n${r.snippet}\n\n`;
        }

        return { content: [{ type: "text", text: response }] };
      }

      case "council_execute": {
        const result = await apiCall("/api/tools/execute", "POST", {
          code: args.code,
          language: args.language,
          timeout: args.timeout || 30,
        });

        let response = `**Code Execution (${args.language})**\n\n`;
        response += `Status: ${result.success ? "Success" : "Failed"}\n`;
        response += `Time: ${result.execution_time}s\n\n`;

        if (result.stdout) {
          response += `**Output:**\n\`\`\`\n${result.stdout}\n\`\`\`\n`;
        }
        if (result.stderr) {
          response += `**Errors:**\n\`\`\`\n${result.stderr}\n\`\`\`\n`;
        }

        return { content: [{ type: "text", text: response }] };
      }

      case "council_memory": {
        const result = await apiCall("/api/tools/memory", "POST", args);

        if (args.action === "get_context") {
          return {
            content: [{ type: "text", text: `**Memory Context:**\n\n${result.context}` }],
          };
        } else if (args.action === "stats") {
          const s = result.stats;
          return {
            content: [
              {
                type: "text",
                text: `**Memory Stats:**\n- Facts: ${s.facts_count}\n- Decisions: ${s.decisions_count}\n- Preferences: ${s.preferences_count}`,
              },
            ],
          };
        } else {
          return {
            content: [{ type: "text", text: `Memory action '${args.action}' completed.` }],
          };
        }
      }

      case "council_config": {
        if (args.action === "get") {
          const config = await apiCall("/api/config");
          return {
            content: [
              {
                type: "text",
                text: `**Council Config:**\n\n**Members:**\n${config.council_models
                  .map((m) => `- ${m}`)
                  .join("\n")}\n\n**Chairman:** ${config.chairman_model}`,
              },
            ],
          };
        } else if (args.action === "set") {
          const updateData = {};
          if (args.council_models) updateData.council_models = args.council_models;
          if (args.chairman_model) updateData.chairman_model = args.chairman_model;
          const result = await apiCall("/api/config", "POST", updateData);
          return {
            content: [
              {
                type: "text",
                text: `**Config Updated:**\n${result.council_models.map((m) => `- ${m}`).join("\n")}\n\nChairman: ${result.chairman_model}`,
              },
            ],
          };
        } else if (args.action === "reset") {
          const result = await apiCall("/api/config/reset", "POST");
          return {
            content: [{ type: "text", text: `Config reset to defaults.` }],
          };
        }
        throw new Error("Invalid action");
      }

      case "council_features": {
        const result = await apiCall("/api/features", "POST", args);
        return {
          content: [
            {
              type: "text",
              text: `**Features:**\n- Web Search: ${result.web_search ? "ON" : "OFF"}\n- Code Execution: ${result.code_execution ? "ON" : "OFF"}\n- Memory: ${result.memory ? "ON" : "OFF"}`,
            },
          ],
        };
      }

      case "council_usage": {
        if (args.reset) {
          await apiCall("/api/usage/reset", "POST");
          return { content: [{ type: "text", text: "Usage stats reset." }] };
        }

        const usage = await apiCall("/api/usage");
        const cost = usage.total_cost < 0.01 ? `$${usage.total_cost.toFixed(6)}` : `$${usage.total_cost.toFixed(4)}`;

        return {
          content: [
            {
              type: "text",
              text: `**Usage:**\n- Input: ${usage.total_input_tokens.toLocaleString()} tokens\n- Output: ${usage.total_output_tokens.toLocaleString()} tokens\n- Cost: ${cost}\n- Calls: ${usage.requests.length}`,
            },
          ],
        };
      }

      case "council_models": {
        const config = await apiCall("/api/config");
        let response = "**Available Models:**\n\n";

        // Show sync info
        response += `**Total Models:** ${config.models_count}\n`;
        response += `**Last Synced:** ${config.last_synced || "Never"}\n\n`;

        for (const [id, info] of Object.entries(config.available_models)) {
          response += `- **${info.name}** (\`${id}\`) - $${info.input_cost}/$${info.output_cost} per 1M\n`;
        }

        return { content: [{ type: "text", text: response }] };
      }

      case "council_refresh_models": {
        const result = await apiCall("/api/models/refresh", "POST");
        const response = `**Models Refreshed:**\n- Total Models: ${result.models_count}\n- Last Synced: ${result.last_synced}\n- Status: ${result.status}`;
        return { content: [{ type: "text", text: response }] };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("LLM Council MCP server running with enhanced features");
}

main().catch(console.error);
