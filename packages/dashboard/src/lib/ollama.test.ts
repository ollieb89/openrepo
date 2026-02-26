import { describe, it, expect, mock, spyOn, beforeEach } from 'bun:test';
import { generateCompletion, generateEmbedding, isOllamaAvailable, ollama } from './ollama';

describe('Ollama Bridge', () => {
  beforeEach(() => {
    mock.restore();
  });

  it('isOllamaAvailable returns true when list succeeds', async () => {
    spyOn(ollama, 'list').mockImplementation(() => Promise.resolve({ models: [] }) as any);
    const available = await isOllamaAvailable();
    expect(available).toBe(true);
  });

  it('isOllamaAvailable returns false when list fails', async () => {
    spyOn(ollama, 'list').mockImplementation(() => Promise.reject(new Error('Connection failed')));
    const available = await isOllamaAvailable();
    expect(available).toBe(false);
  });

  it('generateCompletion sends correct parameters to ollama', async () => {
    spyOn(ollama, 'list').mockImplementation(() => Promise.resolve({ models: [] }) as any);
    const generateSpy = spyOn(ollama, 'generate').mockImplementation(() => Promise.resolve({
      response: 'test response',
    }) as any);

    const response = await generateCompletion('test prompt', { temperature: 0.5 });
    
    expect(response).toBe('test response');
    expect(generateSpy).toHaveBeenCalledWith({
      model: 'phi3:mini',
      prompt: 'test prompt',
      options: {
        temperature: 0.5,
      },
      stream: false,
    });
  });

  it('generateCompletion throws if ollama is not available', async () => {
    spyOn(ollama, 'list').mockImplementation(() => Promise.reject(new Error('Connection failed')));
    expect(generateCompletion('test prompt')).rejects.toThrow('Ollama service is not available');
  });

  it('generateEmbedding sends correct parameters to ollama', async () => {
    spyOn(ollama, 'list').mockImplementation(() => Promise.resolve({ models: [] }) as any);
    const embeddingSpy = spyOn(ollama, 'embeddings').mockImplementation(() => Promise.resolve({
      embedding: [0.1, 0.2, 0.3],
    }) as any);

    const embedding = await generateEmbedding('test text');
    
    expect(embedding).toEqual([0.1, 0.2, 0.3]);
    expect(embeddingSpy).toHaveBeenCalledWith({
      model: 'mxbai-embed-large',
      prompt: 'test text',
    });
  });

  it('generateEmbedding throws if ollama is not available', async () => {
    spyOn(ollama, 'list').mockImplementation(() => Promise.reject(new Error('Connection failed')));
    expect(generateEmbedding('test text')).rejects.toThrow('Ollama service is not available');
  });
});
