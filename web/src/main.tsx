import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { initCapacitorShell } from './capacitor/init'
import './index.css'
import App from './App.tsx'

void initCapacitorShell()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
