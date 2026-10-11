import { useVisits } from '@/api/hooks';
import { ActivityCard } from '@/components/ActivityCard';
import { Banner, Empty, Screen, Skeletons } from '@/components/Shell';
import { openExternal } from '@/lib/native';

export function VisitsPage() {
  const { data, isLoading, isError, error } = useVisits();
  const visits = data ?? [];

  return (
    <Screen
      title="Today's visits"
      subtitle={visits.length ? `${visits.length} stop${visits.length > 1 ? 's' : ''}` : 'No stops'}
    >
      {isError && (
        <Banner kind="error">{(error as Error)?.message ?? 'Could not load visits.'}</Banner>
      )}
      {isLoading && <Skeletons count={2} />}

      {visits.map((visit, index) => (
        <div key={visit.id}>
          <div className="section-title">
            Stop {index + 1}
            {visit.location?.city ? ` · ${visit.location.city}` : ''}
          </div>
          <ActivityCard activity={visit} />
        </div>
      ))}

      {visits.length > 1 && (
        <button
          className="btn secondary"
          style={{ marginTop: 6 }}
          onClick={() => openExternal(visits[0].location?.maps_url ?? '')}
        >
          Start with the first stop
        </button>
      )}

      {!isLoading && !visits.length && (
        <Empty
          icon="🚗"
          title="No visits today"
          hint="Calls and messages are on the Today screen."
        />
      )}
    </Screen>
  );
}
