import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  List,
  ListItem,
  Avatar,
  CircularProgress,
  Divider,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
  Psychology as ModelIcon,
  Download as DownloadIcon,
  PictureAsPdf as PdfIcon,
  CheckCircle as CheckCircleIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { useWebSocket } from '../hooks/useWebSocket';
import { format } from 'date-fns';
import { ollamaService, OllamaModel } from '../services/ollamaService';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { jsPDF } from 'jspdf';
import { fetchWithTimeout } from '../services/http';
import ChatLoadingAnimation from './ChatLoadingAnimation';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface DocumentChatProps {
  documentIds?: string[];
  conversationId?: string;
  onNewConversation?: (conversationId: string) => void;
}

export const DocumentChat: React.FC<DocumentChatProps> = ({
  documentIds,
  conversationId: initialConversationId,
  onNewConversation
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<'searching' | 'analyzing' | 'generating' | 'done'>('searching');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [conversationId, setConversationId] = useState(initialConversationId);

  // CRITICAL FIX: Update local state when prop changes
  useEffect(() => {
    console.log('🔄 Prop conversationId changed from parent:', initialConversationId);
    setConversationId(initialConversationId);
  }, [initialConversationId]);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [availableModels, setAvailableModels] = useState<OllamaModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastScope, setLastScope] = useState<'all_accessible' | 'selected'>('all_accessible');
  const [lastSources, setLastSources] = useState<Array<{ id?: string; filename?: string; title?: string; file_type?: string; created_at?: string }>>([]);
  const [detectedIntent, setDetectedIntent] = useState<string | null>(null);
  const [intentConfidence, setIntentConfidence] = useState<number>(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastAssistantRef = useRef<HTMLDivElement>(null);
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    conversationId ? `/api/v1/chat/ws/chat/${conversationId}` : null
  );

  useEffect(() => {
    console.log('🔄 conversationId changed:', conversationId);
    if (conversationId) {
      console.log('📥 Loading conversation history for:', conversationId);
      loadConversationHistory();
    }
  }, [conversationId]);

  useEffect(() => {
    if (!lastMessage) return;
    const data = JSON.parse(lastMessage.data);
    switch (data.type) {
      case 'message':
        setMessages(prev => [...prev, data.message]);
        setIsTyping(false);
        setIsLoading(false);
        // Update scope and sources from message metadata
        try {
          setLastScope((data.message?.metadata?.scope as any) || 'all_accessible');
          setLastSources(Array.isArray(data.message?.metadata?.sources) ? data.message.metadata.sources : []);
        } catch { }
        break;
      case 'typing':
        setIsTyping(true);
        break;
      case 'error':
        console.error('Chat error:', data.message);
        setIsTyping(false);
        setIsLoading(false);
        break;
    }
  }, [lastMessage]);

  const ensureModelsLoaded = async () => {
    if (modelsLoaded || modelsLoading) return;
    setModelsLoading(true);
    try {
      const models = await ollamaService.getAvailableModels();
      setAvailableModels(models);
      if (models.length > 0 && !selectedModel) {
        setSelectedModel(models[0].name);
      }
      setModelsLoaded(true);
    } catch (error) {
      console.error('Failed to load Ollama models:', error);
    } finally {
      setModelsLoading(false);
    }
  };

  // Preload models once when the chat mounts (so the dropdown is ready)
  useEffect(() => {
    // Don't block UI; fire and forget
    ensureModelsLoaded();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages]);

  const scrollToBottom = () => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); };

  const loadConversationHistory = async () => {
    try {
      console.log('📡 Fetching conversation:', conversationId);
      const response = await fetchWithTimeout(`/api/v1/chat/conversations/${conversationId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        timeoutMs: 8000
      });
      console.log('📊 Response status:', response.status);
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Conversation data:', data);
        console.log('📨 Messages count:', data.messages?.length || 0);
        setMessages(data.messages || []);
      } else {
        console.error('❌ Response not OK:', response.status, await response.text());
      }
    } catch (error) {
      console.error('❌ Failed to load conversation history:', error);
    }
  };

  // Intent detection function
  const detectIntent = (message: string): { intent: string; confidence: number } => {
    const normalized = message.toLowerCase();

    // PRODUCTION-GRADE Analytics intent patterns
    const analyticsPatterns = [
      { pattern: /summarize.*documents.*by.*type.*and.*category/i, intent: 'analytics_summary', confidence: 0.98 },
      { pattern: /summarize.*documents.*by.*category/i, intent: 'analytics_summary', confidence: 0.95 },
      { pattern: /summarize.*documents.*by.*type/i, intent: 'analytics_summary', confidence: 0.95 },
      { pattern: /summarize.*all.*documents.*by.*category/i, intent: 'analytics_summary', confidence: 0.95 },
      { pattern: /summarize.*by.*category/i, intent: 'analytics_summary', confidence: 0.9 },
      { pattern: /summarize.*by.*type/i, intent: 'analytics_summary', confidence: 0.9 },
      { pattern: /summarize.*all.*documents/i, intent: 'analytics_summary', confidence: 0.85 },
      { pattern: /summarize.*documents/i, intent: 'analytics_summary', confidence: 0.8 },
      { pattern: /group.*by.*type/i, intent: 'analytics_grouping', confidence: 0.8 },
      { pattern: /sort.*by.*size/i, intent: 'analytics_sorting', confidence: 0.8 },
      { pattern: /breakdown.*documents/i, intent: 'analytics_breakdown', confidence: 0.9 },
      { pattern: /analyze.*documents/i, intent: 'analytics_analysis', confidence: 0.7 }
    ];

    for (const { pattern, intent, confidence } of analyticsPatterns) {
      if (pattern.test(normalized)) {
        return { intent, confidence };
      }
    }

    return { intent: 'general', confidence: 0.5 };
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    // Detect intent before sending
    const { intent, confidence } = detectIntent(inputMessage);
    setDetectedIntent(intent);
    setIntentConfidence(confidence);

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setLoadingStage('searching');
    setLoadingProgress(0);
    setErrorMessage(null);

    // Simulate progress stages for better UX
    setTimeout(() => { setLoadingStage('searching'); setLoadingProgress(25); }, 500);
    setTimeout(() => { setLoadingStage('analyzing'); setLoadingProgress(50); }, 2000);
    setTimeout(() => { setLoadingStage('generating'); setLoadingProgress(75); }, 4000);
    try {
      if (readyState === WebSocket.OPEN && conversationId) {
        // Include current document context and model for WS messages as well
        sendMessage(JSON.stringify({
          type: 'message',
          content: inputMessage,
          document_ids: (documentIds && documentIds.length > 0) ? documentIds : null,
          model: selectedModel || undefined,
          context_data: {
            selected_documents_count: documentIds?.length || 0,
            scope: documentIds && documentIds.length > 0 ? 'selected' : 'all_accessible',
            current_model: selectedModel,
            conversation_context: {
              message_count: messages.length,
              last_message_type: messages[messages.length - 1]?.role || 'none'
            }
          }
        }));
        // Keep isLoading true until we receive WS events ('typing'/'message'/'error')
      } else {
        const response = await fetchWithTimeout('/api/v1/chat/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            message: inputMessage,
            conversation_id: conversationId,
            document_ids: (documentIds && documentIds.length > 0) ? documentIds : null,
            model: selectedModel,
            stream: false,
            context_data: {
              selected_documents_count: documentIds?.length || 0,
              scope: documentIds && documentIds.length > 0 ? 'selected' : 'all_accessible',
              current_model: selectedModel,
              conversation_context: {
                message_count: messages.length,
                last_message_type: messages[messages.length - 1]?.role || 'none'
              }
            }
          }),
          timeoutMs: 60000  // 60 seconds for complex queries
        });
        if (response.ok) {
          const data = await response.json();
          if (!conversationId && data.conversation_id) {
            setConversationId(data.conversation_id);
            onNewConversation?.(data.conversation_id);
          }
          setMessages(prev => [...prev, data.response]);
          try {
            setLastScope((data.response?.metadata?.scope as any) || 'all_accessible');
            setLastSources(Array.isArray(data.response?.metadata?.sources) ? data.response.metadata.sources : []);
            // Clear intent after successful response
            setDetectedIntent(null);
            setIntentConfidence(0);
          } catch { }
          setLoadingStage('done');
          setLoadingProgress(100);
          setTimeout(() => setIsLoading(false), 300);
        } else {
          const text = await response.text();
          setErrorMessage(text || 'The assistant failed to respond.');
          setLoadingStage('done');
          setLoadingProgress(100);
          setTimeout(() => setIsLoading(false), 300);
        }
      }
    } catch (error: any) {
      console.error('Failed to send message:', error);
      const errorMsg = error?.message || 'Request timed out or network error.';
      setErrorMessage(`Error: ${errorMsg}. Please try again.`);
      setIsLoading(false);
      // Add error message to chat for visibility
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `⚠️ Sorry, I encountered an error: ${errorMsg}`,
        created_at: new Date().toISOString()
      }]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  };

  // Ensure paste works reliably across browsers and focus states
  const handlePaste = (
    e: React.ClipboardEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const pastedText = e.clipboardData?.getData('text');
    if (pastedText && pastedText.length > 0) {
      e.preventDefault();
      setInputMessage((prev) => (prev ? prev + pastedText : pastedText));
    }
  };

  const getLastAssistantMarkdown = (): string | null => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'assistant') return messages[i].content;
    }
    return null;
  };

  const downloadLastAssistantAsMarkdown = () => {
    const md = getLastAssistantMarkdown();
    if (!md) return;
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-response-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadLastAssistantAsPdf = async () => {
    if (!lastAssistantRef.current) return;
    const element = lastAssistantRef.current;
    const pdf = new jsPDF({ unit: 'pt', format: 'a4' });
    await pdf.html(element, {
      margin: 40,
      autoPaging: 'text',
      html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
      callback: (doc) => doc.save(`chat-response-${Date.now()}.pdf`),
    });
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', borderRadius: 3, position: 'relative' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="h6">
            {documentIds && documentIds.length > 0 ? `Chat with ${documentIds.length} document(s)` : 'AI Assistant'}
          </Typography>
          {/* Intent Indicator */}
          {detectedIntent && detectedIntent !== 'general' && (
            <Chip
              label={`Analyzing: ${detectedIntent.replace('analytics_', '').replace('_', ' ')}`}
              color="primary"
              size="small"
              sx={{
                animation: 'pulse 2s infinite',
                '@keyframes pulse': {
                  '0%': { opacity: 1 },
                  '50%': { opacity: 0.7 },
                  '100%': { opacity: 1 }
                }
              }}
            />
          )}
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>AI Model</InputLabel>
            <Select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              label="AI Model"
              disabled={modelsLoading || availableModels.length === 0}
              startAdornment={<ModelIcon fontSize="small" />}
              onOpen={ensureModelsLoaded}
            >
              {modelsLoading ? (
                <MenuItem disabled>
                  <CircularProgress size={16} sx={{ mr: 1 }} />
                  Loading models...
                </MenuItem>
              ) : availableModels.length === 0 ? (
                <MenuItem disabled> No models available </MenuItem>
              ) : (
                availableModels.map((model) => (
                  <MenuItem key={model.name} value={model.name}>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.875rem' }}>
                        {ollamaService.formatModelName(model)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                        {ollamaService.getModelDescription(model)}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Box>
        {/* Scope indicator + sources */}
        <Box sx={{ mb: 1, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <Chip size="small" color={lastScope === 'selected' ? 'primary' : 'default'} label={lastScope === 'selected' ? 'Using selected documents' : 'Using all accessible documents'} />
          {lastSources && lastSources.length > 0 && (
            <Tooltip title="Sources used for this answer">
              <Chip size="small" icon={<CheckCircleIcon fontSize="small" />} label={`${lastSources.length} source${lastSources.length === 1 ? '' : 's'}`} />
            </Tooltip>
          )}
        </Box>
        {documentIds && documentIds.length > 0 && (
          <Chip icon={<AttachFileIcon />} label={`${documentIds.length} document(s) attached`} size="small" color="primary" />
        )}
        {/* Connection indicator (subtle) + progress */}
        <Box sx={{ mt: 1, display: 'flex', gap: 1, alignItems: 'center' }}>
          {(() => {
            let color: string = 'warning.main'
            let label: string = 'HTTP fallback'
            // If no conversation yet, we haven't opened WS; treat as ready via HTTP
            if (!conversationId) { color = 'info.main'; label = 'Ready' }
            else if (readyState === WebSocket.OPEN) { color = 'success.main'; label = 'Realtime' }
            else if (readyState === WebSocket.CONNECTING) { color = 'info.main'; label = 'Connecting…' }
            else if (readyState === WebSocket.CLOSING || readyState === WebSocket.CLOSED) { color = 'error.main'; label = 'Offline' }
            return (
              <Tooltip title={label}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box aria-label={`connection-${label}`} sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, '@keyframes pulse': { '0%': { transform: 'scale(1)' }, '50%': { transform: 'scale(1.25)' }, '100%': { transform: 'scale(1)' } }, animation: (!conversationId || readyState === WebSocket.OPEN) ? 'none' : 'pulse 1.6s ease-in-out infinite' }} />
                  <Typography variant="caption" sx={{ color, fontWeight: 600, opacity: 0.9 }}>{label}</Typography>
                </Box>
              </Tooltip>
            )
          })()}
          {(isLoading || isTyping) && (
            <LinearProgress sx={{ flex: 1, height: 6, borderRadius: 3, '& .MuiLinearProgress-bar': { background: 'linear-gradient(90deg, #6366F1, #22C55E, #06B6D4, #F59E0B)' } }} />
          )}
        </Box>
      </Box>

      {/* Messages - reduced effective height to make room for progress meter */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1.5, minHeight: 0, pb: 12 }}>
        <List sx={{ py: 0 }}>
          {messages.map((message) => (
            <ListItem key={message.id} sx={{ flexDirection: message.role === 'user' ? 'row-reverse' : 'row', gap: 1, alignItems: 'flex-start', py: 0.5 }}>
              <Avatar sx={{ bgcolor: message.role === 'user' ? 'primary.main' : 'secondary.main' }}>
                {message.role === 'user' ? <PersonIcon /> : <BotIcon />}
              </Avatar>
              <Paper elevation={1} sx={{ p: 1.5, maxWidth: '78%', bgcolor: message.role === 'user' ? 'primary.light' : 'background.paper', color: message.role === 'user' ? 'primary.contrastText' : 'text.primary', border: message.role === 'assistant' ? 1 : 0, borderColor: 'divider', borderRadius: 2 }}>
                <Box sx={{ '& table': { width: '100%', borderCollapse: 'collapse', my: 1 }, '& th, & td': { border: '1px solid', borderColor: 'divider', p: 1, verticalAlign: 'top' }, '& pre': { p: 1.5, overflowX: 'auto', bgcolor: 'background.default', borderRadius: 1, border: 1, borderColor: 'divider' }, '& code': { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' } }} ref={message.role === 'assistant' ? lastAssistantRef : undefined}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                </Box>
                <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
                  {format(new Date(message.created_at), 'MMM dd, yyyy HH:mm')}
                </Typography>
              </Paper>
            </ListItem>
          ))}

          {(isLoading || isTyping) && (
            <ListItem sx={{ display: 'block', px: 0 }}>
              <ChatLoadingAnimation
                stage={loadingStage}
                progress={loadingProgress}
              />
            </ListItem>
          )}
        </List>
        <div ref={messagesEndRef} />
      </Box>

      <Divider />

      {/* Input */}
      <Box sx={{ p: 1.5, display: 'flex', gap: 1, alignItems: 'flex-end' }}>
        <TextField
          fullWidth
          multiline
          maxRows={3}
          size="small"
          placeholder="Type your message..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          onPaste={handlePaste}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              (e.target as HTMLInputElement).blur();
            }
          }}
          disabled={isLoading}
          sx={{ flexGrow: 1 }}
        />
        <Tooltip title="Send message (Enter)">
          <span>
            <IconButton
              color="primary"
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              size="large"
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                '&:hover': { bgcolor: 'primary.dark' },
                '&.Mui-disabled': { bgcolor: 'action.disabledBackground' }
              }}
            >
              <SendIcon />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title="Download last answer as Markdown">
          <IconButton onClick={downloadLastAssistantAsMarkdown} size="medium">
            <DownloadIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Download last answer as PDF">
          <IconButton onClick={downloadLastAssistantAsPdf} size="medium">
            <PdfIcon />
          </IconButton>
        </Tooltip>
      </Box>
      {errorMessage && (
        <Box sx={{ px: 2, pb: 2 }}>
          <Paper variant="outlined" sx={{ p: 1.5, borderColor: 'error.light', bgcolor: 'error.lighter', color: 'error.dark' as any }}>
            <Typography variant="body2">{errorMessage}</Typography>
          </Paper>
        </Box>
      )}

      {/* Colorful Progress Meter - shows on send and during generation */}
      {(isLoading || isTyping) && (
        <Box sx={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          p: 3,
          background: 'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.95) 20%, rgba(255,255,255,1) 100%)',
          borderBottomLeftRadius: 3,
          borderBottomRightRadius: 3,
          pointerEvents: 'none',
          zIndex: 1,
          minHeight: 110,
        }} aria-hidden>
          <Box sx={{ mb: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
              <Typography variant="caption" sx={{ fontWeight: 700, color: 'primary.main', letterSpacing: 0.25 }}>
                {(isLoading && !isTyping) ? 'Sending to model…' : isTyping ? 'Generating response…' : 'Processing…'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {isTyping ? 'Streaming tokens' : 'Preparing context'}
              </Typography>
            </Box>
            <LinearProgress
              variant="indeterminate"
              sx={{
                height: 6,
                borderRadius: 3,
                bgcolor: 'grey.200',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 3,
                  background: 'linear-gradient(90deg, #22C55E 0%, #06B6D4 25%, #8B5CF6 50%, #F59E0B 75%, #EF4444 100%)',
                  backgroundSize: '200% 100%',
                  animation: 'gradient 3s ease infinite, MuiLinearProgress-indeterminate1 2.1s cubic-bezier(0.65, 0.815, 0.735, 0.395) infinite',
                  '@keyframes gradient': {
                    '0%': { backgroundPosition: '0% 50%' },
                    '50%': { backgroundPosition: '100% 50%' },
                    '100%': { backgroundPosition: '0% 50%' }
                  }
                }
              }}
            />
          </Box>
          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Chip
              icon={<CircularProgress size={12} thickness={5} sx={{ color: 'primary.main' }} />}
              label="Model: Active"
              size="small"
              color="primary"
              variant="outlined"
            />
            <Chip
              icon={<CheckCircleIcon sx={{ fontSize: 16 }} />}
              label={`${documentIds?.length || 0} Documents`}
              size="small"
              color="success"
              variant="outlined"
            />
            <Chip
              icon={<SpeedIcon sx={{ fontSize: 16 }} />}
              label={readyState === WebSocket.OPEN ? 'Realtime (WS)' : 'HTTP'}
              size="small"
              color="info"
              variant="outlined"
            />
          </Box>
        </Box>
      )}
    </Paper>
  );
};