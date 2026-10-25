import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '@/auth/AuthProvider'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { PublicOnlyRoute } from '@/auth/PublicOnlyRoute'
import { AuthPage } from '@/pages/AuthPage'
import { ChatListPage } from '@/pages/ChatListPage'
import { ChatThreadPage } from '@/pages/ChatThreadPage'
import { SourceDocumentPage } from '@/pages/SourceDocumentPage'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/sign-in" element={<AuthPage mode="sign-in" />} />
            <Route path="/sign-up" element={<AuthPage mode="sign-up" />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/workspace" element={<Navigate to="/chats" replace />} />
            <Route path="/chats" element={<ChatListPage />} />
            <Route path="/chats/:threadId" element={<ChatThreadPage />} />
            <Route path="/sources/:documentId/:chunkId" element={<SourceDocumentPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/sign-in" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
