/**
 * TypeScript type definitions for the Voice Assistant application
 */

// WebSocket message types
export interface WebSocketMessage {
  type: 'audio_chunk' | 'start_call' | 'end_call' | 'ai_response' | 'call_started' | 'call_ended' | 'error';
  data?: any;
  audio_data?: string;
  transcript?: string;
  confidence?: number;
  session_id?: string;
  message?: string;
}

// Voice call related types
export interface VoiceCallState {
  isConnected: boolean;
  isRecording: boolean;
  isPlaying: boolean;
  sessionId: string | null;
  error: string | null;
}

export interface AudioSettings {
  sampleRate: number;
  channels: number;
  bitDepth: number;
  echoCancellation: boolean;
  noiseSuppression: boolean;
}

// Analytics types
export interface CallAnalytics {
  overview: {
    total_calls: number;
    calls_today: number;
    calls_this_week: number;
    calls_this_month: number;
    average_duration: number;
    average_interactions: number;
    success_rate: number;
    peak_hour: number;
  };
  trends: {
    daily_calls: Array<{ date: string; calls: number }>;
    hourly_distribution: Record<string, number>;
    duration_trend: Array<{ date: string; average_duration: number }>;
    interaction_trend: Array<{ date: string; average_interactions: number }>;
  };
  performance: {
    average_response_time: number;
    error_rate: number;
    user_satisfaction: number;
  };
}

export interface CommonQuestion {
  pattern: string;
  count: number;
  percentage: number;
  examples: string[];
}

export interface CommonQuestionsData {
  common_patterns: CommonQuestion[];
  intent_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  total_questions: number;
}

// User interface types
export interface User {
  id: string;
  name: string;
  email: string;
  role: 'user' | 'admin';
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  confidence?: number;
}

export interface ConversationSession {
  id: string;
  userId?: string;
  startTime: string;
  endTime?: string;
  duration: number;
  totalInteractions: number;
  status: 'active' | 'ended' | 'error';
  messages: ConversationMessage[];
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface HealthCheckResponse {
  status: string;
  services: {
    deepgram: boolean;
    elevenlabs: boolean;
    groq: boolean;
    database: boolean;
  };
}

// Component prop types
export interface VoiceCallProps {
  onCallStart?: () => void;
  onCallEnd?: () => void;
  onError?: (error: string) => void;
}

export interface AdminDashboardProps {
  user: User;
}

// Chart data types
export interface ChartDataPoint {
  x: string | number;
  y: number;
  label?: string;
}

export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
  }>;
}

// Error types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

// Configuration types
export interface AppConfig {
  apiUrl: string;
  wsUrl: string;
  audioSettings: AudioSettings;
  features: {
    voiceCall: boolean;
    adminDashboard: boolean;
    analytics: boolean;
  };
}

// Hook return types
export interface UseWebSocketReturn {
  socket: WebSocket | null;
  isConnected: boolean;
  sendMessage: (message: WebSocketMessage) => void;
  lastMessage: WebSocketMessage | null;
  error: string | null;
}

export interface UseAudioReturn {
  isRecording: boolean;
  isPlaying: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  playAudio: (audioData: string) => Promise<void>;
  error: string | null;
}

export interface UseAnalyticsReturn {
  analytics: CallAnalytics | null;
  commonQuestions: CommonQuestionsData | null;
  loading: boolean;
  error: string | null;
  refreshAnalytics: () => Promise<void>;
}

// Theme types
export interface ThemeColors {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  background: string;
  surface: string;
  text: {
    primary: string;
    secondary: string;
  };
}

export interface AppTheme {
  colors: ThemeColors;
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
}
