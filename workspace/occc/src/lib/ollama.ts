import { Ollama } from 'ollama';

const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://localhost:11434';
const DEFAULT_MODEL = 'phi3:mini';

const ollama = new Ollama({ host: OLLAMA_HOST });

/**
 * Check if the local Ollama service is available.
 */
export async function isOllamaAvailable(): Promise<boolean> {
  try {
    // We use list() as a health check
    await ollama.list();
    return true;
  } catch (error) {
    console.warn('[Ollama] Local Ollama service not available:', error);
    return false;
  }
}

/**
 * Generate a completion from a prompt using Phi-3.
 */
export async function generateCompletion(
  prompt: string,
  options: { temperature?: number } = {}
): Promise<string> {
  if (!(await isOllamaAvailable())) {
    throw new Error('Ollama service is not available');
  }

  try {
    const response = await ollama.generate({
      model: DEFAULT_MODEL,
      prompt,
      options: {
        temperature: options.temperature ?? 0,
      },
      stream: false,
    });

    return response.response;
  } catch (error) {
    console.error('[Ollama] Error generating completion:', error);
    throw error;
  }
}

/**
 * Generate a streaming completion from a prompt using Phi-3.
 * Returns an AsyncGenerator that yields tokens.
 */
export async function* streamCompletion(
  prompt: string,
  options: { temperature?: number; model?: string } = {}
): AsyncGenerator<string> {
  if (!(await isOllamaAvailable())) {
    throw new Error('Ollama service is not available');
  }

  try {
    const stream = await ollama.generate({
      model: options.model ?? DEFAULT_MODEL,
      prompt,
      options: {
        temperature: options.temperature ?? 0,
      },
      stream: true,
    });

    for await (const part of stream) {
      yield part.response;
    }
  } catch (error) {
    console.error('[Ollama] Error in streaming completion:', error);
    throw error;
  }
}

/**
 * Generate a vector embedding for a string using a local model.
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  if (!(await isOllamaAvailable())) {
    throw new Error('Ollama service is not available');
  }

  try {
    const response = await ollama.embeddings({
      model: 'mxbai-embed-large', // Recommended for high quality local embeddings
      prompt: text,
    });

    return response.embedding;
  } catch (error) {
    console.error('[Ollama] Error generating embedding:', error);
    throw error;
  }
}

export { ollama };
