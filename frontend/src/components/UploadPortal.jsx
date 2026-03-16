import { useState, useRef } from 'react'
import { api } from '../api/client'

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
    background: 'var(--accent-primary)',
    boxShadow: '0 0 10px var(--accent-primary)'
  },
  navSub: { 
    color: 'var(--text-muted)', 
    letterSpacing: '1px',
    fontSize: '12px'
  },
  body: { 
    width: '100%',
    maxWidth: '1000px', 
    margin: '0 auto',
    flex: 1
  },
  headerSection: {
    marginBottom: '40px',
    textAlign: 'center'
  },
  pageTag: { 
    color: 'var(--accent-primary)', 
    letterSpacing: '2px', 
    textTransform: 'uppercase', 
    marginBottom: '12px',
    fontSize: '12px',
    fontWeight: '600'
  },
  pageTitle: { 
    fontSize: '42px', 
    fontWeight: '700', 
    color: 'var(--text-main)', 
    marginBottom: '16px',
    letterSpacing: '-1px'
  },
  pageDesc: {
    color: 'var(--text-muted)',
    fontSize: '16px',
    maxWidth: '500px',
    margin: '0 auto',
    lineHeight: '1.6'
  },
  grid: { 
    display: 'grid', 
    gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', 
    gap: '32px' 
  },
  card: { 
    padding: '32px' 
  },
  sectionLabel: {
    fontSize: '18px',
    fontWeight: '600',
    color: 'var(--text-main)',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  label: { 
    display: 'block', 
    fontSize: '13px', 
    fontWeight: '500',
    color: 'var(--text-label)', 
    marginBottom: '8px' 
  },
  input: { 
    width: '100%', 
    border: '1px solid var(--border)', 
    padding: '12px 16px', 
    fontSize: '15px', 
    background: 'var(--bg-input)', 
    color: 'var(--text-main)', 
    marginBottom: '20px', 
    borderRadius: 'var(--radius-md)',
    outline: 'none',
    transition: 'all var(--transition-fast)',
    boxSizing: 'border-box'
  },
  dropzone: (active, done) => ({
    border: `2px dashed ${done ? 'var(--status-success)' : active ? 'var(--accent-primary)' : 'var(--border)'}`,
    padding: '20px', 
    marginBottom: '16px', 
    cursor: 'pointer',
    background: done ? 'var(--status-success-bg)' : active ? 'var(--bg-input)' : 'transparent',
    display: 'flex', 
    justifyContent: 'space-between', 
    alignItems: 'center',
    transition: 'all var(--transition-normal)',
    borderRadius: 'var(--radius-md)'
  }),
  dropTitle: { 
    fontSize: '14px', 
    fontWeight: '600', 
    color: 'var(--text-main)', 
    marginBottom: '4px' 
  },
  dropSub: { 
    fontSize: '12px', 
    color: 'var(--text-muted)' 
  },
  dropStatus: (done) => ({ 
    fontSize: '12px', 
    fontWeight: done ? '600' : '500', 
    color: done ? 'var(--status-success)' : 'var(--text-muted)',
    background: done ? 'transparent' : 'var(--bg-input)',
    padding: done ? '0' : '6px 12px',
    borderRadius: 'var(--radius-full)'
  }),
  note: { 
    marginTop: '24px', 
    padding: '16px', 
    background: 'rgba(59, 130, 246, 0.1)', 
    border: '1px solid rgba(59, 130, 246, 0.2)',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-start'
  },
  noteIcon: {
    color: 'var(--accent-primary)',
    fontSize: '18px'
  },
  noteText: { 
    fontSize: '13px', 
    color: 'var(--text-label)', 
    lineHeight: '1.6' 
  },
  submitBtn: { 
    width: '100%', 
    background: 'var(--accent-primary)', 
    color: '#fff', 
    border: 'none', 
    padding: '16px', 
    fontSize: '16px', 
    fontWeight: '600', 
    marginTop: '32px', 
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    transition: 'all var(--transition-normal)',
    boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.39)',
  },
  error: { 
    background: 'var(--status-error-bg)', 
    border: '1px solid var(--status-error)', 
    padding: '16px', 
    marginTop: '24px', 
    borderRadius: 'var(--radius-md)',
    fontSize: '14px', 
    color: '#fca5a5',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
}

export default function UploadPortal({ onResult, onStart }) {
  const [form, setForm]   = useState({ company_name:'', cin:'', loan_amount_cr:'', sector:'' })
  const [files, setFiles] = useState({ annual_report:null, bank_statement:null, gstr3b:null, gstr2a:null })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [dragActive, setDragActive] = useState(null)
  const refs = { annual_report: useRef(), bank_statement: useRef(), gstr3b: useRef(), gstr2a: useRef() }

  const handleFile = (key, file) => {
    if (file) setFiles(f => ({ ...f, [key]: file }))
  }

  const handleSubmit = async () => {
    if (!form.company_name || !form.cin || !form.loan_amount_cr || !form.sector) {
      setError('Please fill all application details.'); return
    }
    setError('')
    setLoading(true)
    if(onStart) onStart()
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k,v]) => fd.append(k, v))
      Object.entries(files).forEach(([k,v]) => { if (v) fd.append(k, v) })
      // Simulated delay for UI demonstration if api is not fully connected
      // await new Promise(r => setTimeout(r, 2000))
      const res = await api.analyze(fd)
      onResult(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Analysis failed.')
      setLoading(false)
    } 
  }

  const docTypes = [
    { key:'annual_report',  label:'Annual Report',              sub:'PDF — Digital or Scanned',     req:true  },
    { key:'bank_statement', label:'Bank Statement (12 Months)', sub:'CSV or Excel',                 req:true  },
    { key:'gstr3b',         label:'GST Filings — GSTR-3B',      sub:'CSV or Excel',                 req:false },
    { key:'gstr2a',         label:'GST GSTR-2A',                sub:'CSV or Excel (Optional)',      req:false },
  ]

  return (
    <div className="animate-fade-in" style={S.page}>
      <nav className="glass-panel" style={S.nav}>
        <div style={S.navTitle}>
          <div style={S.navDot}></div>
          INTELLI-CREDIT
        </div>
        <div className="mono" style={S.navSub}></div>
      </nav>

      <div style={S.body}>
        <div style={S.headerSection}>
          <div className="mono" style={S.pageTag}></div>
          <div style={S.pageTitle}>Credit Appraisal Portal</div>
          <div style={S.pageDesc}>Upload corporate documents to initiate an automated, AI-driven credit risk analysis.</div>
        </div>

        <div style={S.grid}>
          {/* LEFT — application details */}
          <div className="glass-panel" style={S.card}>
            <div style={S.sectionLabel}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
              Application Details
            </div>
            {[
              ['company_name',   'Company Name',                       'text'],
              ['cin',            'Corporate Identification Number',    'text'],
              ['loan_amount_cr', 'Loan Amount Requested (₹ Crore)',   'number'],
              ['sector',         'Industry Sector',                    'text'],
            ].map(([key, label, type]) => (
              <div key={key}>
                <label style={S.label}>{label}</label>
                <input
                  style={S.input}
                  type={type}
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={`Enter ${label.toLowerCase()}`}
                  onFocus={(e) => e.target.style.borderColor = 'var(--accent-primary)'}
                  onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
                />
              </div>
            ))}
          </div>

          {/* RIGHT — document upload */}
          <div className="glass-panel" style={S.card}>
            <div style={S.sectionLabel}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.2 15c.7-1.2 1-2.5.7-3.9-.6-2-2.4-3.5-4.4-3.5h-1.2c-.7-3-3.2-5.2-6.2-5.6-3-.3-5.9 1.3-7.3 4-1.2 2.5-1 6.5.5 8.8m8.7-1.6V21"></path><path d="M16 16l-4-4-4 4"></path></svg>
              Document Upload
            </div>
            {docTypes.map(({ key, label, sub }) => (
              <div
                key={key}
                style={S.dropzone(dragActive === key, !!files[key])}
                onClick={() => refs[key].current.click()}
                onDragOver={(e) => { e.preventDefault(); setDragActive(key) }}
                onDragLeave={() => setDragActive(null)}
                onDrop={(e) => { e.preventDefault(); setDragActive(null); handleFile(key, e.dataTransfer.files[0]) }}
              >
                <div>
                  <div style={S.dropTitle}>{label}</div>
                  <div className="mono" style={S.dropSub}>{sub}</div>
                </div>
                <div className="mono" style={S.dropStatus(!!files[key])}>
                  {files[key] ? (
                    <span style={{ display:'flex', alignItems:'center', gap:'6px' }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      {files[key].name.slice(0,20)}{files[key].name.length > 20 ? '...' : ''}
                    </span>
                  ) : 'BROWSE'}
                </div>
                <input ref={refs[key]} type="file" hidden
                  accept=".pdf,.csv,.xlsx,.xls"
                  onChange={e => handleFile(key, e.target.files[0])}
                />
              </div>
            ))}
            <div style={S.note}>
              <div style={S.noteIcon}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
              </div>
              <div style={S.noteText}>Annual Report and Bank Statement are required. Providing GST files significantly improves loan limit accuracy and processing speed.</div>
            </div>
          </div>
        </div>

        {error && (
          <div className="animate-fade-in" style={S.error}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            {error}
          </div>
        )}

        <button
          style={{ 
            ...S.submitBtn, 
            opacity: loading ? 0.7 : 1,
            transform: loading ? 'scale(0.98)' : 'scale(1)',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
          onClick={handleSubmit}
          disabled={loading}
          onMouseOver={(e) => !loading && (e.target.style.background = 'var(--accent-primary-hover)')}
          onMouseOut={(e) => !loading && (e.target.style.background = 'var(--accent-primary)')}
        >
          {loading ? 'Initializing Engine...' : 'Begin Credit Analysis'}
        </button>
      </div>
    </div>
  )
}