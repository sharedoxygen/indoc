import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketHook {
  sendMessage: (message: string) => void;
  lastMessage: MessageEvent | null;
  readyState: number;
  connect: () => void;
  disconnect: () => void;
}

export const useWebSocket = (url: string | null): WebSocketHook => {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (!url || wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      // Build WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}${url}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setReadyState(WebSocket.OPEN);
        reconnectAttemptsRef.current = 0;

        // Send authentication token
        const token = localStorage.getItem('token');
        if (token) {
          ws.send(JSON.stringify({ token }));
        }
      };

      ws.onmessage = (event) => {
        setLastMessage(event);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setReadyState(WebSocket.CLOSED);
        wsRef.current = null;

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < 5) {
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, timeout);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setReadyState(WebSocket.CLOSED);
    }
  }, [url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setReadyState(WebSocket.CLOSED);
    reconnectAttemptsRef.current = 0;
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    if (url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, connect, disconnect]);

  return {
    sendMessage,
    lastMessage,
    readyState,
    connect,
    disconnect
  };
};