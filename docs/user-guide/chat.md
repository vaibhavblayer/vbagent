# Chat Interface

Interactive conversational interface with LLM orchestration for natural language access to all VBAgent functions.

## Overview

The chat interface provides a natural language way to interact with VBAgent. Instead of remembering CLI commands, just describe what you want in plain English.

## Starting Chat

```bash
vbagent chat
```

You'll see a welcome message:

```
╭─────────────────────────────────────────────────────────╮
│                                                         │
│  Welcome to VBAgent Chat!                              │
│                                                         │
│  Natural language interface to all vbagent functions   │
│                                                         │
╰─────────────────────────────────────────────────────────╯

You: 
```

## Features

✨ **Natural Language Commands**
- No need to remember exact CLI syntax
- Describe what you want in plain English
- The LLM understands context and intent

🔄 **Multi-Turn Conversations**
- Context is maintained across messages
- Reference previous results
- Build on earlier work

🛠️ **Automatic Tool Orchestration**
- LLM automatically calls appropriate vbagent functions
- Handles complex multi-step workflows
- Combines multiple tools as needed

🎨 **Rich Terminal Output**
- Beautiful formatted output with colors
- Progress indicators for long operations
- Structured display of results

💾 **Conversation History**
- Previous context is remembered
- Can reference earlier problems
- Maintains state across the session

## Example Conversations

### Basic Image Processing

```
You: Process this image: question.png
