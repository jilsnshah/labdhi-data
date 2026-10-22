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
import { BidDetailPage } from '@/pages/bids/BidDetailPage';
import { BidsPage } from '@/pages/bids/BidsPage';
import { InquiriesPage } from '@/pages/inquiries/InquiriesPage';
import { InquiryDetailPage } from '@/pages/inquiries/InquiryDetailPage';
import { PartyEnquiriesPage } from '@/pages/inquiries/PartyEnquiriesPage';
import { ApplicationsPage } from '@/pages/masters/ApplicationsPage';
import { GradesPage } from '@/pages/masters/GradesPage';
import { LocationsPage } from '@/pages/masters/LocationsPage';
import { ManufacturersPage } from '@/pages/masters/ManufacturersPage';
import { MaterialsPage } from '@/pages/masters/MaterialsPage';
import { ProductsPage } from '@/pages/masters/ProductsPage';
import { PartiesPage } from '@/pages/parties/PartiesPage';
import { PartyDetailPage } from '@/pages/parties/PartyDetailPage';
import { PortalEnquiryPage } from '@/pages/portal/PortalEnquiryPage';
import { PortalBidPage, PortalHomePage } from '@/pages/portal/PortalPage';

/**
 * The party portal: open to customers, suppliers and transporters who hold a
 * link - the bids they were invited to, and the enquiries they raise
 * themselves. It has no sign-in and no shell, and it is declared before
 * everything else so a signed-out visitor is never bounced to the login page.
 *
 * ``/enquire`` is declared before the bid route because both are one segment
 * after the code; a static segment outranks a parameter, so the word wins.
 */
const PORTAL_ROUTES = (
  <>
    <Route path="/portal/:code" element={<PortalHomePage />} />
    <Route path="/portal/:code/enquire" element={<PortalEnquiryPage />} />
    <Route path="/portal/:code/:bidId" element={<PortalBidPage />} />
  </>
);

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
        {PORTAL_ROUTES}
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      {PORTAL_ROUTES}
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

        <Route path="/bids/customer" element={<BidsPage bidType="CUSTOMER" />} />
        <Route path="/bids/supplier" element={<BidsPage bidType="SUPPLIER" />} />
        <Route path="/bids/transport" element={<BidsPage bidType="TRANSPORT" />} />
        <Route path="/bids/:bidId" element={<BidDetailPage />} />

        <Route path="/inquiries/customer" element={<InquiriesPage inquiryType="CUSTOMER" />} />
        <Route path="/inquiries/supplier" element={<InquiriesPage inquiryType="SUPPLIER" />} />
        <Route path="/inquiries/transport" element={<InquiriesPage inquiryType="TRANSPORT" />} />
        <Route path="/inquiries/from-parties" element={<PartyEnquiriesPage />} />
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
