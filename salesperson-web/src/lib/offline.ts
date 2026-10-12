/**
 * Report outbox.
 *
 * A visit report must never be lost because the phone had no signal in a
 * factory. Two kinds of write go through here: completing an assigned activity,
 * and logging one the salesperson did on their own (a cold call or visit).
 * Both are written to local storage first, then pushed; the queue is retried on
 * reconnect and on app resume. Each carries a client token the server uses to
 * recognise a retry, so sending twice never records twice.
 */

import { api, ApiError } from '@/api/client';
import type {
  ActivityOutcome,
  ActivityType,
  LogActivityRequest,
  LogActivityResponse,
} from '@/api/types';
import { localJson } from './storage';

const KEY = 'fieldsales.outbox';

export interface QueuedFollowUp {
  activity_type: ActivityType;
  scheduled_at: string;
  note: string | null;
}

export interface QueuedCompletion {
  kind?: 'complete';
  token: string;
  activityId: number;
  outcome_code: ActivityOutcome;
  completion_note: string;
  completed_at: string;
  followUp?: QueuedFollowUp | null;
}

export interface QueuedLog {
  kind: 'log';
  token: string;
  /** Shown while it waits: "Call · Rajkot Polymers". */
  label: string;
  payload: LogActivityRequest;
  followUp?: QueuedFollowUp | null;
}

export type QueuedItem = QueuedCompletion | QueuedLog;

export const isLog = (item: QueuedItem): item is QueuedLog => item.kind === 'log';

type Listener = (pending: QueuedItem[]) => void;
const listeners = new Set<Listener>();

function read(): QueuedItem[] {
  return localJson.read<QueuedItem[]>(KEY, []);
}

function write(items: QueuedItem[]): void {
  localJson.write(KEY, items);
  listeners.forEach((listener) => listener(items));
}

export function pending(): QueuedItem[] {
  return read();
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  listener(read());
  return () => listeners.delete(listener);
}

export function enqueue(item: QueuedItem): void {
  const items = read().filter((existing) => existing.token !== item.token);
  write([...items, item]);
}

function dequeue(token: string): void {
  write(read().filter((item) => item.token !== token));
}

/** Results of the last flush, keyed by token, so a screen can show what was created. */
const results = new Map<string, LogActivityResponse>();

export function resultFor(token: string): LogActivityResponse | undefined {
  return results.get(token);
}

async function send(item: QueuedItem): Promise<void> {
  let activityId: number;
  if (isLog(item)) {
    const response = await api.post<LogActivityResponse>('/salesperson/activities', {
      ...item.payload,
      client_token: item.token,
    });
    results.set(item.token, response);
    activityId = response.activity.id;
  } else {
    await api.post(`/salesperson/activities/${item.activityId}/complete`, {
      outcome_code: item.outcome_code,
      completion_note: item.completion_note,
      completed_at: item.completed_at,
      client_token: item.token,
    });
    activityId = item.activityId;
  }
  if (item.followUp) {
    await api.post(`/salesperson/activities/${activityId}/follow-up`, item.followUp);
  }
}

let flushing = false;

/** Push everything we can; returns the number of reports that synced. */
export async function flush(): Promise<number> {
  if (flushing) return 0;
  flushing = true;
  let synced = 0;
  try {
    for (const item of read()) {
      try {
        await send(item);
        dequeue(item.token);
        synced += 1;
      } catch (error) {
        if (error instanceof ApiError && error.offline) break; // still offline, try later
        // A real rejection (e.g. the office cancelled the activity) must not
        // block the queue forever - drop it and let the user see the server state.
        dequeue(item.token);
        lastRejection = error instanceof ApiError ? error.message : 'A queued report was rejected.';
      }
    }
  } finally {
    flushing = false;
  }
  return synced;
}

let lastRejection: string | null = null;

/** The server's reason for refusing the most recent queued item, read once. */
export function takeRejection(): string | null {
  const message = lastRejection;
  lastRejection = null;
  return message;
}

export function newToken(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
