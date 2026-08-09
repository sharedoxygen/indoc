/**
 * Service for interacting with Ollama API directly
 */
export interface OllamaModel {
  name: string;
  model: string;
  size: number;
  digest: string;
  details: {
    parameter_size: string;
    quantization_level: string;
    family: string;
  };
  modified_at: string;
}

export interface OllamaModelsResponse {
  models: OllamaModel[];
}

export class OllamaService {
  private baseUrl: string;

  constructor() {
    // Resolved lazily from backend admin settings; fallback to localhost
    this.baseUrl = '';
  }

  private async resolveBaseUrl(): Promise<string> {
    if (this.baseUrl) return this.baseUrl;
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      // Try to use backend-configured base URL (admin endpoint)
      const resp = await fetch('/api/v1/settings/admin', { headers });
      if (resp.ok) {
        const data = await resp.json();
        const url = data?.ollama?.base_url;
        if (typeof url === 'string' && url.length > 0) {
          this.baseUrl = url;
          return this.baseUrl;
        }
      }
    } catch (_) {
      // ignore and fall back to default
    }
    this.baseUrl = 'http://localhost:11434';
    return this.baseUrl;
  }

  private parseSizeFromModelName(name: string): string | undefined {
    // Try to infer sizes like 7b, 13b, 70b, 8x7b etc.
    const m = name.match(/(\d+(?:x\d+)?)(b)/i);
    return m ? m[1] + m[2].toUpperCase() : undefined;
  }

  private parseParameterSize(param: string | undefined): number {
    if (!param) return Number.MAX_SAFE_INTEGER;
    const match = String(param).trim().match(/(\d+(?:\.\d+)?)([kKmMbB])?/);
    if (!match) return Number.MAX_SAFE_INTEGER;
    const value = parseFloat(match[1]);
    const unit = (match[2] || 'B').toUpperCase();
    // Treat parameter_size like tokens count B=Billions, M=Millions, K=Thousands
    const multipliers: Record<string, number> = { K: 1e3, M: 1e6, B: 1e9 };
    const factor = multipliers[unit] ?? 1;
    return value * factor;
  }

  async getAvailableModels(): Promise<OllamaModel[]> {
    try {
      // 1) Prefer backend endpoint (uses configured OLLAMA_BASE_URL and RBAC)
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const backendResp = await fetch('/api/v1/llm/models', { headers });
      if (backendResp.ok) {
        const backendModels: Array<{ name: string; description?: string; size?: string }> = await backendResp.json();
        const mapped: OllamaModel[] = backendModels
          .filter(m => !m.name.includes('embed') && !m.name.includes('embedding'))
          .map(m => ({
            name: m.name,
            model: m.name,
            size: 0,
            digest: '',
            details: {
              parameter_size: this.parseSizeFromModelName(m.name) || undefined as unknown as string,
              quantization_level: '',
              family: m.name.split(':')[0] || 'model'
            },
            modified_at: ''
          }));
        if (mapped.length > 0) {
          return mapped.sort((a, b) =>
            this.parseParameterSize(a.details?.parameter_size) - this.parseParameterSize(b.details?.parameter_size)
          );
        }
      }

      // 2) Fallback: query Ollama directly
      const baseUrl = await this.resolveBaseUrl();
      const response = await fetch(`${baseUrl}/api/tags`);
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data: OllamaModelsResponse = await response.json();
      const chatModels = data.models.filter(model =>
        !model.name.includes('embed') && !model.name.includes('embedding')
      );
      return chatModels.sort((a, b) =>
        this.parseParameterSize(a.details?.parameter_size) - this.parseParameterSize(b.details?.parameter_size)
      );
    } catch (error) {
      console.error('Failed to fetch Ollama models:', error);
      return [];
    }
  }

  async checkConnection(): Promise<boolean> {
    try {
      const baseUrl = await this.resolveBaseUrl();
      const response = await fetch(`${baseUrl}/api/tags`);
      return response.ok;
    } catch (error) {
      console.error('Ollama connection check failed:', error);
      return false;
    }
  }

  formatModelName(model: OllamaModel): string {
    // Convert technical names to user-friendly format
    return model.name
      .replace(/:/g, ' ')
      .replace(/-/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  getModelDescription(model: OllamaModel): string {
    const { parameter_size, family } = model.details;
    const sizeText = parameter_size ? ` (${parameter_size})` : '';
    if (model.name.includes('deepseek')) return `DeepSeek model${sizeText} - Advanced reasoning and coding`;
    if (model.name.includes('gpt-oss')) return `GPT-OSS model${sizeText} - General purpose language model`;
    if (model.name.includes('qwen')) return `Qwen model${sizeText} - Multilingual and vision capabilities`;
    if (model.name.includes('gemma')) return `Google Gemma model${sizeText} - Efficient and capable`;
    if (model.name.includes('kimi')) return `Kimi model${sizeText} - Long context understanding`;
    return `${family} model${sizeText} - Language model`;
  }
}
export const ollamaService = new OllamaService();

