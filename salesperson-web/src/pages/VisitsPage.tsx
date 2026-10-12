import { useNavigate } from 'react-router-dom';

import { useVisits } from '@/api/hooks';
import type { FieldActivity } from '@/api/types';
import { StatusPill } from '@/components/ActivityCard';
import { Icon } from '@/components/Icon';
import { Banner, Empty, Screen, SectionTitle, Skeletons } from '@/components/Shell';
import { time } from '@/lib/format';
import { openExternal } from '@/lib/native';

const MAPS_DIR = 'https://www.google.com/maps/dir/?api=1&travelmode=driving';

function stopOf(visit: FieldActivity): string | null {
  const location = visit.location;
  if (!location) return null;
  if (location.latitude && location.longitude) return `${location.latitude},${location.longitude}`;
  return location.formatted;
}

/** One Google Maps link through every open stop, in schedule order. */
function routeUrl(visits: FieldActivity[]): string | null {
  const stops = visits.map(stopOf).filter((stop): stop is string => Boolean(stop));
  if (!stops.length) return null;
  const destination = stops[stops.length - 1];
  const waypoints = stops.slice(0, -1);
  return (
    `${MAPS_DIR}&destination=${encodeURIComponent(destination)}` +
    (waypoints.length ? `&waypoints=${encodeURIComponent(waypoints.join('|'))}` : '')
  );
}

export function VisitsPage() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error } = useVisits();
  const visits = data ?? [];
  const open = visits.filter(
    (visit) => visit.status === 'SCHEDULED' || visit.status === 'IN_PROGRESS',
  );
  const done = visits.length - open.length;
  const route = routeUrl(open);
  const cities = Array.from(
    new Set(visits.map((visit) => visit.location?.city).filter(Boolean)),
  ) as string[];

  return (
    <Screen
      eyebrow="Today's route"
      title={
        visits.length ? (
          <>
            {visits.length} stop{visits.length > 1 ? 's' : ''}
            {cities.length ? <em> · {cities.slice(0, 2).join(', ')}</em> : null}
          </>
        ) : (
          'No stops today'
        )
      }
      subtitle={visits.length ? `${done} visited · ${open.length} to go` : undefined}
      hero={
        visits.length ? (
          <div className="route-hero">
            <div className="route-progress">
              {visits.map((visit) => (
                <span
                  key={visit.id}
                  className={`route-seg${visit.status === 'COMPLETED' ? ' done' : ''}${
                    visit.status === 'IN_PROGRESS' ? ' live' : ''
                  }`}
                />
              ))}
            </div>
            {route && (
              <button className="btn brass" onClick={() => openExternal(route)}>
                <Icon name="navigate" size={17} /> Drive the whole route
              </button>
            )}
          </div>
        ) : undefined
      }
    >
      {isError && (
        <Banner kind="error">{(error as Error)?.message ?? 'Could not load visits.'}</Banner>
      )}
      {isLoading && <Skeletons count={2} />}

      {visits.length > 0 && <SectionTitle aside="In schedule order">Stops</SectionTitle>}
      <div className="route">
        {visits.map((visit, index) => {
          const isDone = visit.status === 'COMPLETED';
          const live = visit.status === 'SCHEDULED' || visit.status === 'IN_PROGRESS';
          return (
            <div key={visit.id} className={`stop${isDone ? ' done' : ''}`}>
              <div className="stop-rail">
                <span className="stop-num">
                  {isDone ? <Icon name="check" size={14} stroke={2.6} /> : index + 1}
                </span>
              </div>
              <div
                className="stop-card"
                role="link"
                onClick={() => navigate(`/activity/${visit.id}`)}
              >
                <div className="row between">
                  <span className="stop-time">{time(visit.scheduled_at)}</span>
                  <StatusPill activity={visit} />
                </div>
                <div className="stop-name">{visit.customer.name}</div>
                {visit.location && <div className="stop-addr">{visit.location.formatted}</div>}
                {(visit.purpose || visit.subject) && !isDone && (
                  <div className="act-brief">{visit.subject || visit.purpose}</div>
                )}
                {live && (
                  <div className="btn-row tight" onClick={(event) => event.stopPropagation()}>
                    {visit.location && (
                      <button
                        className="btn small brass-soft"
                        onClick={() => openExternal(visit.location!.maps_url)}
                      >
                        <Icon name="navigate" size={15} /> Directions
                      </button>
                    )}
                    {visit.customer.phone && (
                      <a className="btn small ghost" href={`tel:${visit.customer.phone}`}>
                        <Icon name="phone" size={15} /> Call
                      </a>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!isLoading && !visits.length && (
        <Empty
          icon="route"
          title="No visits on the books"
          hint="Walked into a shop anyway? Log it as a cold visit."
        >
          <button
            className="btn ghost small"
            style={{ marginTop: 14 }}
            onClick={() => navigate('/log?type=VISIT')}
          >
            <Icon name="plus" size={16} /> Log a visit
          </button>
        </Empty>
      )}
    </Screen>
  );
}
