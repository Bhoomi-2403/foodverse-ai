import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import FoodRecognition from './pages/FoodRecognition';
import FreshnessDetector from './pages/FreshnessDetector';
import HygieneMonitor from './pages/HygieneMonitor';
import KitchenAssistant from './pages/KitchenAssistant';
import MealPlanner from './pages/MealPlanner';

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/food-recognition" element={<FoodRecognition />} />
          <Route path="/freshness-detector" element={<FreshnessDetector />} />
          <Route path="/hygiene-monitor" element={<HygieneMonitor />} />
          <Route path="/kitchen-assistant" element={<KitchenAssistant />} />
          <Route path="/meal-planner" element={<MealPlanner />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}
