# Chat Interface

Interactive conversational interface with LLM orchestration for natural language access to all VBAgent functions.

## Overview

The chat interface provides a natural language way to interact with VBAgent. Instead of remembering CLI commands, just describe what you want in plain English. The LLM orchestrator automatically selects and executes the appropriate tools based on your request.

## Quick Start

```bash
# Start interactive chat session
vbagent chat

# Use custom model
vbagent chat --model gpt-5.2

# Load previous conversation
vbagent chat --history conversation.json

# Auto-save conversation on exit
vbagent chat --save-history session.json
```

**Exit commands:** Type `exit`, `quit`, or `q` to end the session. Press `Ctrl+C` or `Ctrl+D` to interrupt.

---

## Features

✨ **Natural Language Commands** - No need to remember exact CLI syntax

🔄 **Multi-Turn Conversations** - Context is maintained across messages

🛠️ **Automatic Tool Orchestration** - LLM automatically calls appropriate vbagent functions

🎨 **Rich Terminal Output** - Beautiful formatted output with colors and panels

💾 **Conversation History** - Load/save conversations for later

🤖 **Smart Clarification** - Asks follow-up questions when information is missing

---

## Available Capabilities

The chat interface has access to all VBAgent tools:

| Category | Tools | What You Can Ask |
|----------|-------|------------------|
| **Image Processing** | `scan`, `classify` | "Scan this question image", "Classify question.png" |
| **Diagram Generation** | `tikz` | "Generate a free body diagram", "Create TikZ from diagram.png" |
| **Problem Generation** | `generate_problem` | "Create a passage on friction", "Generate 3 MCQs on kinematics" |
| **Variants** | `variant` | "Create numerical variants", "Generate context variants" |
| **Format Conversion** | `convert` | "Convert to MCQ format", "Change to subjective type" |
| **Question Bank** | `index_question_bank`, `query_questions` | "Index my questions folder", "Find medium difficulty mechanics problems" |
| **DPP Creation** | `create_dpp` | "Create a 10 question DPP", "Make a balanced practice set" |
| **LaTeX Parsing** | `extract_subitems`, `parse_latex_project` | "Extract problems from main.tex", "Parse this LaTeX project" |
| **Export** | `export_files`, `export_directory` | "Export as flat structure", "Create project with main.tex" |
| **Metadata** | `index_metadata`, `query_metadata` | "Index metadata", "Query kinematics questions" |

---

## Example Conversations

### 1. Scan Question Image

```
You: Scan question.png and save to output.tex

Assistant: I'll scan the image and extract LaTeX.
⚙ Executing tool: scan...
✓ Tool completed: scan

LaTeX extracted successfully! Saved to output.tex
```

### 2. Generate Problem from Idea

```
You: Create a problem on double block friction system

Assistant: I can help you generate a problem on double block friction! What topic is this for?

You: Mechanics

Assistant: Great! What type of question would you like? (mcq_sc, passage, subjective)

You: passage with 3 questions

Assistant: Perfect! Generating passage with 3 questions on double block friction system...
⚙ Executing tool: generate_problem...
✓ Tool completed: generate_problem

Problem generated successfully! Saved to generated_problem.tex
```

### 3. Create DPP Set

```
You: Create a 10 question DPP from mechanics with balanced difficulty

Assistant: I'll create a balanced DPP with 10 questions from mechanics.
⚙ Executing tool: create_dpp...
✓ Tool completed: create_dpp

DPP created with 10 questions (4 easy, 4 medium, 2 hard). Saved to dpp_2026-02-15.tex
```

### 4. Query Question Bank

```
You: Find all medium difficulty kinematics problems

Assistant: Searching question bank for medium difficulty kinematics problems...
⚙ Executing tool: query_questions...
✓ Tool completed: query_questions

Found 23 problems matching your criteria:
- Problem #42: Projectile motion with air resistance
- Problem #57: Relative velocity in 2D
- Problem #89: Circular motion with friction
...
```

### 5. Generate Variants

```
You: Create 3 numerical variants of problem.tex

Assistant: Generating 3 numerical variants...
⚙ Executing tool: variant...
✓ Tool completed: variant

3 numerical variants created successfully! Saved to variants/numerical_problem_1.tex, numerical_problem_2.tex, numerical_problem_3.tex
```

### 6. Export Questions

```
You: Export all questions in structured format to output/

Assistant: Exporting questions in structured format...
⚙ Executing tool: export_directory...
✓ Tool completed: export_directory

Questions exported to output/ with organized subdirectories by topic.
```

---

## Smart Clarification

The chat interface intelligently asks for missing information:

```
You: Generate a problem

Assistant: I can help you generate a problem! What should the problem be about?

You: Friction

Assistant: Great! What topic is this for? (e.g., Mechanics, Dynamics)

You: Mechanics

Assistant: Perfect! What type of question? (mcq_sc, passage, subjective, etc.)

You: passage

Assistant: How many questions should the passage have? (typically 2-4)

You: 3

Assistant: Generating passage on friction with 3 questions...
⚙ Executing tool: generate_problem...
✓ Tool completed

Problem generated successfully!
```

The assistant asks ONE question at a time, making the conversation natural and easy to follow.

---

## Tips for Best Results

### Be Specific

❌ **Vague:** "Process some images"  
✅ **Clear:** "Scan question_1.png and save to scans/q1.tex"

### Use Natural Language

You don't need to match exact parameter names:
- "Create a DPP with 10 questions" ✅
- "Make a practice set from kinematics" ✅
- "Generate numerical variants" ✅

### Provide Context

The assistant remembers previous messages:
```
You: Scan question.png

Assistant: [scans the image]

You: Now create 3 numerical variants

Assistant: [creates variants from the previously scanned file]
```

### Combine Multiple Steps

```
You: Scan question.png, classify it, and generate 2 numerical variants
```

The assistant will execute tools in the correct order.

---

## Command Options

```bash
vbagent chat [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--model <name>` | Override orchestrator model (e.g., `gpt-5.2`, `grok-4`) |
| `--history <file>` | Load conversation history from JSON file |
| `--save-history <file>` | Save conversation history to JSON file on exit |

### Examples

```bash
# Use specific model
vbagent chat --model gpt-5.2

# Continue previous conversation
vbagent chat --history session_2026-02-14.json

# Auto-save conversation
vbagent chat --save-history my_session.json

# Load and save
vbagent chat --history old.json --save-history new.json
```

---

## Troubleshooting

### Tool Execution Fails

If a tool fails, the assistant will show an error message. You can:
1. Check the error details
2. Rephrase your request
3. Provide missing information

### Conversation Gets Confused

If the assistant loses context:
1. Be more explicit in your request
2. Start a new session with `exit` and restart
3. Use `--save-history` to preserve important conversations

### Model Not Available

If your configured model isn't available:
```bash
vbagent chat --model gpt-5-mini  # Use a different model
```

---

## Related Commands

- `vbagent init` - Initialize workspace configuration
- `vbagent config` - Configure models and settings
- `vbagent mcp` - Run as MCP server for external agents

---

## See Also

- [CLI Commands](cli-commands.md) - Direct CLI command reference
- [Problem Generation](problem-generation.md) - Detailed problem generation guide
- [Database](database.md) - Question bank management
- [Batch Processing](batch-processing.md) - Process multiple files
