import { QueryClient } from '@tanstack/react-query';
import axios from 'axios';

// Configure axios for API requests
const apiClient = axios.create({
  baseURL: import.meta.env.PROD ? '' : 'http://localhost:3000',
  timeout: 30000,
});

// Default query function for React Query
const defaultQueryFn = async ({ queryKey }) => {
  const [url, ...params] = queryKey;
  const response = await apiClient.get(url, { params: params[0] });
  return response.data;
};

// Create Query Client
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: defaultQueryFn,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// API request helper for mutations
export const apiRequest = async (url, options = {}) => {
  const { method = 'GET', data, params } = options;
  
  const config = {
    method,
    url,
    params,
    timeout: 30000,
  };
  
  if (data) {
    config.data = data;
  }
  
  const response = await apiClient(config);
  return response.data;
};