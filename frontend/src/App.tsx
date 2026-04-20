import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/layout/Layout'
import HomePage from '@/pages/HomePage'
import ChatPanel from '@/components/chat/ChatPanel'
import { useActiveCaseStore } from '@/store'

export default function App() {
  const { activeCase } = useActiveCaseStore()

  return (
    <>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </Layout>

      {/* Global slide-in chat panel — rendered outside Layout so it overlays */}
      {activeCase && <ChatPanel />}
    </>
  )
}
