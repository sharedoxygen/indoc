# inDoc Chat - User Guide

**Version:** 1.1.0  
**Last Updated:** October 11, 2025

---

## Welcome to inDoc Conversational Chat

inDoc's chat feature lets you have natural conversations with your document library. Ask questions, get insights, and explore your documents through an intelligent AI assistant.

---

## Getting Started

### 1. Select Your Documents

Before asking questions, select the documents you want to chat about:

1. Navigate to the **Chat** page
2. Browse your document library on the left panel
3. Check the boxes next to relevant documents (minimum 3 recommended)
4. Or use the search bar to find specific documents

**💡 Tip:** Select at least 3-5 documents for best results. The AI provides more accurate answers when it has sufficient context.

### 2. Ask Your Question

Type your question in the chat box and press Enter or click Send.

**Good Questions:**
- "What are the main points in these documents?"
- "Compare the approaches mentioned in these research papers"
- "Summarize the financial data from Q3 reports"
- "Are there any compliance issues mentioned?"

**Tips for Better Answers:**
- Be specific: "What's the revenue growth?" vs "Tell me about revenue"
- Reference document types: "Based on the PDF reports..."
- Ask follow-up questions: The AI remembers your conversation
- Use suggested questions: Click the suggested question chips

### 3. Understand the Response

Each response includes:
- **Answer:** Grounded in your selected documents
- **Sources:** Documents used to generate the answer
- **Suggested Questions:** Related follow-up questions you might ask

**Understanding Quality Indicators:**
- ✅ **High Confidence:** Answer strongly supported by documents
- ⚠️ **Verification Needed:** Some claims may need cross-checking
- ℹ️ **Insufficient Context:** Need more documents selected

---

## Features

### Conversation Memory
The AI remembers your entire conversation. You can:
- Ask follow-up questions without repeating context
- Reference previous answers ("What about the second point you mentioned?")
- Build on earlier analysis progressively

**History:** Last 6 messages are included in context

### Multi-Document Analysis
Select multiple documents to:
- Compare and contrast information
- Find patterns across documents
- Synthesize insights from various sources
- Cross-reference data

### Answer Grounding
Every answer is grounded in your actual documents:
- **Minimum 3 sources required** for confident answers
- Response includes which documents were used
- Claims are verified against retrieved content
- No fabricated information - only what's in your documents

### Intelligent Features
- **Suggested Questions:** AI proposes relevant follow-ups
- **Source Citations:** See which documents support each claim
- **Context Awareness:** Remembers conversation thread
- **Progressive Display:** Responses stream in real-time (no 30s wait)

---

## Best Practices

### Document Selection

**Do:**
- ✅ Select 3-5 related documents for focused analysis
- ✅ Use search to find relevant documents first
- ✅ Include variety (different perspectives, data sources)
- ✅ Add more documents if answer is insufficient

**Don't:**
- ❌ Select only 1 document (below minimum threshold)
- ❌ Select unrelated documents (confuses context)
- ❌ Select 100+ documents (overwhelming context)

### Question Formulation

**Do:**
- ✅ Ask specific, focused questions
- ✅ Reference document types ("in the PDFs...")
- ✅ Build on previous answers with follow-ups
- ✅ Use suggested questions as starting points

**Don't:**
- ❌ Ask multiple unrelated questions at once
- ❌ Ask about information not in your documents
- ❌ Expect answers beyond document scope

### Conversation Management

**Do:**
- ✅ Start new conversation for different topics
- ✅ Use conversation history to review past discussions
- ✅ Keep conversations focused on related topics
- ✅ Export important conversations for reference

**Don't:**
- ❌ Mix unrelated topics in one conversation
- ❌ Expect the AI to remember conversations from weeks ago
- ❌ Assume AI can access documents you haven't selected

---

## Troubleshooting

### "I don't have enough information to answer confidently"

**Reason:** Less than 3 documents selected or documents don't contain relevant information

**Solution:**
1. Select more documents (aim for 3-5)
2. Search for documents related to your question
3. Rephrase your question to match available document content
4. Upload additional documents if needed

### "AI service temporarily unavailable"

**Reason:** Language model service is down (Ollama or OpenAI)

**Solution:**
1. Wait a moment and try again (auto-fallback in progress)
2. Use Search feature instead
3. Browse documents directly
4. Contact administrator if persists

### Response Seems Off-Topic

**Reason:** Selected documents don't match your question

**Solution:**
1. Review selected documents
2. Use search to find more relevant documents
3. Refine your question to be more specific
4. Check document content previews

### Slow Response Time

**Reason:** Large document set or complex analysis

**Solution:**
1. Reduce number of selected documents (5-10 optimal)
2. Be patient - complex analysis takes 10-20 seconds
3. Use streaming endpoint for progressive display
4. Try more specific questions (faster processing)

---

## Security & Privacy

### Your Data is Safe
- **Private:** Conversations are private to your account
- **Tenant Isolation:** Can't access other organizations' data
- **Role-Based:** Access controlled by your permissions
- **Encrypted:** Data encrypted at rest and in transit

### What Gets Logged
- Search queries (for improving results)
- Response times (for performance monitoring)
- Errors (for troubleshooting)

### What Doesn't Get Logged
- Full document content (only metadata)
- Personal information (unless in document titles)
- Detailed conversation content (only metadata)

---

## Advanced Tips

### Using Analytics Mode
Ask broad questions to trigger analytics:
- "How many documents do I have?"
- "Summarize my library by category"
- "Show breakdown by file type"

### Exploring Document Relationships
- "Which documents mention Project X?"
- "Find documents related to Q3 2024"
- "Show all contracts from Vendor Y"

### Comparative Analysis
- "Compare version 1 and version 2 of the proposal"
- "What changed between these two reports?"
- "Which document has the most recent data?"

---

## Keyboard Shortcuts

- **Enter:** Send message
- **Shift + Enter:** New line in message
- **Esc:** Clear message input
- **Ctrl/Cmd + K:** Focus search box

---

## FAQ

**Q: How many documents can I select at once?**
A: We recommend 3-10 documents for optimal performance. The system supports up to 50, but more documents = longer processing time.

**Q: Can the AI access documents I haven't selected?**
A: No. The AI only sees documents you explicitly select. This ensures focused, relevant answers.

**Q: Does the AI remember everything I've asked?**
A: The AI remembers the last 6 messages in your current conversation. Start a new conversation for unrelated topics.

**Q: Can I edit my question after sending?**
A: Not currently. If you made a typo, simply send a correction message.

**Q: How do I save important conversations?**
A: Use Chat History to view past conversations. Export feature coming soon.

**Q: What languages are supported?**
A: English is fully supported. Other languages may work but aren't officially supported yet.

**Q: Can multiple users chat about the same documents?**
A: Each user has private conversations. Document sharing is controlled by permissions.

---

## Need Help?

- **In-App Support:** Click the help icon (?)
- **Administrator:** Contact your inDoc administrator
- **Documentation:** Check our full documentation at docs/
- **Logs:** Administrators can view system logs for troubleshooting

---

## What's New

### Version 1.1.0 (October 2025)
- ✨ **Streaming Responses:** See answers appear progressively
- ✨ **Answer Grounding:** Minimum 3 sources for quality assurance
- ✨ **LLM Fallback:** Automatic failover if primary AI service down
- ✨ **Suggested Questions:** AI proposes relevant follow-ups
- ✨ **Conversation Memory:** Remembers last 6 messages
- 🔒 **Enhanced Security:** Password policies, JWT validation

---

**Happy Chatting!** 🎉

For technical documentation, see `private-docs/` (administrators only).

