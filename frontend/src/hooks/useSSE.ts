import { useState, useCallback } from 'react';

export function useSSE<T = any>() {
  const [data, setData] = useState<T[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = useCallback(async (url: string, payload: any) => {
    setIsStreaming(true);
    setError(null);
    setData([]);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('astroq_token')}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`SSE request failed: ${response.statusText}`);
      }
      
      if (!response.body) {
         throw new Error('ReadableStream not supported');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6);
            if (dataStr.trim() !== '') {
              try {
                const parsed = JSON.parse(dataStr);
                setData(prev => [...prev, parsed]);
              } catch (e) {
                console.error('Failed to parse SSE data chunk:', dataStr);
              }
            }
          }
        });
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { data, error, isStreaming, startStream };
}
