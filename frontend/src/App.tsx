import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layouts/MainLayout';
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

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
