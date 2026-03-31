import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { MainLayout } from './layouts/MainLayout';
import { LoginPage } from './pages/LoginPage';
import { Dashboard, Contracts, ContractDetail, Issues, Integrations, Notifications } from './pages';
import { MarketingDashboard } from './pages/marketing/MarketingDashboard';
import { MarketingCalendar } from './pages/marketing/MarketingCalendar';
import { MarketingPosts } from './pages/marketing/MarketingPosts';
import { MarketingPostDetail } from './pages/marketing/MarketingPostDetail';
import { MarketingSources } from './pages/marketing/MarketingSources';
import { MarketingAI } from './pages/marketing/MarketingAI';
import { QuarantineDashboard } from './pages/quarantine/QuarantineDashboard';
import { Procurements } from './pages/procurement/Procurements';
import { ProcurementDetail } from './pages/procurement/ProcurementDetail';
import { AdminPage } from './pages/admin/AdminPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return (
    <div className="min-h-screen bg-[#F8FAFC] flex items-center justify-center">
      <span className="text-[#64748B] text-sm">Загрузка...</span>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user?.roles.includes('admin')) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        {/* Legal */}
        <Route index element={<Dashboard />} />
        <Route path="contracts" element={<Contracts />} />
        <Route path="contracts/:id" element={<ContractDetail />} />
        <Route path="issues" element={<Issues />} />
        <Route path="integrations" element={<Integrations />} />
        <Route path="notifications" element={<Notifications />} />

        {/* Marketing */}
        <Route path="marketing" element={<MarketingDashboard />} />
        <Route path="marketing/calendar" element={<MarketingCalendar />} />
        <Route path="marketing/posts" element={<MarketingPosts />} />
        <Route path="marketing/posts/:id" element={<MarketingPostDetail />} />
        <Route path="marketing/sources" element={<MarketingSources />} />
        <Route path="marketing/ai" element={<MarketingAI />} />

        {/* Quarantine */}
        <Route path="quarantine" element={<QuarantineDashboard />} />

        {/* Procurement */}
        <Route path="procurement" element={<Procurements />} />
        <Route path="procurement/:id" element={<ProcurementDetail />} />

        {/* Admin */}
        <Route
          path="admin"
          element={
            <AdminRoute>
              <AdminPage />
            </AdminRoute>
          }
        />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
