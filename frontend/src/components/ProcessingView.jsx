import { useEffect, useState } from 'react'

const STEPS = [
  { text: 'Parsing Annual Report PDF...',          flag: false },
  { text: 'Extracting financial statements...',    flag: false },
  { text: 'Loading bank statement transactions...', flag: false },
  { text: 'Running circular trading detection...', flag: true  },
  { text: 'Scanning for hidden EMI obligations...', flag: false },
  { text: 'GST–bank mismatch analysis...',          flag: true  },
  { text: 'Research agent: adverse news search...', flag: false },
  { text: 'MCA director DIN cross-check...',        flag: true  },
  { text: 'eCourts litigation search...',           flag: false },
  { text: 'Sector intelligence scan...',            flag: false },
  { text: 'Computing Five Cs scorecard...',         flag: false },
  { text: 'Analysis complete.',                     flag: false, final: true },
]

const S = {
  page: { 
    minHeight: '100vh', 
    padding: '24px',
    display: 'flex',
    flexDirection: 'column'
  },
  nav: { 
    padding: '16px 32px', 
    display: 'flex', 
    justifyContent: 'space-between', 
    alignItems: 'center',
    marginBottom: '40px'
  },
  navTitle: { 
    fontSize: '20px', 
    fontWeight: '700', 
    color: 'var(--text-main)', 
    letterSpacing: '-0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  navDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: 'var(--status-warning)',
    boxShadow: '0 0 10px var(--status-warning)',
    animation: 'blink 2s infinite'
  },
  navSub: { 
    color: 'var(--status-warning)', 
    letterSpacing: '1px',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  },
  body: { 
    width: '100%',
    maxWidth: '800px', 
    margin: '0 auto',
    flex: 1
  },
  header: { 
    marginBottom: '32px',
    textAlign: 'center'
  },
  tag: { 
    color: 'var(--status-warning)', 
    letterSpacing: '2px', 
    textTransform: 'uppercase', 
    marginBottom: '12px',
    fontSize: '12px',
    fontWeight: '600'
  },
  title: { 
    fontSize: '32px', 
    fontWeight: '700', 
    color: 'var(--text-main)',
    marginBottom: '8px',
    letterSpacing: '-0.5px'
  },
  sub: { 
    fontSize: '15px', 
    color: 'var(--text-muted)' 
  },
  terminal: { 
    background: '#050505', 
    padding: '32px', 
    minHeight: '400px',
    borderRadius: 'var(--radius-lg)',
    border: '1px solid var(--border)',
    boxShadow: 'inset 0 0 40px rgba(0,0,0,0.5), var(--shadow-lg)'
  },
  logLabel: { 
    color: 'var(--text-muted)', 
    letterSpacing: '2px', 
    textTransform: 'uppercase', 
    marginBottom: '24px',
    fontSize: '11px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid var(--border)',
    paddingBottom: '12px'
  },
  entry: { 
    marginBottom: '14px', 
    display: 'flex',
    alignItems: 'flex-start',
    animation: 'fadeUp 0.3s ease-out forwards',
    opacity: 0,
    transform: 'translateY(10px)'
  },
  prefix: (flag, final) => ({ 
    color: flag ? 'var(--status-warning)' : final ? 'var(--status-success)' : 'var(--accent-primary)', 
    marginRight: '12px',
    fontSize: '13px',
    marginTop: '2px'
  }),
  entryText: (flag, final) => ({ 
    fontSize: '14px', 
    color: flag ? 'var(--status-warning)' : final ? 'var(--status-success)' : 'var(--text-main)', 
    fontWeight: final ? '600' : '400',
    lineHeight: '1.5'
  }),
  cursor: { 
    display: 'inline-block', 
    width: '10px', 
    height: '16px', 
    background: 'var(--accent-primary)', 
    verticalAlign: 'middle', 
    marginLeft: '12px', 
    animation: 'blink 1s step-end infinite',
    boxShadow: '0 0 10px var(--accent-glow)'
  },
  note: { 
    marginTop: '32px', 
    padding: '16px', 
    background: 'var(--bg-input)', 
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-start'
  },
  noteIcon: {
    color: 'var(--text-muted)',
    fontSize: '18px'
  },
  noteText: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    lineHeight: '1.6'
  }
}

export default function ProcessingView({ onComplete }) {
  const [shown, setShown] = useState([])

  useEffect(() => {
    // Add keyframes for terminal entries
    const style = document.createElement('style')
    style.innerHTML = `
      @keyframes fadeUp {
        to { opacity: 1; transform: translateY(0); }
      }
      .spin { animation: spin 2s linear infinite; }
      @keyframes spin { 100% { transform: rotate(360deg); } }
    `
    document.head.appendChild(style)
    return () => document.head.removeChild(style)
  }, [])

  useEffect(() => {
    let i = 0
    const delays = [300,500,400,600,400,700,800,900,600,500,700,800]
    let timeoutId;
    
    function next() {
      if (i >= STEPS.length) {
        timeoutId = setTimeout(() => {
          if(onComplete) onComplete({
            company_name: "Mock Company Ltd",
            cin: "L12345MH2000PLC123456",
            loan_amount_cr: 15,
            sector: "Manufacturing",
            date: new Date().toLocaleDateString(),
            processing_time_seconds: 4.2,
            scoring: {
              decision: "CONDITIONAL",
              composite_score: 72
            }
          })
        }, 1500)
        return
      }
      const step = STEPS[i]
      setShown(p => [...p, step])
      i++
      timeoutId = setTimeout(next, delays[i] || 400)
    }
    timeoutId = setTimeout(next, 300)
    
    return () => clearTimeout(timeoutId)
  }, [onComplete])

  return (
    <div className="animate-fade-in" style={S.page}>
      <nav className="glass-panel" style={S.nav}>
        <div style={S.navTitle}>
          <div style={S.navDot}></div>
          INTELLI-CREDIT
        </div>
        <div className="mono" style={S.navSub}>
          <svg className="spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
          ANALYSIS IN PROGRESS
        </div>
      </nav>
      
      <div style={S.body}>
        <div style={S.header}>
          <div className="mono" style={S.tag}>Processing</div>
          <div style={S.title}>Running AI Credit Analysis</div>
          <div style={S.sub}>Do not close this window — securely processing documents.</div>
        </div>
        
        <div style={S.terminal}>
          <div className="mono" style={S.logLabel}>
            <span>System Log</span>
            <span>{Math.round((shown.length / STEPS.length) * 100)}%</span>
          </div>
          
          <div className="mono">
            {shown.map((s, i) => (
              <div key={i} style={S.entry}>
                <span style={S.prefix(s.flag, s.final)}>
                  {s.flag ? '[WARN]' : s.final ? '[DONE]' : '[INFO]'}
                </span>
                <span style={S.entryText(s.flag, s.final)}>{s.text}</span>
              </div>
            ))}
            {shown.length < STEPS.length && (
              <div style={{...S.entry, opacity: 1, transform: 'none'}}>
                <span style={S.prefix(false, false)}>[RUN ]</span>
                <span style={{color: 'var(--text-muted)'}}>processing next module...</span>
                <span style={S.cursor} />
              </div>
            )}
          </div>
        </div>
        
        <div style={S.note}>
          <div style={S.noteIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          </div>
          <div style={S.noteText}>
            The research agent is running live web searches for adverse news, MCA records, and eCourts litigation. Results are encrypted and temporarily stored in memory.
          </div>
        </div>
      </div>
    </div>
  )
}