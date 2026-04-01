import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.MINDFLOW_API_URL || 'http://localhost:8000';
const API_KEY = process.env.MINDFLOW_API_KEY || '';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        ...(API_KEY && { 'Authorization': `Bearer ${API_KEY}` }),
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.message);
        return Promise.reject(error);
      }
    );
  }

  async sendMessage(content: string, sessionId?: string) {
    const response = await this.client.post('/v1/agent/chat/stream', {
      message: content,
      session_id: sessionId,
      stream: true,
    });
    return response.data;
  }

  async getAgentStatus(agentId: string) {
    const response = await this.client.get(`/v1/agents/${agentId}/status`);
    return response.data;
  }

  async listAgents() {
    const response = await this.client.get('/v1/agent/list');
    return response.data;
  }

  async getSessions() {
    const response = await this.client.get('/v1/chat/sessions');
    return response.data;
  }

  async createSession() {
    const response = await this.client.post('/v1/chat/sessions', {
      title: 'CLI Session',
    });
    return response.data;
  }
}

export const apiService = new ApiService();
