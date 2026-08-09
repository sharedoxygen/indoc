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
  Card,
  CardContent,
  CardActions,
  Button,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Fade,
  Grow,
  Collapse,
  Alert,
  Grid,
  Stack,
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
  ExpandMore as ExpandMoreIcon,
  Visibility as VisibilityIcon,
  Link as LinkIcon,
  Security as SecurityIcon,
  Warning as WarningIcon,
  TrendingUp as InsightIcon,
  BookmarkBorder as BookmarkIcon,
  Share as ShareIcon,
} from '@mui/icons-material';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatDistanceToNow } from 'date-fns';
import { ollamaService, OllamaModel } from '../services/ollamaService';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  metadata?: {
    context_used?: boolean;
    phi_redacted?: boolean;
    redactions_applied?: number;
    compliance_scan?: {
      phi_found: boolean;
      detections_count: number;
    };
    citations?: Citation[];
    document_sources?: DocumentSource[];
  };
}

interface Citation {
  document_id: string;
  filename: string;
  page?: number;
  section?: string;
  confidence: number;
  snippet: string;
}

interface DocumentSource {
  id: string;
  filename: string;
  file_type: string;
  relevance_score: number;
  status: 'active' | 'referenced' | 'unused';
}

interface ComplianceStatus {
  mode: string;
  phi_detected: boolean;
  redactions_applied: number;
  last_scan: string;
}

interface EnhancedDocumentChatProps {
  documentIds?: string[];
  conversationId?: string;
  onNewConversation?: (conversationId: string) => void;
  complianceMode?: string;
  showDocumentPreview?: boolean;
  showCitations?: boolean;
  showInsights?: boolean;
}

export const EnhancedDocumentChat: React.FC<EnhancedDocumentChatProps> = ({
  documentIds = [],
  conversationId,
  onNewConversation,
  complianceMode = 'standard',
  showDocumentPreview = true,
  showCitations = true,
  showInsights = true,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [availableModels, setAvailableModels] = useState<OllamaModel[]>([]);
  const [documentSources, setDocumentSources] = useState<DocumentSource[]>([]);
  const [complianceStatus, setComplianceStatus] = useState<ComplianceStatus | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [conversationInsights, setConversationInsights] = useState<string[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // WebSocket connection for real-time updates
  const { socket, isConnected } = useWebSocket(conversationId ? `/ws/chat/${conversationId}` : null);

  useEffect(() => {
    loadAvailableModels();
    if (documentIds.length > 0) {
      loadDocumentSources();
      generateSuggestedQuestions();
    }
  }, [documentIds]);

  useEffect(() => {
    if (complianceMode !== 'standard') {
      loadComplianceStatus();
    }
  }, [complianceMode]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadAvailableModels = async () => {
    try {
      const models = await ollamaService.getModels();
      setAvailableModels(models);
      if (models.length > 0 && !selectedModel) {
        setSelectedModel(models[0].name);
      }
    } catch (error) {
      console.error('Error loading models:', error);
    }
  };

  const loadDocumentSources = async () => {
    try {
      // Mock document sources - in real app, fetch from API
      const sources: DocumentSource[] = documentIds.map((id, index) => ({
        id,
        filename: `Document_${index + 1}.pdf`,
        file_type: 'pdf',
        relevance_score: 0.9 - index * 0.1,
        status: index === 0 ? 'active' : 'unused',
      }));
      setDocumentSources(sources);
    } catch (error) {
      console.error('Error loading document sources:', error);
    }
  };

  const loadComplianceStatus = async () => {
    try {
      // Mock compliance status - in real app, fetch from API
      setComplianceStatus({
        mode: complianceMode,
        phi_detected: false,
        redactions_applied: 0,
        last_scan: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Error loading compliance status:', error);
    }
  };

  const generateSuggestedQuestions = async () => {
    // Mock suggested questions based on documents
    const questions = [
      "What are the key findings in these documents?",
      "Compare the main conclusions across all documents",
      "What contradictions or conflicts exist between documents?",
      "Summarize the most important information",
      "What insights can you draw from this document set?",
    ];
    setSuggestedQuestions(questions);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Mock API call - replace with actual API
      setTimeout(() => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `I've analyzed your question "${userMessage.content}" across ${documentIds.length} documents. Here's what I found:\n\n**Key Insights:**\n- Finding 1 from Document A\n- Finding 2 from Document B\n- Cross-reference found between Documents A and C\n\n**Sources:** References found in 3 documents with high confidence.`,
          created_at: new Date().toISOString(),
          metadata: {
            context_used: true,
            citations: [
              {
                document_id: documentIds[0] || '1',
                filename: 'Document_1.pdf',
                page: 5,
                confidence: 0.95,
                snippet: 'This is a relevant excerpt from the document...',
              },
            ],
            document_sources: documentSources.slice(0, 2),
          },
        };

        setMessages(prev => [...prev, assistantMessage]);
        setIsLoading(false);

        // Update document source statuses
        setDocumentSources(prev =>
          prev.map(doc => ({
            ...doc,
            status: Math.random() > 0.5 ? 'referenced' : 'unused',
          }))
        );
      }, 2000);
    } catch (error) {
      console.error('Error sending message:', error);
      setIsLoading(false);
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    setInputMessage(question);
  };

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setShowPreview(true);
  };

  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    const hasCompliance = message.metadata?.compliance_scan?.phi_found;

    return (
      <Grow in timeout={500} key={message.id}>
        <ListItem
          sx={{
            flexDirection: 'column',
            alignItems: isUser ? 'flex-end' : 'flex-start',
            px: 2,
            py: 1,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              flexDirection: isUser ? 'row-reverse' : 'row',
              gap: 1,
              maxWidth: '85%',
            }}
          >
            <Avatar sx={{ bgcolor: isUser ? 'primary.main' : 'secondary.main' }}>
              {isUser ? <PersonIcon /> : <BotIcon />}
            </Avatar>

            <Box
              sx={{
                flex: 1,
                minWidth: 0,
              }}
            >
              <Paper
                sx={{
                  p: 2,
                  bgcolor: isUser ? 'primary.50' : 'grey.50',
                  border: hasCompliance ? '2px solid orange' : 'none',
                }}
              >
                {hasCompliance && (
                  <Alert severity="warning" sx={{ mb: 1, py: 0 }}>
                    <Typography variant="caption">
                      PHI detected - {message.metadata?.redactions_applied} redactions applied
                    </Typography>
                  </Alert>
                )}

                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>

                {message.metadata?.citations && showCitations && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Sources:
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {message.metadata.citations.map((citation, index) => (
                        <Chip
                          key={index}
                          label={`${citation.filename} (p.${citation.page})`}
                          size="small"
                          icon={<LinkIcon />}
                          clickable
                          onClick={() => handleCitationClick(citation)}
                          sx={{ mb: 0.5 }}
                        />
                      ))}
                    </Stack>
                  </Box>
                )}
              </Paper>

              <Typography
                variant="caption"
                sx={{
                  display: 'block',
                  mt: 0.5,
                  textAlign: isUser ? 'right' : 'left',
                  color: 'text.secondary',
                }}
              >
                {formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}
                {message.metadata?.context_used && ' • Used document context'}
              </Typography>
            </Box>
          </Box>
        </ListItem>
      </Grow>
    );
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header with Document Context */}
      <Paper sx={{ p: 2, mb: 1 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs>
            <Typography variant="h6">
              Document Conversation
              {documentIds.length > 0 && (
                <Chip
                  label={`${documentIds.length} document${documentIds.length !== 1 ? 's' : ''}`}
                  size="small"
                  sx={{ ml: 1 }}
                />
              )}
            </Typography>
          </Grid>
          
          {complianceMode !== 'standard' && (
            <Grid item>
              <Chip
                icon={<SecurityIcon />}
                label={complianceMode.toUpperCase()}
                color="warning"
                variant="outlined"
              />
            </Grid>
          )}
        </Grid>

        {/* Document Sources */}
        {documentSources.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Document Sources:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {documentSources.map((doc) => (
                <Tooltip key={doc.id} title={`Relevance: ${(doc.relevance_score * 100).toFixed(0)}%`}>
                  <Chip
                    label={doc.filename}
                    size="small"
                    color={
                      doc.status === 'active'
                        ? 'primary'
                        : doc.status === 'referenced'
                        ? 'success'
                        : 'default'
                    }
                    icon={
                      doc.status === 'active' ? (
                        <VisibilityIcon />
                      ) : doc.status === 'referenced' ? (
                        <CheckCircleIcon />
                      ) : undefined
                    }
                  />
                </Tooltip>
              ))}
            </Stack>
          </Box>
        )}
      </Paper>

      {/* Messages Area */}
      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {/* Main Chat */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Paper
            ref={chatContainerRef}
            sx={{
              flex: 1,
              overflow: 'auto',
              mb: 1,
              bgcolor: 'grey.50',
            }}
          >
            <List sx={{ p: 0 }}>
              {messages.length === 0 && (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary" gutterBottom>
                    👋 Ready to chat with your documents!
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ask questions, request summaries, or explore insights across your document library.
                  </Typography>
                </Box>
              )}

              {messages.map(renderMessage)}

              {isLoading && (
                <ListItem sx={{ justifyContent: 'center', py: 2 }}>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    AI is thinking...
                  </Typography>
                </ListItem>
              )}

              <div ref={messagesEndRef} />
            </List>
          </Paper>

          {/* Suggested Questions */}
          {messages.length === 0 && suggestedQuestions.length > 0 && (
            <Collapse in>
              <Paper sx={{ p: 2, mb: 1 }}>
                <Typography variant="subtitle2" gutterBottom>
                  💡 Try asking:
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {suggestedQuestions.slice(0, 3).map((question, index) => (
                    <Chip
                      key={index}
                      label={question}
                      variant="outlined"
                      size="small"
                      clickable
                      onClick={() => handleSuggestedQuestion(question)}
                      sx={{ mb: 0.5 }}
                    />
                  ))}
                </Stack>
              </Paper>
            </Collapse>
          )}

          {/* Input Area */}
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
              <TextField
                fullWidth
                multiline
                maxRows={4}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask about your documents..."
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={isLoading}
              />
              <IconButton
                color="primary"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                sx={{ p: 1.5 }}
              >
                <SendIcon />
              </IconButton>
            </Box>

            {/* Model Selection */}
            <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>AI Model</InputLabel>
                <Select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  label="AI Model"
                >
                  {availableModels.map((model) => (
                    <MenuItem key={model.name} value={model.name}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <ModelIcon fontSize="small" />
                        {model.name}
                        <Chip label={model.size} size="small" />
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Box sx={{ display: 'flex', gap: 1 }}>
                <Tooltip title="Export conversation">
                  <IconButton size="small">
                    <DownloadIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Share conversation">
                  <IconButton size="small">
                    <ShareIcon />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
          </Paper>
        </Box>

        {/* Document Preview Panel */}
        {showPreview && selectedCitation && (
          <Fade in>
            <Paper sx={{ width: 400, ml: 1, p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Document Preview
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Typography variant="subtitle2">
                {selectedCitation.filename}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Page {selectedCitation.page} • Confidence: {(selectedCitation.confidence * 100).toFixed(0)}%
              </Typography>

              <Paper sx={{ p: 2, bgcolor: 'grey.50', mt: 2 }}>
                <Typography variant="body2">
                  "{selectedCitation.snippet}"
                </Typography>
              </Paper>

              <Button
                variant="outlined"
                startIcon={<VisibilityIcon />}
                sx={{ mt: 2 }}
                onClick={() => setShowPreview(false)}
              >
                View Full Document
              </Button>
            </Paper>
          </Fade>
        )}
      </Box>
    </Box>
  );
};

export default EnhancedDocumentChat;
