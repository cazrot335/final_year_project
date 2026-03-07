import { useState } from 'react'
import { BrowserRouter,Routes,Route } from 'react-router-dom' ;
import './App.css'
import Home from './pages/Home'
import Discovery from "./pages/Discorvery";
import GapAnalysis from "./pages/GapAnalysis";
import Interview from "./pages/Interview";
import AppLayout from './layout/AppLayout';

function App() {
  const [count, setCount] = useState(0)

  return (
     <BrowserRouter>

      <AppLayout>

        <Routes>

          <Route path="/" element={<Home />} />
          <Route path="/discovery" element={<Discovery />} />

          <Route path="/gap-analysis" element={<GapAnalysis />} />

          <Route path="/interview" element={<Interview />} />
        </Routes>

      </AppLayout>

    </BrowserRouter>
  )
}

export default App
