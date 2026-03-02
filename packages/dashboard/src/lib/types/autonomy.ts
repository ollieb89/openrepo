export type AutonomyState = 'planning' | 'executing' | 'blocked' | 'escalating' | 'complete';

export interface AutonomyEscalation {
  reason: string;
  confidence: number;
  timestamp: number;
}

export interface AutonomyInfo {
  state: AutonomyState;
  confidence_score: number;
  selected_tools: string[];
  escalation?: AutonomyEscalation;
}

import type { Task } from '@/lib/types';

export interface TaskWithAutonomy extends Task {
  title?: string;
  autonomy?: AutonomyInfo;
}

export interface AutonomyStateChangedEvent {
  type: 'autonomy.state_changed';
  task_id: string;
  payload: {
    state: AutonomyState;
    previous_state: AutonomyState;
  };
  timestamp: number;
}

export interface AutonomyConfidenceUpdatedEvent {
  type: 'autonomy.confidence_updated';
  task_id: string;
  payload: {
    score: number;
    previous_score: number;
  };
  timestamp: number;
}

export interface AutonomyEscalationTriggeredEvent {
  type: 'autonomy.escalation_triggered';
  task_id: string;
  payload: {
    reason: string;
    confidence: number;
  };
  timestamp: number;
}

export interface AutonomyToolsSelectedEvent {
  type: 'autonomy.tools_selected';
  task_id: string;
  payload: {
    tools: string[];
  };
  timestamp: number;
}

export interface AutonomyCourseCorrectionEvent {
  type: 'autonomy.course_correction';
  task_id: string;
  payload: {
    failed_step: {
      action: string;
    };
    recovery_steps: {
      action: string;
    }[];
  };
  timestamp: number;
}

export type AutonomyEvent = 
  | AutonomyStateChangedEvent 
  | AutonomyConfidenceUpdatedEvent 
  | AutonomyEscalationTriggeredEvent 
  | AutonomyToolsSelectedEvent
  | AutonomyCourseCorrectionEvent;

export interface EscalationEvent {
  task_id: string;
  reason: string;
  confidence: number;
  timestamp: number;
}

export interface CourseCorrection {
  timestamp: number;
  failed_step: {
    action: string;
  };
  recovery_steps: {
    action: string;
  }[];
}
