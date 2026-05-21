import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SessionProvider } from "./hooks/SessionContext.jsx";
import ProtectedLayout from "./layout/ProtectedLayout.jsx";
import DoctorDashboard from "./pages/DoctorDashboard.jsx";
import DoctorPatientPage from "./pages/DoctorPatientPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import PatientDashboard from "./pages/PatientDashboard.jsx";
import PatientStats from "./pages/PatientStats.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import RehabPage from "./pages/RehabPage.jsx";
import "./styles/index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <SessionProvider>
        <Routes>
          <Route path="/auth/login" element={<LoginPage />} />
          <Route path="/auth/register" element={<RegisterPage />} />
          <Route path="/patient" element={<Navigate to="/patient/" replace />} />
          <Route path="/doctor" element={<Navigate to="/doctor/" replace />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/patient/" element={<PatientDashboard />} />
            <Route path="/patient/history" element={<Navigate to="/patient/stats" replace />} />
            <Route path="/patient/stats" element={<PatientStats />} />
            <Route path="/patient/rehab" element={<Navigate to="/patient/rehab/" replace />} />
            <Route path="/patient/rehab/" element={<RehabPage />} />
            <Route path="/doctor/" element={<DoctorDashboard />} />
            <Route path="/doctor/patient/:patientId" element={<DoctorPatientPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/auth/login" replace />} />
        </Routes>
      </SessionProvider>
    </BrowserRouter>
  </StrictMode>
);
