import { describe, it, expect, mock, spyOn, beforeEach } from 'bun:test';
import { extractDecisionsFromThread } from './summarizer';
import * as ollamaBridge from '../ollama';
import type { ThreadRecord } from '../types/decisions';

describe('Summarizer', () => {
  beforeEach(() => {
    mock.restore();
  });

  it('extractDecisionsFromThread correctly parses a decision block', async () => {
    const thread: ThreadRecord = {
      id: 'thread-1',
      payload: {
        text: "Let's decide on the color. I suggest blue. <@U123> agrees. We should also link PROJ-456.",
        user: 'U123',
        messageTs: '123456',
        channelId: 'C123'
      }
    };

    const mockResponse = `
DECISION_START
Outcome: We decided to use blue for the new UI.
Participants: <@U123>
Next Steps: Update the style guide.
Citation: Let's decide on the color. I suggest blue.
DECISION_END
`;

    spyOn(ollamaBridge, 'generateCompletion').mockImplementation(() => Promise.resolve(mockResponse));

    const decisions = await extractDecisionsFromThread(thread);

    expect(decisions).toHaveLength(1);
    expect(decisions[0].outcome).toBe('We decided to use blue for the new UI.');
    expect(decisions[0].participants).toContain('<@U123>');
    expect(decisions[0].citation).toBe("Let's decide on the color. I suggest blue.");
    expect(decisions[0].threadId).toBe('thread-1');
  });

  it('extractDecisionsFromThread hoists Linear IDs', async () => {
      const thread: ThreadRecord = {
        id: 'thread-2',
        payload: {
          text: 'We are tracking this in PROJ-789. <@U456> is assigned.',
          user: 'U456',
          messageTs: '123457',
          channelId: 'C123'
        }
      };

      const mockResponse = `
DECISION_START
Outcome: Linked to PROJ-789.
Participants: <@U456>
Next Steps: Finish PROJ-789.
Citation: We are tracking this in PROJ-789.
DECISION_END
`;

      spyOn(ollamaBridge, 'generateCompletion').mockImplementation(() => Promise.resolve(mockResponse));

      const decisions = await extractDecisionsFromThread(thread);

      expect(decisions[0].linearIds).toContain('PROJ-789');
  });

  it('extractDecisionsFromThread filters out hallucinations (citations not in source)', async () => {
    const thread: ThreadRecord = {
      id: 'thread-3',
      payload: {
        text: 'Real text here.',
        user: 'U123',
        messageTs: '123458',
        channelId: 'C123'
      }
    };

    const mockResponse = `
DECISION_START
Outcome: Fake decision.
Participants: None
Next Steps: None
Citation: Hallucinated text.
DECISION_END
`;

    spyOn(ollamaBridge, 'generateCompletion').mockImplementation(() => Promise.resolve(mockResponse));

    const decisions = await extractDecisionsFromThread(thread);
    expect(decisions).toHaveLength(0);
  });
});
