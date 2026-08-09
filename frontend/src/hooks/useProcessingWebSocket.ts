import { useEffect, useRef, useState } from 'react';

export interface ProcessingUpdate {
  type: string;
  documentId: string;
  step: string;
  status: string;
  progress?: number;
  message?: string;
  details?: string[];
  errorMessage?: string;
  timestamp: string;
}

export const useProcessingWebSocket = (onUpdate: (update: ProcessingUpdate) => void) => {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    let isActive = true;
    
    const connect = () => {
      const token = localStorage.getItem('token');
      if (!token) {
        console.warn('No token available for WebSocket connection');
        return;
      }
      
      if (!isActive) {
        console.log('Component unmounting, skipping WebSocket connection');
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/ws/processing?token=${token}`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('✅ Processing WebSocket connected');
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('📨 Processing update:', data);
            onUpdate(data);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log('🔌 Processing WebSocket disconnected');
          setIsConnected(false);
          wsRef.current = null;
          
          // Only reconnect if component is still mounted
          if (isActive) {
            reconnectTimeoutRef.current = setTimeout(() => {
              if (isActive) {
                console.log('🔄 Reconnecting WebSocket...');
                connect();
              }
            }, 3000);
          }
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
      }
    };

    connect();

    return () => {
      isActive = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      wsRef.current = null;
    };
  }, [onUpdate]);

  return { isConnected };
};

