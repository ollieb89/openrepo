/**
 * WebSocket client with connection state management and graceful fallback.
 * Handles optional WebSocket connections when the server is not available.
 */

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'unavailable';

export interface WsClientOptions {
  url: string;
  onMessage?: (data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  maxRetries?: number;
  retryDelay?: number;
  silent?: boolean; // If true, don't log connection errors
}

export class WsClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private retryCount = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private options: Required<WsClientOptions>;

  constructor(options: WsClientOptions) {
    this.options = {
      onMessage: () => {},
      onConnect: () => {},
      onDisconnect: () => {},
      maxRetries: 3,
      retryDelay: 5000,
      silent: true, // Default to silent to avoid spamming console
      ...options,
    };
  }

  getState(): ConnectionState {
    return this.state;
  }

  isConnected(): boolean {
    return this.state === 'connected';
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.CONNECTING || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.state = 'connecting';

    try {
      this.ws = new WebSocket(this.options.url);

      this.ws.onopen = () => {
        this.state = 'connected';
        this.retryCount = 0;
        this.options.onConnect();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.options.onMessage(data);
        } catch {
          this.options.onMessage(event.data);
        }
      };

      this.ws.onclose = () => {
        this.state = 'disconnected';
        this.options.onDisconnect();
        this.handleReconnect();
      };

      this.ws.onerror = () => {
        // Mark as unavailable after max retries
        if (this.retryCount >= this.options.maxRetries) {
          this.state = 'unavailable';
          if (!this.options.silent) {
            console.warn('[WsClient] WebSocket unavailable after max retries');
          }
        }
      };
    } catch (err) {
      this.state = 'unavailable';
      if (!this.options.silent) {
        console.warn('[WsClient] Failed to create WebSocket:', err);
      }
    }
  }

  private handleReconnect(): void {
    if (this.retryCount >= this.options.maxRetries) {
      this.state = 'unavailable';
      if (!this.options.silent) {
        console.info('[WsClient] Max retries reached, WebSocket features disabled');
      }
      return;
    }

    this.retryCount++;
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, this.options.retryDelay);
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      // Prevent auto-reconnect on manual disconnect
      this.retryCount = this.options.maxRetries;
      this.ws.close();
      this.ws = null;
    }

    this.state = 'disconnected';
  }

  send(data: unknown): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
      return true;
    }
    return false;
  }
}

/**
 * Hook-compatible WebSocket client factory.
 * Returns a client that handles optional WebSocket server gracefully.
 */
export function createWsClient(options: WsClientOptions): WsClient {
  return new WsClient(options);
}
