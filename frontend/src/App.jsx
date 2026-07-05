import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './layouts/AppLayout.jsx';
import LoginPage from './pages/LoginPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import HeatmapPage from './pages/HeatmapPage.jsx';
import EmployeeProfilePage from './pages/EmployeeProfilePage.jsx';
import TasksPage from './pages/TasksPage.jsx';
import EvidencesPage from './pages/EvidencesPage.jsx';
import EvidenceAnalysisPage from './pages/EvidenceAnalysisPage.jsx';
import KpiEvaluationPage from './pages/KpiEvaluationPage.jsx';
import CopilotChatPage from './pages/CopilotChatPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Trang login — công khai */}
          <Route path="/login" element={<LoginPage />} />

          {/* Tất cả route còn lại cần đăng nhập */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/heatmap" element={<HeatmapPage />} />
            <Route path="/employees/:userId" element={<EmployeeProfilePage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/evidences" element={<EvidencesPage />} />
            <Route path="/evidences/:evidenceId/analysis" element={<EvidenceAnalysisPage />} />
            <Route path="/kpi/:userId" element={<KpiEvaluationPage />} />
            <Route path="/copilot" element={<CopilotChatPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
