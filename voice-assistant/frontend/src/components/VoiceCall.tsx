import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Button,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Chip,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Mic,
  MicOff,
  Phone,
  PhoneDisabled,
  VolumeUp,
  VolumeOff,
} from '@mui/icons-material';

import { VoiceCallProps, WebSocketMessage, ConversationMessage } from '../types';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAudio } from '../hooks/useAudio';

const VoiceCall: React.FC<VoiceCallProps> = ({ onCallStart, onCallEnd, onError }) => {
  // State management
  const [isCallActive, setIsCallActive] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [isAIResponding, setIsAIResponding] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');

  // Custom hooks
  const { socket, isConnected, sendMessage, lastMessage, error: wsError } = useWebSocket();
  const { isRecording, isPlaying, startRecording, stopRecording, playAudio, error: audioError } = useAudio();

  // Refs
  const conversationEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'call_started':
        setSessionId(lastMessage.session_id || null);
        setIsCallActive(true);
        setConnectionStatus('connected');
        onCallStart?.();
        
        // Add welcome message to conversation
        const welcomeMessage: ConversationMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: lastMessage.message || 'Hello! How can I help you today?',
          timestamp: new Date().toISOString(),
        };
        setConversation([welcomeMessage]);
        
        // Play welcome message
        if (lastMessage.audio_data) {
          playAudio(lastMessage.audio_data);
        }
        break;

      case 'ai_response':
        setIsAIResponding(false);
        
        // Add AI response to conversation
        if (lastMessage.transcript) {
          const aiMessage: ConversationMessage = {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: lastMessage.transcript,
            timestamp: new Date().toISOString(),
          };
          setConversation(prev => [...prev, aiMessage]);
        }
        
        // Play AI response audio
        if (lastMessage.audio_data) {
          playAudio(lastMessage.audio_data);
        }
        break;

      case 'call_ended':
        setIsCallActive(false);
        setSessionId(null);
        setConnectionStatus('disconnected');
        onCallEnd?.();
        
        // Add goodbye message
        const goodbyeMessage: ConversationMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: lastMessage.message || 'Thank you for calling. Have a great day!',
          timestamp: new Date().toISOString(),
        };
        setConversation(prev => [...prev, goodbyeMessage]);
        break;

      case 'error':
        const errorMsg = lastMessage.message || 'An error occurred during the call';
        onError?.(errorMsg);
        setIsCallActive(false);
        setConnectionStatus('disconnected');
        break;
    }
  }, [lastMessage, onCallStart, onCallEnd, onError, playAudio]);

  // Handle errors
  useEffect(() => {
    if (wsError || audioError) {
      const error = wsError || audioError;
      onError?.(error);
    }
  }, [wsError, audioError, onError]);

  // Start call
  const handleStartCall = async () => {
    try {
      setConnectionStatus('connecting');
      
      // Start recording
      await startRecording();
      
      // Send start call message
      const message: WebSocketMessage = {
        type: 'start_call',
      };
      sendMessage(message);
      
    } catch (error) {
      console.error('Failed to start call:', error);
      setConnectionStatus('disconnected');
      onError?.('Failed to start call. Please check your microphone permissions.');
    }
  };

  // End call
  const handleEndCall = () => {
    // Stop recording
    stopRecording();
    
    // Send end call message
    const message: WebSocketMessage = {
      type: 'end_call',
    };
    sendMessage(message);
    
    setIsCallActive(false);
    setConnectionStatus('disconnected');
  };

  // Toggle recording
  const handleToggleRecording = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      try {
        await startRecording();
      } catch (error) {
        onError?.('Failed to start recording. Please check your microphone permissions.');
      }
    }
  };

  // Send audio chunk (this would be called by the audio hook)
  const sendAudioChunk = (audioData: string) => {
    if (!isCallActive || !sessionId) return;
    
    const message: WebSocketMessage = {
      type: 'audio_chunk',
      data: audioData,
    };
    sendMessage(message);
    setIsAIResponding(true);
  };

  // Get connection status color
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'success';
      case 'connecting': return 'warning';
      default: return 'error';
    }
  };

  // Get connection status text
  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      default: return 'Disconnected';
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 2 }}>
      {/* Header */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ textAlign: 'center' }}>
          <Typography variant="h4" component="h1" gutterBottom>
            AI Voice Assistant
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Talk to our AI customer service agent
          </Typography>
          
          {/* Connection Status */}
          <Box sx={{ mt: 2, mb: 2 }}>
            <Chip 
              label={getStatusText()} 
              color={getStatusColor() as any}
              variant="outlined"
              sx={{ mr: 2 }}
            />
            {sessionId && (
              <Chip 
                label={`Session: ${sessionId.slice(0, 8)}...`} 
                variant="outlined"
                size="small"
              />
            )}
          </Box>

          {/* Call Controls */}
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
            {!isCallActive ? (
              <Button
                variant="contained"
                size="large"
                startIcon={<Phone />}
                onClick={handleStartCall}
                disabled={connectionStatus === 'connecting'}
                sx={{ minWidth: 150 }}
              >
                {connectionStatus === 'connecting' ? (
                  <>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    Connecting...
                  </>
                ) : (
                  'Start Call'
                )}
              </Button>
            ) : (
              <>
                <IconButton
                  color={isRecording ? 'secondary' : 'default'}
                  onClick={handleToggleRecording}
                  size="large"
                  sx={{ 
                    bgcolor: isRecording ? 'secondary.light' : 'grey.200',
                    '&:hover': {
                      bgcolor: isRecording ? 'secondary.main' : 'grey.300',
                    }
                  }}
                >
                  {isRecording ? <Mic /> : <MicOff />}
                </IconButton>
                
                <Button
                  variant="contained"
                  color="error"
                  size="large"
                  startIcon={<PhoneDisabled />}
                  onClick={handleEndCall}
                  sx={{ minWidth: 150 }}
                >
                  End Call
                </Button>
                
                <IconButton
                  color={isPlaying ? 'primary' : 'default'}
                  size="large"
                  disabled
                  sx={{ bgcolor: 'grey.200' }}
                >
                  {isPlaying ? <VolumeUp /> : <VolumeOff />}
                </IconButton>
              </>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Current Status */}
      {isCallActive && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {isRecording && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      bgcolor: 'error.main',
                      animation: 'pulse 1s infinite',
                      '@keyframes pulse': {
                        '0%': { opacity: 1 },
                        '50%': { opacity: 0.5 },
                        '100%': { opacity: 1 },
                      },
                    }}
                  />
                  <Typography variant="body2" color="error">
                    Recording...
                  </Typography>
                </Box>
              )}
              
              {isAIResponding && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={16} />
                  <Typography variant="body2" color="primary">
                    AI is responding...
                  </Typography>
                </Box>
              )}
              
              {isPlaying && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <VolumeUp color="primary" />
                  <Typography variant="body2" color="primary">
                    Playing response...
                  </Typography>
                </Box>
              )}
            </Box>
            
            {currentTranscript && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Current transcript:
                </Typography>
                <Typography variant="body1" sx={{ fontStyle: 'italic' }}>
                  "{currentTranscript}"
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Conversation History */}
      {conversation.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Conversation
            </Typography>
            <Paper 
              sx={{ 
                maxHeight: 400, 
                overflow: 'auto', 
                bgcolor: 'grey.50',
                p: 1
              }}
            >
              <List dense>
                {conversation.map((message, index) => (
                  <React.Fragment key={message.id}>
                    <ListItem
                      sx={{
                        flexDirection: 'column',
                        alignItems: message.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <Box
                        sx={{
                          maxWidth: '80%',
                          bgcolor: message.role === 'user' ? 'primary.light' : 'grey.200',
                          color: message.role === 'user' ? 'white' : 'text.primary',
                          borderRadius: 2,
                          p: 2,
                          mb: 1,
                        }}
                      >
                        <Typography variant="body1">
                          {message.content}
                        </Typography>
                        {message.confidence && (
                          <Typography variant="caption" sx={{ opacity: 0.7 }}>
                            Confidence: {(message.confidence * 100).toFixed(0)}%
                          </Typography>
                        )}
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {message.role === 'user' ? 'You' : 'AI Assistant'} • {' '}
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </Typography>
                    </ListItem>
                    {index < conversation.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
              <div ref={conversationEndRef} />
            </Paper>
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {(wsError || audioError) && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {wsError || audioError}
        </Alert>
      )}
    </Box>
  );
};

export default VoiceCall;
