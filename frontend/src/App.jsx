import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Competitors from './pages/Competitors'
import Insights from './pages/Insights'

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-950 text-white">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 pt-16 md:pt-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/competitors" element={<Competitors />} />
            <Route path="/insights" element={<Insights />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
export default App
