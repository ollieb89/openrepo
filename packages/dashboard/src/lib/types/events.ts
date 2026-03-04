export enum EventDomain {
  TASK = 'openclaw.task',
  AGENT = 'openclaw.agent',
  AUTONOMY = 'openclaw.autonomy',
  MEMORY = 'openclaw.memory',
  POOL = 'openclaw.pool',
}

export enum EventType {
  // Task lifecycle
  TASK_CREATED = 'task.created',
  TASK_STARTED = 'task.started',
  TASK_COMPLETED = 'task.completed',
  TASK_FAILED = 'task.failed',
  TASK_ESCALATED = 'task.escalated',
  TASK_OUTPUT = 'task.output',

  // Agent lifecycle
  AGENT_DISPATCHED = 'agent.dispatched',
  AGENT_RESPONSE = 'agent.response',
  AGENT_ERROR = 'agent.error',

  // Autonomy
  AUTONOMY_STATE_CHANGED = 'autonomy.state_changed',
  AUTONOMY_CONFIDENCE_UPDATED = 'autonomy.confidence_updated',
  AUTONOMY_ESCALATION = 'autonomy.escalation',

  // Memory
  MEMORY_STORED = 'memory.stored',
  MEMORY_RECALLED = 'memory.recalled',

  // Pool
  POOL_SLOT_ACQUIRED = 'pool.slot_acquired',
  POOL_SLOT_RELEASED = 'pool.slot_released',
  POOL_OVERFLOW = 'pool.overflow',
}

export interface TaskOutputPayload {
  line: string;
  stream: 'stdout' | 'stderr';
}

export interface OrchestratorEvent {
  type: EventType;
  domain: EventDomain;
  project_id: string;
  agent_id?: string;
  task_id?: string;
  payload?: Record<string, any>;
  timestamp: number;
  correlation_id?: string;
}
