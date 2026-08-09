import { useEffect, useRef } from 'react';

/**
 * Hook for optimizing API queries with debouncing and request deduplication
 */
export const useOptimizedQuery = <T>(
  queryFn: () => Promise<T>,
  deps: any[],
  debounceMs: number = 300
) => {
  const timeoutRef = useRef<NodeJS.Timeout>();
  const lastRequestRef = useRef<string>();
  const resultRef = useRef<T>();

  useEffect(() => {
    // Create request signature for deduplication
    const requestSignature = JSON.stringify(deps);
    
    // Skip if same request is already pending/completed
    if (lastRequestRef.current === requestSignature) {
      return;
    }

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Debounce the request
    timeoutRef.current = setTimeout(async () => {
      try {
        lastRequestRef.current = requestSignature;
        const result = await queryFn();
        resultRef.current = result;
      } catch (error) {
        console.error('Optimized query error:', error);
      }
    }, debounceMs);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, deps);

  return resultRef.current;
};

/**
 * Batch multiple API requests to reduce network overhead
 */
export const batchRequests = async <T>(
  requests: (() => Promise<T>)[],
  batchSize: number = 5
): Promise<T[]> => {
  const results: T[] = [];
  
  for (let i = 0; i < requests.length; i += batchSize) {
    const batch = requests.slice(i, i + batchSize);
    const batchResults = await Promise.allSettled(batch.map(req => req()));
    
    batchResults.forEach(result => {
      if (result.status === 'fulfilled') {
        results.push(result.value);
      }
    });
  }
  
  return results;
};
