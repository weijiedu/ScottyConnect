import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './common/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import VerificationPage from './pages/VerificationPage'
import MainPage from './pages/MainPage'
import NetworkingPage from './pages/NetworkingPage'
import CreateEventPage from './pages/CreateEventPage'
import MyEventsPage from './pages/MyEventsPage'
import EventConfirmationPage from './pages/EventConfirmationPage'
import EditEventPage from './pages/EditEventPage'
import TaskBoardPage from './pages/TaskBoardPage'
import FeedbackHistoryPage from './pages/FeedbackHistoryPage'
import FeedbackSubmissionPage from './pages/FeedbackSubmissionPage'
import MyMeetingsPage from './pages/MyMeetingsPage'
import EventDetailPage from './pages/EventDetailPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify" element={<VerificationPage />} />
        <Route path="/mainpage" element={
          <ProtectedRoute>
            <MainPage />
          </ProtectedRoute>
        } />
        <Route path="/networking" element={
          <ProtectedRoute>
            <NetworkingPage />
          </ProtectedRoute>
        } />
        <Route path="/my-meetings" element={
          <ProtectedRoute>
            <MyMeetingsPage />
          </ProtectedRoute>
        } />
        <Route path="/feedback" element={
          <ProtectedRoute>
            <FeedbackHistoryPage />
          </ProtectedRoute>
        } />
        <Route
          path="/publish-event"
          element={
            <ProtectedRoute>
              <CreateEventPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-events"
          element={
            <ProtectedRoute>
              <MyEventsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/events/:id"
          element={
            <ProtectedRoute>
              <EventDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/events/:id/edit"
          element={
            <ProtectedRoute>
              <EditEventPage />
            </ProtectedRoute>
          }
        />
        <Route path="/events/:eventId/tasks" element={
          <ProtectedRoute>
            <TaskBoardPage />
          </ProtectedRoute>
        } />
        <Route path="/events/:eventId/feedback" element={
          <ProtectedRoute>
            <FeedbackSubmissionPage />
          </ProtectedRoute>
        } />
        <Route path="/event-published" element={
          <ProtectedRoute>
            <EventConfirmationPage />
          </ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to="/mainpage" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
