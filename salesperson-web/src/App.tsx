import { useEffect } from 'react';
import { BRAND } from './lib/brand';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { useDashboard, useRefreshAll } from '@/api/hooks';
import { BottomNav } from '@/components/BottomNav';
import { Spinner, Toaster } from '@/components/Shell';
import { useAuth } from '@/lib/auth';
import { onNetworkRestored, onResume, registerBackButton } from '@/lib/native';
import * as outbox from '@/lib/offline';
import { ActivityDetailPage } from '@/pages/ActivityDetailPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { LogActivityPage } from '@/pages/LogActivityPage';
import { LoginPage } from '@/pages/LoginPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { TodayPage } from '@/pages/TodayPage';
import { UpcomingPage } from '@/pages/UpcomingPage';
import { VisitsPage } from '@/pages/VisitsPage';

const NAV_ROUTES = ['/today', '/visits', '/upcoming', '/profile'];

export function App() {
  const { profile, restoring } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const refresh = useRefreshAll();
  const { data } = useDashboard(Boolean(profile));

  // Hardware back: navigate inside the app, and only leave from a tab root.
  useEffect(() => {
    registerBackButton(
      () => !NAV_ROUTES.includes(window.location.hash.replace('#', '') || '/today'),
      () => navigate(-1),
      () => {
        if (window.confirm(`Close ${BRAND.name} Field?`)) {
          void import('@capacitor/app').then(({ App: CapApp }) => CapApp.exitApp());
        }
      },
    );
  }, [navigate]);

  // Flush queued reports when the network or the app comes back.
  useEffect(() => {
    const sync = () => {
      void outbox.flush().then((synced) => {
        if (synced > 0) refresh();
      });
    };
    onNetworkRestored(sync);
    onResume(sync);
    sync();
  }, [refresh]);

  if (restoring) {
    return (
      <div className="boot">
        <span className="brand-mark">L</span>
        <Spinner />
      </div>
    );
  }

  if (!profile) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }

  const showNav = NAV_ROUTES.includes(location.pathname);

  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/today" replace />} />
        <Route path="/today" element={<TodayPage />} />
        <Route path="/visits" element={<VisitsPage />} />
        <Route path="/upcoming" element={<UpcomingPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/log" element={<LogActivityPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/activity/:activityId" element={<ActivityDetailPage />} />
        <Route path="*" element={<Navigate to="/today" replace />} />
      </Routes>
      <Toaster />
      {showNav && (
        <BottomNav
          badges={{
            '/today': data?.counts.today_pending ?? 0,
            '/visits': data?.counts.today_visits ?? 0,
          }}
        />
      )}
    </>
  );
}
