/**
 * WebSocket Context
 *
 * Provides real-time communication with the backend via WebSocket.
 * Supports both API proxy mode (empty API_HOST) and direct mode (full URL).
 *
 * In API proxy mode, WebSocket connections are made relative to the current
 * page URL, allowing the Next.js proxy to forward /ws to the backend.
 */

'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

import { API_HOST } from '@/lib/api';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected';

type WebSocketMessage = { type?: string; [key: string]: unknown };
type MessageHandler = (message: WebSocketMessage) => void;

interface WebSocketContextValue {
  status: WebSocketStatus;
  subscribe: (type: string, handler: MessageHandler) => () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | undefined>(undefined);

function getAuthToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/auth_token=([^;]+)/);
  return match ? match[1] : null;
}

/**
 * Build the WebSocket URL based on API configuration.
 *
 * API Proxy Mode (API_HOST empty): Uses window.location to connect via /ws
 * Direct Mode (API_HOST set): Connects directly to backend WebSocket endpoint
 */
function buildWebSocketUrl(token: string) {
  let host: string;
  let protocol: string;

  if (API_HOST) {
    // Direct mode: Connect to explicit backend URL
    const base = new URL(API_HOST);
    protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    host = base.host;
  } else if (typeof window !== 'undefined') {
    // API Proxy mode: Connect relative to current page (proxied by Next.js)
    protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    host = window.location.host;
  } else {
    // Fallback for SSR (shouldn't happen for WebSocket)
    return '';
  }

  return `${protocol}//${host}/ws?token=${encodeURIComponent(token)}`;
}

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const socketRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef(new Map<string, Set<MessageHandler>>());
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [token, setToken] = useState<string | null>(null);

  const notify = useCallback((message: WebSocketMessage) => {
    const handlers = listenersRef.current.get(message.type || '');
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message);
        } catch (err) {
          console.error('WebSocket handler error', err);
        }
      });
    }
  }, []);

  const connect = useCallback(
    (authToken: string) => {
      setStatus('connecting');
      const url = buildWebSocketUrl(authToken);
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => setStatus('connected');
    ws.onclose = () => {
      setStatus('disconnected');
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      reconnectTimeout.current = setTimeout(() => {
        if (token) {
          connect(token);
        }
      }, 3000);
    };
    ws.onerror = () => {
      ws.close();
    };
    ws.onmessage = event => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        notify(message);
      } catch {
        // ignore malformed messages
      }
    };
  },
    [notify, token]
  );

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const syncToken = () => setToken(getAuthToken());
    syncToken();
    const interval = setInterval(syncToken, 5000);

    return () => {
      clearInterval(interval);
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      socketRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setStatus('disconnected');
      socketRef.current?.close();
      return undefined;
    }

    connect(token);

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      socketRef.current?.close();
    };
  }, [connect, token]);

  const subscribe = useCallback((type: string, handler: MessageHandler) => {
    const listeners = listenersRef.current.get(type) ?? new Set<MessageHandler>();
    listeners.add(handler);
    listenersRef.current.set(type, listeners);

    return () => {
      const existing = listenersRef.current.get(type);
      if (!existing) return;
      existing.delete(handler);
      if (existing.size === 0) {
        listenersRef.current.delete(type);
      }
    };
  }, []);

  const value: WebSocketContextValue = {
    status,
    subscribe,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocketContext() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return ctx;
}
