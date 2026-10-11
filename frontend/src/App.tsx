import { Center, Loader } from '@mantine/core';
import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/layout/AppLayout';
import { useAuth } from '@/lib/auth';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';
import { NotesPage } from '@/pages/NotesPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { ActivitiesPage } from '@/pages/activities/ActivitiesPage';
import { ActivityCalendarPage } from '@/pages/activities/ActivityCalendarPage';
import { SalespeoplePage } from '@/pages/activities/SalespeoplePage';
import { InquiriesPage } from '@/pages/inquiries/InquiriesPage';
import { InquiryDetailPage } from '@/pages/inquiries/InquiryDetailPage';
import { ApplicationsPage } from '@/pages/masters/ApplicationsPage';
import { GradesPage } from '@/pages/masters/GradesPage';
import { LocationsPage } from '@/pages/masters/LocationsPage';
import { ManufacturersPage } from '@/pages/masters/ManufacturersPage';
import { MaterialsPage } from '@/pages/masters/MaterialsPage';
import { ProductsPage } from '@/pages/masters/ProductsPage';
import { PartiesPage } from '@/pages/parties/PartiesPage';
import { PartyDetailPage } from '@/pages/parties/PartyDetailPage';

export function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />

        <Route path="/masters/products" element={<ProductsPage />} />
        <Route path="/masters/materials" element={<MaterialsPage />} />
        <Route path="/masters/grades" element={<GradesPage />} />
        <Route path="/masters/manufacturers" element={<ManufacturersPage />} />
        <Route path="/masters/applications" element={<ApplicationsPage />} />
        <Route path="/masters/locations" element={<LocationsPage />} />

        <Route path="/parties/customers" element={<PartiesPage partyType="CUSTOMER" />} />
        <Route path="/parties/suppliers" element={<PartiesPage partyType="SUPPLIER" />} />
        <Route path="/parties/transporters" element={<PartiesPage partyType="TRANSPORTER" />} />
        <Route path="/parties/:partyId" element={<PartyDetailPage />} />

        <Route path="/inquiries/customer" element={<InquiriesPage inquiryType="CUSTOMER" />} />
        <Route path="/inquiries/supplier" element={<InquiriesPage inquiryType="SUPPLIER" />} />
        <Route path="/inquiries/transport" element={<InquiriesPage inquiryType="TRANSPORT" />} />
        <Route path="/inquiries/:inquiryId" element={<InquiryDetailPage />} />

        <Route path="/activities/today" element={<ActivitiesPage scope="today" />} />
        <Route path="/activities/upcoming" element={<ActivitiesPage scope="upcoming" />} />
        <Route path="/activities/history" element={<ActivitiesPage scope="history" />} />
        <Route path="/activities/calendar" element={<ActivityCalendarPage />} />
        <Route path="/activities/salespeople" element={<SalespeoplePage />} />

        <Route path="/notes" element={<NotesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
