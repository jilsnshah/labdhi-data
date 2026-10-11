/** Schedule, assign, log, complete and follow up on customer activities. */

import {
  Alert,
  Button,
  Group,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { DateTimePicker } from '@mantine/dates';
import { IconAlertTriangle, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';

import { activityApi, useApiMutation, useConflictCheck } from '@/api/hooks';
import type {
  Activity,
  ActivityOutcome,
  ActivityType,
  PartyQuickCreate,
  PartyType,
} from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import {
  canCreateParty,
  cleanQuickCreate,
  NewPartyFields,
} from '@/components/modals/NewPartyFields';
import {
  formatDateTime,
  humanize,
  pickerNowPlus,
  toIso,
  toPickerDateTime,
} from '@/lib/format';

const TYPES: ActivityType[] = ['CALL', 'WHATSAPP', 'SMS', 'VISIT', 'EMAIL', 'MEETING'];
/** Types the backend requires a location for. */
const LOCATION_TYPES: ActivityType[] = ['VISIT', 'MEETING'];

const OUTCOMES: ActivityOutcome[] = [
  'COMPLETED',
  'CUSTOMER_INTERESTED',
  'CUSTOMER_NOT_INTERESTED',
  'FOLLOW_UP_REQUIRED',
  'NO_RESPONSE',
  'RESCHEDULED',
  'OTHER',
];

function ConflictWarning({
  salespersonId,
  scheduledAt,
  excludeActivityId,
}: {
  salespersonId: number | null;
  scheduledAt: string | null;
  excludeActivityId?: number;
}) {
  const { data } = useConflictCheck(salespersonId, scheduledAt, excludeActivityId);
  if (!data?.has_conflict) return null;
  return (
    <Alert color="amber" icon={<IconAlertTriangle size={16} />} p="xs">
      <Text fz="xs" fw={600}>
        Potential scheduling conflict
      </Text>
      {data.conflicts.map((conflict) => (
        <Text key={conflict.activity_id} fz="xs">
          Already has {humanize(conflict.activity_type)} with {conflict.customer_name} at{' '}
          {formatDateTime(conflict.scheduled_at)} ({conflict.minutes_apart} min apart)
        </Text>
      ))}
      <Text fz="xs" c="dimmed" mt={4}>
        You can still save this activity.
      </Text>
    </Alert>
  );
}

export function ActivityFormModal({
  onClose,
  partyId,
  partyLabel,
  partyType: fixedPartyType,
  relatedInquiryId,
  record,
  defaultType = 'CALL',
  defaultSalespersonId,
}: {
  onClose: () => void;
  partyId?: number;
  partyLabel?: string;
  /** Locks the party type, e.g. when opened from a supplier page. */
  partyType?: PartyType;
  relatedInquiryId?: number;
  record?: Activity | null;
  defaultType?: ActivityType;
  defaultSalespersonId?: number | null;
}) {
  const [mode, setMode] = useState<'SCHEDULE' | 'LOG'>('SCHEDULE');
  const [partyType, setPartyType] = useState<PartyType>(
    fixedPartyType ?? record?.party?.party_type ?? 'CUSTOMER',
  );
  const [partySource, setPartySource] = useState<'EXISTING' | 'NEW'>('EXISTING');
  const [newParty, setNewParty] = useState<PartyQuickCreate>({});
  const [party, setParty] = useState<number | null>(partyId ?? record?.party_id ?? null);
  const [activityType, setActivityType] = useState<ActivityType>(
    record?.activity_type ?? defaultType,
  );
  const [subject, setSubject] = useState(record?.subject ?? '');
  const [when, setWhen] = useState<string | null>(
    toPickerDateTime(record?.scheduled_at) ?? pickerNowPlus(1, 'hour'),
  );
  const [note, setNote] = useState(record?.note ?? '');
  const [outcome, setOutcome] = useState('');
  const [outcomeCode, setOutcomeCode] = useState<ActivityOutcome>('COMPLETED');
  const [salespersonId, setSalespersonId] = useState<number | null>(
    record?.assigned_salesperson_id ?? defaultSalespersonId ?? null,
  );
  const [locationId, setLocationId] = useState<number | null>(record?.location_id ?? null);
  const [locationMode, setLocationMode] = useState<'PICK' | 'NEW' | 'TEXT'>('PICK');
  const [newLocation, setNewLocation] = useState({ label: '', city: '', state: '' });
  const [locationText, setLocationText] = useState('');

  const needsLocation = LOCATION_TYPES.includes(activityType);

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record ? activityApi.patch(record.id, body) : activityApi.create(body),
    { successMessage: record ? 'Activity updated' : 'Activity saved' },
  );

  const locationPayload = () => {
    if (!needsLocation) return { location_id: null };
    if (locationMode === 'NEW') {
      return {
        new_location: {
          label: newLocation.label.trim() || null,
          city: newLocation.city.trim(),
          state: newLocation.state.trim() || null,
        },
      };
    }
    if (locationMode === 'TEXT') {
      return { location_text: locationText.trim() };
    }
    return { location_id: locationId };
  };

  const partyPayload = () =>
    partySource === 'NEW'
      ? { new_party: cleanQuickCreate(newParty, partyType) }
      : { party_id: party };

  const submit = async () => {
    const base = {
      activity_type: activityType,
      subject: subject.trim() || null,
      note: note.trim() || null,
      assigned_salesperson_id: salespersonId,
      ...locationPayload(),
    };
    if (record) {
      await save.mutateAsync({ ...base, scheduled_at: toIso(when) });
    } else if (mode === 'SCHEDULE') {
      await save.mutateAsync({
        ...base,
        ...partyPayload(),
        status: 'SCHEDULED',
        scheduled_at: toIso(when),
        related_inquiry_id: relatedInquiryId ?? null,
      });
    } else {
      await save.mutateAsync({
        ...base,
        ...partyPayload(),
        status: 'COMPLETED',
        completed_at: toIso(when) ?? new Date().toISOString(),
        outcome: outcome.trim() || null,
        outcome_code: outcomeCode,
        related_inquiry_id: relatedInquiryId ?? null,
      });
    }
    onClose();
  };

  const partyReady =
    partySource === 'NEW' ? canCreateParty(newParty) : party !== null;
  const locationReady =
    !needsLocation ||
    (locationMode === 'PICK' && locationId !== null) ||
    (locationMode === 'NEW' && newLocation.city.trim().length > 0) ||
    (locationMode === 'TEXT' && locationText.trim().length > 0);
  const valid = (record ? true : partyReady) && (mode === 'LOG' || when !== null) && locationReady;

  return (
    <Modal
      opened
      onClose={onClose}
      size="lg"
      title={record ? `Activity #${record.id}` : 'Customer activity'}
    >
      <Stack gap="md">
        {!record && (
          <SegmentedControl
            fullWidth
            value={mode}
            onChange={(value) => setMode(value as 'SCHEDULE' | 'LOG')}
            data={[
              { value: 'SCHEDULE', label: 'Schedule / assign' },
              { value: 'LOG', label: 'Log something done' },
            ]}
          />
        )}
        {!record && (
          <>
            {!fixedPartyType && (
              <SegmentedControl
                fullWidth
                size="xs"
                value={partyType}
                onChange={(value) => {
                  setPartyType(value as PartyType);
                  setParty(null);
                }}
                data={[
                  { value: 'CUSTOMER', label: 'Customer' },
                  { value: 'SUPPLIER', label: 'Supplier' },
                  { value: 'TRANSPORTER', label: 'Transporter' },
                ]}
              />
            )}
            {!partyId && (
              <SegmentedControl
                fullWidth
                size="xs"
                value={partySource}
                onChange={(value) => setPartySource(value as 'EXISTING' | 'NEW')}
                data={[
                  { value: 'EXISTING', label: 'Known party' },
                  { value: 'NEW', label: "Someone new" },
                ]}
              />
            )}
          </>
        )}

        {partySource === 'NEW' && !record ? (
          <NewPartyFields
            partyType={partyType}
            value={newParty}
            onChange={setNewParty}
            onUseExisting={(id) => {
              setParty(id);
              setPartySource('EXISTING');
            }}
          />
        ) : (
          <EntitySelect
            kind="party"
            label={humanize(partyType)}
            required
            filters={{ party_type: partyType }}
            value={party}
            onChange={setParty}
            initialLabel={partyLabel ?? record?.party?.name}
            disabled={Boolean(partyId) || Boolean(record)}
          />
        )}
        <Group grow>
          <Select
            label="Type"
            data={TYPES.map((value) => ({ value, label: humanize(value) }))}
            value={activityType}
            onChange={(value) => value && setActivityType(value as ActivityType)}
            allowDeselect={false}
          />
          <DateTimePicker
            label={mode === 'LOG' && !record ? 'Happened at' : 'Scheduled at'}
            required
            valueFormat="DD MMM YYYY, HH:mm"
            value={when}
            onChange={setWhen}
          />
        </Group>

        {needsLocation && (
          <Stack gap="xs">
            <SegmentedControl
              fullWidth
              size="xs"
              value={locationMode}
              onChange={(value) => setLocationMode(value as 'PICK' | 'NEW' | 'TEXT')}
              data={[
                { value: 'PICK', label: 'Known address' },
                { value: 'NEW', label: 'New address' },
                { value: 'TEXT', label: 'Just describe it' },
              ]}
            />
            {locationMode === 'PICK' && (
              <EntitySelect
                kind="location"
                label="Location"
                required
                description="Where the field user has to go."
                value={locationId}
                onChange={setLocationId}
                initialLabel={
                  record?.location
                    ? [record.location.label, record.location.city].filter(Boolean).join(' - ')
                    : undefined
                }
                filters={party ? { party_id: party } : undefined}
              />
            )}
            {locationMode === 'NEW' && (
              <Group grow>
                <TextInput
                  label="Label"
                  placeholder="Factory / shop"
                  value={newLocation.label}
                  onChange={(event) =>
                    setNewLocation({ ...newLocation, label: event.currentTarget.value })
                  }
                />
                <TextInput
                  label="City"
                  required
                  value={newLocation.city}
                  onChange={(event) =>
                    setNewLocation({ ...newLocation, city: event.currentTarget.value })
                  }
                />
                <TextInput
                  label="State"
                  value={newLocation.state}
                  onChange={(event) =>
                    setNewLocation({ ...newLocation, state: event.currentTarget.value })
                  }
                />
              </Group>
            )}
            {locationMode === 'TEXT' && (
              <TextInput
                label="Where to go"
                required
                description="No address on file yet - the field user can pin it on arrival."
                placeholder="His shop on Gondal Road, opposite the bus stand"
                value={locationText}
                onChange={(event) => setLocationText(event.currentTarget.value)}
              />
            )}
          </Stack>
        )}

        <EntitySelect
          kind="user"
          label="Assign to salesperson"
          description="Only active salesperson accounts appear here. Leave empty to keep it with the desk."
          filters={{ role: 'SALESPERSON' }}
          value={salespersonId}
          onChange={setSalespersonId}
          initialLabel={record?.assigned_salesperson?.name}
        />

        {mode === 'SCHEDULE' && (
          <ConflictWarning
            salespersonId={salespersonId}
            scheduledAt={toIso(when) ?? null}
            excludeActivityId={record?.id}
          />
        )}

        <TextInput
          label="Subject"
          placeholder="e.g. Visit ABC Pipes factory"
          value={subject}
          onChange={(event) => setSubject(event.currentTarget.value)}
        />
        <Textarea
          label={mode === 'LOG' && !record ? 'Context' : 'Purpose / brief for the field user'}
          autosize
          minRows={2}
          placeholder="Discuss the monthly PVC requirement. Customer is interested in Reliance K-67."
          value={note}
          onChange={(event) => setNote(event.currentTarget.value)}
        />
        {mode === 'LOG' && !record && (
          <>
            <Select
              label="Outcome"
              data={OUTCOMES.map((value) => ({ value, label: humanize(value) }))}
              value={outcomeCode}
              onChange={(value) => value && setOutcomeCode(value as ActivityOutcome)}
              allowDeselect={false}
            />
            <Textarea
              label="What happened?"
              autosize
              minRows={2}
              value={outcome}
              onChange={(event) => setOutcome(event.currentTarget.value)}
            />
          </>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!valid}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function CompleteActivityModal({
  activity,
  onClose,
}: {
  activity: Activity;
  onClose: () => void;
}) {
  const [outcome, setOutcome] = useState('');
  const [outcomeCode, setOutcomeCode] = useState<ActivityOutcome>('COMPLETED');
  const [withFollowUp, setWithFollowUp] = useState(false);
  const [followUpType, setFollowUpType] = useState<ActivityType>(activity.activity_type);
  const [followUpAt, setFollowUpAt] = useState<string | null>(pickerNowPlus(7, 'day'));
  const [followUpNote, setFollowUpNote] = useState('');

  const complete = useApiMutation((body: unknown) => activityApi.complete(activity.id, body), {
    successMessage: 'Activity completed',
  });

  const submit = async () => {
    await complete.mutateAsync({
      outcome: outcome.trim(),
      outcome_code: outcomeCode,
      completed_at: new Date().toISOString(),
      follow_up: withFollowUp
        ? {
            activity_type: followUpType,
            scheduled_at: toIso(followUpAt),
            note: followUpNote.trim() || null,
          }
        : null,
    });
    onClose();
  };

  return (
    <Modal opened onClose={onClose} title={`Complete ${humanize(activity.activity_type)}`}>
      <Stack gap="md">
        <Alert color="ink" p="xs" icon={<IconInfoCircle size={16} />}>
          <Text fz="xs">
            {activity.party?.name} · scheduled {formatDateTime(activity.scheduled_at)}
            {activity.assigned_salesperson
              ? ` · assigned to ${activity.assigned_salesperson.name}`
              : ''}
          </Text>
          {activity.note && (
            <Text fz="xs" c="dimmed" mt={4}>
              Plan: {activity.note}
            </Text>
          )}
        </Alert>
        <Select
          label="Outcome"
          data={OUTCOMES.map((value) => ({ value, label: humanize(value) }))}
          value={outcomeCode}
          onChange={(value) => value && setOutcomeCode(value as ActivityOutcome)}
          allowDeselect={false}
        />
        <Textarea
          label="What happened?"
          required
          data-autofocus
          autosize
          minRows={3}
          value={outcome}
          onChange={(event) => setOutcome(event.currentTarget.value)}
        />
        <Switch
          label="Schedule a follow-up"
          description="Creates a new activity linked to this one, keeping the same assignee."
          checked={withFollowUp}
          onChange={(event) => setWithFollowUp(event.currentTarget.checked)}
        />
        {withFollowUp && (
          <Stack gap="md">
            <Group grow>
              <Select
                label="Follow-up type"
                data={TYPES.map((value) => ({ value, label: humanize(value) }))}
                value={followUpType}
                onChange={(value) => value && setFollowUpType(value as ActivityType)}
                allowDeselect={false}
              />
              <DateTimePicker
                label="Scheduled at"
                required
                valueFormat="DD MMM YYYY, HH:mm"
                value={followUpAt}
                onChange={setFollowUpAt}
              />
            </Group>
            <Textarea
              label="Why this follow-up?"
              autosize
              minRows={2}
              value={followUpNote}
              onChange={(event) => setFollowUpNote(event.currentTarget.value)}
            />
          </Stack>
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            loading={complete.isPending}
            disabled={!outcome.trim() || (withFollowUp && !followUpAt)}
          >
            Complete
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function AssignActivityModal({
  activity,
  onClose,
}: {
  activity: Activity;
  onClose: () => void;
}) {
  const [salespersonId, setSalespersonId] = useState<number | null>(
    activity.assigned_salesperson_id,
  );
  const assign = useApiMutation(
    (value: number | null) => activityApi.assign(activity.id, value),
    { successMessage: 'Assignment updated' },
  );

  return (
    <Modal opened onClose={onClose} title={`Assign activity #${activity.id}`}>
      <Stack gap="md">
        <Text fz="sm" c="dimmed">
          {humanize(activity.activity_type)} · {activity.party?.name} ·{' '}
          {formatDateTime(activity.scheduled_at)}
        </Text>
        <EntitySelect
          kind="user"
          label="Salesperson"
          filters={{ role: 'SALESPERSON' }}
          value={salespersonId}
          onChange={setSalespersonId}
          initialLabel={activity.assigned_salesperson?.name}
          description="Clear the field to hand the activity back to the desk."
        />
        <ConflictWarning
          salespersonId={salespersonId}
          scheduledAt={activity.scheduled_at}
          excludeActivityId={activity.id}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={assign.isPending}
            onClick={async () => {
              await assign.mutateAsync(salespersonId);
              onClose();
            }}
          >
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
