# AutoGPT Platform: Execution API, Monitoring & Integrations

REST/WebSocket surface for triggering and monitoring graph (agent) executions on
the self-hosted Platform, plus how credentials flow into blocks.

Default endpoints (local dev):
- Backend API: `http://localhost:8006/api`
- WebSocket: `ws://localhost:8001/ws`
- Frontend UI: `http://localhost:3000`

## Trigger types

**Manual execution:**
```http
POST /api/v1/graphs/{graph_id}/execute
Content-Type: application/json

{
  "inputs": {
    "input_name": "value"
  }
}
```

**Webhook trigger:**
```http
POST /api/v1/webhooks/{webhook_id}
Content-Type: application/json

{
  "data": "webhook payload"
}
```

**Scheduled execution:**
```json
{
  "schedule": "0 */2 * * *",
  "graph_id": "graph-uuid",
  "inputs": {}
}
```

## Monitoring execution

**WebSocket updates:**
```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(`Node ${update.node_id}: ${update.status}`);
};
```

**REST API polling:**
```http
GET /api/v1/executions/{execution_id}
```

## Building agents in the visual builder

1. **Open Agent Builder** at http://localhost:3000
2. **Add blocks** from the BlocksControl panel
3. **Connect nodes** by dragging between handles
4. **Configure inputs** in each node
5. **Run agent** using PrimaryActionBar

### Common blocks

**AI Blocks:**
- `AITextGeneratorBlock` - Generate text with LLMs
- `AIConversationBlock` - Multi-turn conversations
- `SmartDecisionMakerBlock` - Conditional logic

**Integration Blocks:**
- GitHub, Google, Discord, Notion connectors
- Webhook triggers and handlers
- HTTP request blocks

**Control Blocks:**
- Input/Output blocks
- Branching and decision nodes
- Loop and iteration blocks

## Integrations & credentials

### Adding credentials

1. Navigate to Profile > Integrations
2. Select provider (OpenAI, GitHub, Google, etc.)
3. Enter API keys or authorize OAuth
4. Credentials are encrypted and stored securely

### Using credentials in blocks

Blocks automatically access user credentials:

```python
class MyLLMBlock(Block):
    def execute(self, inputs):
        # Credentials are injected by the system
        credentials = self.get_credentials("openai")
        client = OpenAI(api_key=credentials.api_key)
        # ...
```

### Supported providers

| Provider | Auth Type | Use Cases |
|----------|-----------|-----------|
| OpenAI | API Key | LLM, embeddings |
| Anthropic | API Key | Claude models |
| GitHub | OAuth | Code, repos |
| Google | OAuth | Drive, Gmail, Calendar |
| Discord | Bot Token | Messaging |
| Notion | OAuth | Documents |
