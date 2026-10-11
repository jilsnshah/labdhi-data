/**
 * The 360-degree party screen.
 *
 * Who they are stays pinned in the rail - contact, addresses, what they trade -
 * while inquiries, field work, quotes and notes live in tabs, so the record is
 * one screen rather than a scroll.
 */

import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Group,
  Loader,
  Menu,
  Stack,
  Tabs,
  Text,
} from '@mantine/core';
import {
  IconCalendarPlus,
  IconDotsVertical,
  IconGitMerge,
  IconMapPin,
  IconNotes,
  IconPackage,
  IconPencil,
  IconPlus,
  IconTrash,
  IconUserCheck,
  IconX,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { partyApi, useApiMutation, useParty360 } from '@/api/hooks';
import type { PartyLocation, PartyProduct } from '@/api/types';
import { ActivityTable } from '@/components/ActivityTable';
import { DetailLayout, RailHighlight, RailSection } from '@/components/DetailLayout';
import { EventTimeline } from '@/components/EventTimeline';
import { InquiryTable } from '@/components/InquiryTable';
import { StatusBadge } from '@/components/StatusBadge';
import { ActivityFormModal } from '@/components/modals/ActivityModals';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { NoteFormModal } from '@/components/modals/NoteFormModal';
import {
  MergePartyModal,
  PartyApplicationModal,
  PartyFormModal,
  PartyLocationModal,
  PartyProductModal,
} from '@/components/modals/PartyModals';
import { EmptyState, Field } from '@/components/ui';
import { formatDate, formatDateTime, humanize } from '@/lib/format';

export function PartyDetailPage() {
  const { partyId } = useParams();
  const id = Number(partyId);
  const { data, isLoading } = useParty360(id);
  const [editOpen, setEditOpen] = useState(false);
  const [inquiryOpen, setInquiryOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [locationModal, setLocationModal] = useState<PartyLocation | null | 'new'>(null);
  const [productModal, setProductModal] = useState<PartyProduct | null | 'new'>(null);
  const [applicationModalOpen, setApplicationModalOpen] = useState(false);

  const promote = useApiMutation(() => partyApi.promote(id), {
    successMessage: 'Promoted to a known party',
  });
  const removeLocation = useApiMutation((linkId: number) => partyApi.removeLocation(id, linkId), {
    successMessage: 'Location unlinked',
  });
  const removeApplication = useApiMutation(
    (linkId: number) => partyApi.removeApplication(id, linkId),
    { successMessage: 'End-use unlinked' },
  );
  const removeProduct = useApiMutation((linkId: number) => partyApi.removeProduct(id, linkId), {
    successMessage: 'Product unlinked',
  });

  if (isLoading || !data) {
    return (
      <Group justify="center" py="xl">
        <Loader />
      </Group>
    );
  }

  const { party, stats } = data;
  const isCustomer = party.party_type === 'CUSTOMER';
  const isSupplier = party.party_type === 'SUPPLIER';
  const isTransporter = party.party_type === 'TRANSPORTER';

  const rail = (
    <>
      <RailHighlight
        label="Active inquiries"
        value={stats.open_inquiries}
        caption={`${stats.closed_inquiries} closed`}
      />

      <RailSection label="Contact">
        <Field label="Person" value={party.contact_person || '—'} width={74} />
        <Field label="Phone" value={party.phone || '—'} width={74} />
        <Field label="Email" value={party.email || '—'} width={74} />
        <Field label="GST" value={party.gst_number || '—'} width={74} />
      </RailSection>

      <RailSection
        label={isTransporter ? 'Operating areas' : 'Locations'}
        action={
          <Button
            size="compact-xs"
            variant="subtle"
            leftSection={<IconPlus size={12} />}
            onClick={() => setLocationModal('new')}
          >
            Add
          </Button>
        }
      >
        {party.locations.length === 0 ? (
          <Text fz="sm" c="ink.5">
            No address on record — a visit needs somewhere to go.
          </Text>
        ) : (
          party.locations.map((link) => (
            <Group key={link.id} justify="space-between" wrap="nowrap" align="flex-start">
              <Group gap={8} wrap="nowrap" style={{ minWidth: 0 }}>
                <IconMapPin size={14} style={{ marginTop: 3, opacity: 0.4, flexShrink: 0 }} />
                <Stack gap={0} style={{ minWidth: 0 }}>
                  <Group gap={6} wrap="nowrap">
                    <Text fz="sm" fw={550} truncate>
                      {link.location.label || link.location.city}
                    </Text>
                    {link.is_primary && (
                      <Text fz="xs" c="ink.5">
                        primary
                      </Text>
                    )}
                  </Group>
                  <Text fz="xs" c="ink.5" truncate>
                    {humanize(link.location_type)} ·{' '}
                    {[link.location.city, link.location.state].filter(Boolean).join(', ')}
                  </Text>
                </Stack>
              </Group>
              <RowMenu
                onEdit={() => setLocationModal(link)}
                onRemove={() => removeLocation.mutate(link.id)}
              />
            </Group>
          ))
        )}
      </RailSection>

      {!isTransporter && (
        <RailSection
          label={isSupplier ? 'Supplies' : 'Buys'}
          action={
            <Button
              size="compact-xs"
              variant="subtle"
              leftSection={<IconPlus size={12} />}
              onClick={() => setProductModal('new')}
            >
              Link
            </Button>
          }
        >
          {party.products.length === 0 ? (
            <Text fz="sm" c="ink.5">
              No products linked yet.
            </Text>
          ) : (
            party.products.map((link) => (
              <Group key={link.id} justify="space-between" wrap="nowrap">
                <Group gap={8} wrap="nowrap" style={{ minWidth: 0 }}>
                  <IconPackage size={14} style={{ opacity: 0.4, flexShrink: 0 }} />
                  <Stack gap={0} style={{ minWidth: 0 }}>
                    <Text fz="sm" truncate>
                      {link.product.display_name}
                    </Text>
                    <Text fz="xs" c="ink.5">
                      {humanize(link.relationship_type)}
                    </Text>
                  </Stack>
                </Group>
                <RowMenu
                  onEdit={() => setProductModal(link)}
                  onRemove={() => removeProduct.mutate(link.id)}
                />
              </Group>
            ))
          )}
        </RailSection>
      )}

      {!isTransporter && (
        <RailSection
          label="Works in"
          action={
            <Button
              size="compact-xs"
              variant="subtle"
              leftSection={<IconPlus size={12} />}
              onClick={() => setApplicationModalOpen(true)}
            >
              Add
            </Button>
          }
        >
          {party.applications.length === 0 ? (
            <Text fz="sm" c="ink.5">
              No end-use recorded yet.
            </Text>
          ) : (
            <Group gap={6}>
              {party.applications.map((link) => (
                <Badge
                  key={link.id}
                  variant="light"
                  color={link.active ? 'ink' : 'gray'}
                  size="sm"
                  rightSection={
                    <IconX
                      size={11}
                      style={{ cursor: 'pointer', display: 'block' }}
                      onClick={() => removeApplication.mutate(link.id)}
                    />
                  }
                >
                  {link.application.name}
                </Badge>
              ))}
            </Group>
          )}
        </RailSection>
      )}

      <RailSection label="Record">
        <Field label="Added" value={formatDate(party.created_at)} width={74} />
        <Field label="Source" value={humanize(party.source)} width={74} />
        <Text fz="xs" c="ink.5">
          {isCustomer ? 'Deals and sales' : isSupplier ? 'Purchases' : 'Transport jobs'} arrive with
          the trading module.
        </Text>
      </RailSection>
    </>
  );

  return (
    <>
      <Group justify="space-between" align="center" wrap="wrap" gap="md" mb="lg">
        <Stack gap={2} style={{ minWidth: 0 }}>
          <Group gap="sm" wrap="nowrap">
            <Text fz={20} fw={600} c="ink.9" lh={1.2} truncate>
              {party.name}
            </Text>
            {party.stage !== 'ACTIVE' && <StatusBadge value={party.stage} size="md" />}
            {party.status === 'INACTIVE' && <StatusBadge value="INACTIVE" size="md" />}
          </Group>
          <Text fz="sm" c="ink.5">
            {humanize(party.party_type)} · {stats.activities} activities · {stats.notes} notes
          </Text>
        </Stack>

        <Group gap="xs" wrap="nowrap">
          {party.stage === 'PROSPECT' && (
            <Button
              variant="default"
              leftSection={<IconUserCheck size={15} />}
              loading={promote.isPending}
              onClick={() => promote.mutate(undefined)}
            >
              Mark as known
            </Button>
          )}
          <Button
            variant="default"
            leftSection={<IconCalendarPlus size={15} />}
            onClick={() => setActivityOpen(true)}
          >
            Activity
          </Button>
          <Button leftSection={<IconPlus size={15} />} onClick={() => setInquiryOpen(true)}>
            New inquiry
          </Button>
          <Menu position="bottom-end" withinPortal width={210}>
            <Menu.Target>
              <ActionIcon variant="default" size={34} aria-label="More actions">
                <IconDotsVertical size={16} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item leftSection={<IconPencil size={15} />} onClick={() => setEditOpen(true)}>
                Edit details
              </Menu.Item>
              <Menu.Item leftSection={<IconNotes size={15} />} onClick={() => setNoteOpen(true)}>
                Add a note
              </Menu.Item>
              <Menu.Item leftSection={<IconGitMerge size={15} />} onClick={() => setMergeOpen(true)}>
                Merge a duplicate
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      {party.stage === 'MERGED' && party.merged_into_id && (
        <Alert color="ink" icon={<IconGitMerge size={16} />} mb="lg">
          Merged into{' '}
          <Text component={Link} to={`/parties/${party.merged_into_id}`} c="accent.9" fz="sm" span>
            party #{party.merged_into_id}
          </Text>
          . Kept for history; it cannot be used for new business.
        </Alert>
      )}
      {party.stage === 'PROSPECT' && (
        <Alert color="amber" icon={<IconUserCheck size={16} />} mb="lg">
          Created in one step from an inquiry or a call, so the identity is not verified yet.
          Closing an inquiry as <b>converted to deal</b> promotes it automatically.
        </Alert>
      )}

      <DetailLayout rail={rail}>
        <Tabs defaultValue="inquiries" className="work-tabs">
          <Tabs.List mb="md">
            <Tabs.Tab
              value="inquiries"
              rightSection={
                stats.open_inquiries ? (
                  <Text fz="xs" c="ink.5" className="mono-tight">
                    {stats.open_inquiries}
                  </Text>
                ) : undefined
              }
            >
              Inquiries
            </Tabs.Tab>
            <Tabs.Tab value="activities">Activities</Tabs.Tab>
            <Tabs.Tab value="notes">Notes</Tabs.Tab>
            <Tabs.Tab value="timeline">Timeline</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="inquiries">
            <Stack gap="lg">
              <Box>
                <Text fz="sm" c="ink.6" mb="sm">
                  Active
                </Text>
                <InquiryTable
                  rows={data.open_inquiries}
                  inquiryType={isCustomer ? 'CUSTOMER' : isSupplier ? 'SUPPLIER' : 'TRANSPORT'}
                  showParty={false}
                  emptyMessage="Nothing active"
                  emptyHint="New inquiries for this party appear here."
                />
              </Box>
              {data.inquiry_history.length > 0 && (
                <Box>
                  <Text fz="sm" c="ink.6" mb="sm">
                    Closed
                  </Text>
                  <InquiryTable
                    rows={data.inquiry_history}
                    inquiryType={isCustomer ? 'CUSTOMER' : isSupplier ? 'SUPPLIER' : 'TRANSPORT'}
                    showParty={false}
                  />
                </Box>
              )}
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="activities">
            <Stack gap="sm">
              <Group justify="space-between" align="center">
                <Text fz="sm" c="ink.6">
                  {stats.upcoming_activities} upcoming · {stats.activities} in total
                </Text>
                <Button
                  size="compact-sm"
                  variant="default"
                  leftSection={<IconPlus size={13} />}
                  onClick={() => setActivityOpen(true)}
                >
                  New activity
                </Button>
              </Group>
              <ActivityTable
                rows={data.activities}
                showCustomer={false}
                emptyMessage="No activity recorded yet"
                emptyHint="Schedule a call or a visit to start the history."
              />
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="notes">
            <Stack gap="sm">
              <Group justify="space-between" align="center">
                <Text fz="sm" c="ink.6">
                  Context that is not an activity
                </Text>
                <Button
                  size="compact-sm"
                  variant="default"
                  leftSection={<IconPlus size={13} />}
                  onClick={() => setNoteOpen(true)}
                >
                  Add note
                </Button>
              </Group>
              {data.notes.length === 0 ? (
                <Card padding="xl">
                  <EmptyState icon={<IconNotes size={20} />} title="No notes yet" compact />
                </Card>
              ) : (
                <Stack gap="sm">
                  {data.notes.map((note) => (
                    <Card key={note.id} padding="md">
                      <Text fz="sm" className="wrap">
                        {note.note}
                      </Text>
                      <Text fz="xs" c="ink.5" mt={6}>
                        {note.creator?.name} · {formatDateTime(note.created_at)}
                      </Text>
                    </Card>
                  ))}
                </Stack>
              )}
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="timeline">
            <Card padding="lg">
              <EventTimeline events={data.timeline} />
            </Card>
          </Tabs.Panel>
        </Tabs>
      </DetailLayout>

      {editOpen && (
        <PartyFormModal
          partyType={party.party_type}
          record={party}
          onClose={() => setEditOpen(false)}
        />
      )}
      {inquiryOpen && (
        <InquiryFormModal
          opened
          onClose={() => setInquiryOpen(false)}
          defaultType={isCustomer ? 'CUSTOMER' : isSupplier ? 'SUPPLIER' : 'TRANSPORT'}
          lockType
          partyId={party.id}
          partyLabel={party.name}
        />
      )}
      {activityOpen && (
        <ActivityFormModal
          partyId={party.id}
          partyLabel={party.name}
          partyType={party.party_type}
          onClose={() => setActivityOpen(false)}
        />
      )}
      {noteOpen && (
        <NoteFormModal partyId={party.id} partyLabel={party.name} onClose={() => setNoteOpen(false)} />
      )}
      {locationModal && (
        <PartyLocationModal
          party={party}
          record={locationModal === 'new' ? null : locationModal}
          onClose={() => setLocationModal(null)}
        />
      )}
      {applicationModalOpen && (
        <PartyApplicationModal party={party} onClose={() => setApplicationModalOpen(false)} />
      )}
      {productModal && (
        <PartyProductModal
          party={party}
          record={productModal === 'new' ? null : productModal}
          onClose={() => setProductModal(null)}
        />
      )}
      {mergeOpen && <MergePartyModal party={party} onClose={() => setMergeOpen(false)} />}
    </>
  );
}

function RowMenu({ onEdit, onRemove }: { onEdit: () => void; onRemove: () => void }) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon size="sm" aria-label="Row actions">
          <IconDotsVertical size={13} />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item leftSection={<IconPencil size={14} />} onClick={onEdit}>
          Edit
        </Menu.Item>
        <Menu.Item color="rust" leftSection={<IconTrash size={14} />} onClick={onRemove}>
          Unlink
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
