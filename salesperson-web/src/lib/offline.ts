/**
 * Completion outbox.
 *
 * A visit report must never be lost because the phone had no signal in a
 * factory. Completions (and their optional follow-up) are written to local
 * storage first, then pushed; the queue is retried on reconnect and on app
 * resume. The server treats a repeated completion as idempotent, so retries are
 * safe.
 */

import { api, ApiError } from '@/api/client';
import type { ActivityOutcome, ActivityType } from '@/api/types';
import { localJson } from './storage';

const KEY = 'fieldsales.outbox';

export interface QueuedCompletion {
  token: string;
  activityId: number;
  outcome_code: ActivityOutcome;
  completion_note: string;
  completed_at: string;
  followUp?: {
    activity_type: ActivityType;
    scheduled_at: string;
    note: string | null;
  } | null;
}

type Listener = (pending: QueuedCompletion[]) => void;
const listeners = new Set<Listener>();

function read(): QueuedCompletion[] {
  return localJson.read<QueuedCompletion[]>(KEY, []);
}

function write(items: QueuedCompletion[]): void {
  localJson.write(KEY, items);
  listeners.forEach((listener) => listener(items));
}

export function pending(): QueuedCompletion[] {
  return read();
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  listener(read());
  return () => listeners.delete(listener);
}

export function enqueue(item: QueuedCompletion): void {
  const items = read().filter((existing) => existing.token !== item.token);
  write([...items, item]);
}

function dequeue(token: string): void {
  write(read().filter((item) => item.token !== token));
}

async function send(item: QueuedCompletion): Promise<void> {
  await api.post(`/salesperson/activities/${item.activityId}/complete`, {
    outcome_code: item.outcome_code,
    completion_note: item.completion_note,
    completed_at: item.completed_at,
    client_token: item.token,
  });
  if (item.followUp) {
    await api.post(`/salesperson/activities/${item.activityId}/follow-up`, item.followUp);
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
      }
    }
  } finally {
    flushing = false;
  }
  return synced;
}

export function newToken(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
