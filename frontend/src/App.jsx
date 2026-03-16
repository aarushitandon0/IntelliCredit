import { useState } from 'react'
import './App.css'
import UploadPortal    from './components/UploadPortal'
import ProcessingView  from './components/ProcessingView'
import ResultsDashboard from './components/ResultsDashboard'

export default function App() {
  const [view,   setView]   = useState('upload')   // upload | processing | results
  const [result, setResult] = useState(null)

  return (
    <>
      {view === 'upload' && (
        <UploadPortal
          onStart={() => setView('processing')}
          onResult={(data) => { setResult(data); setView('results') }}
        />
      )}
      {view === 'processing' && (
        <ProcessingView
          onComplete={(data) => { setResult(data); setView('results') }}
        />
      )}
      {view === 'results' && result && (
        <ResultsDashboard
          data={result}
          onReset={() => { setResult(null); setView('upload') }}
        />
      )}
    </>
  )
}