import { streamCompletion } from './src/lib/ollama';

async function test() {
  console.log('Starting stream...');
  try {
    const generator = streamCompletion('Tell me a short joke about a pirate.');
    for await (const token of generator) {
      process.stdout.write(token);
    }
    console.log('\nStream finished.');
  } catch (error) {
    console.error('Error during test:', error);
  }
}

test();
