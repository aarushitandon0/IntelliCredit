import { useState } from 'react'
import OverviewTab   from './tabs/OverviewTab'
import FraudTab      from './tabs/FraudTab'
import ResearchTab   from './tabs/ResearchTab'
import FiveCsTab     from './tabs/FiveCsTab'
import OfficerPortal from './tabs/OfficerPortal'

const TABS = [
  { id:'overview',  label:'Overview',        icon: 'M4 6h16M4 12h16M4 18h7' },
  { id:'fraud',     label:'Fraud Detection', icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' },
  { id:'research',  label:'Research',        icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4' },
  { id:'fivecs',    label:'Five Cs Score',   icon: 'M12 20V10m0 10l-4-4m4 4l4-4M4 4h16' },
  { id:'officer',   label:'Officer Portal',  icon: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m8-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8z' },
]

const S = {
  wrap: { 
    height: '100vh', 
    display: 'flex', 
    flexDirection: 'row', 
    background: 'var(--bg-dark)'
  },
  sidebar: {
    width: '260px',
    background: 'var(--bg-card)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0
  },
  sidebarHeader: {
    padding: '24px',
    borderBottom: '1px solid var(--border)',
    marginBottom: '16px'
  },
  brandTitle: {
    fontSize: '18px', 
    fontWeight: '700', 
    color: 'var(--text-main)', 
    letterSpacing: '-0.5px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '8px'
  },
  navDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: 'var(--accent-primary)',
    boxShadow: '0 0 10px var(--accent-glow)'
  },
  brandSub: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    paddingLeft: '20px'
  },
  tabList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '0 12px',
    flex: 1
  },
  tabBtn: (active) => ({
    padding: '12px 16px', 
    border: 'none',
    borderLeft: active ? '3px solid var(--accent-primary)' : '3px solid transparent',
    background: active ? 'var(--bg-input)' : 'transparent',
    borderRadius: active ? '0 var(--radius-md) var(--radius-md) 0' : 'var(--radius-md)',
    fontSize: '14px', 
    fontWeight: active ? '600' : '500',
    color: active ? 'var(--text-main)' : 'var(--text-muted)',
    cursor: 'pointer', 
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    transition: 'all var(--transition-fast)',
    textAlign: 'left'
  }),
  sidebarFooter: {
    padding: '24px',
    borderTop: '1px solid var(--border)'
  },
  resetBtn: { 
    width: '100%',
    fontSize: '13px', 
    color: 'var(--text-main)', 
    fontWeight: '500', 
    background: 'var(--bg-input)', 
    border: '1px solid var(--border)', 
    padding: '10px 16px', 
    cursor: 'pointer',
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px'
  },
  mainPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0
  },
  topbar: {
    padding: '24px 40px',
    borderBottom: '1px solid var(--border)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: 'var(--bg-card)',
    backdropFilter: 'blur(8px)',
  },
  topMetaGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  companyName: {
    fontSize: '24px',
    fontWeight: '700',
    color: 'var(--text-main)',
    letterSpacing: '-0.5px'
  },
  metaText: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  topRight: { 
    display: 'flex', 
    gap: '24px', 
    alignItems: 'center' 
  },
  scoreGroup: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '4px'
  },
  scoreVal: { 
    fontSize: '32px', 
    fontWeight: '700',
    letterSpacing: '-1px',
    lineHeight: '1'
  },
  scoreLabel: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '1px'
  },
  badge: (color) => ({ 
    background: `${color}15`, 
    color: color,
    border: `1px solid ${color}40`,
    fontSize: '11px', 
    fontWeight: '600', 
    letterSpacing: '1px', 
    padding: '6px 12px',
    borderRadius: 'var(--radius-full)'
  }),
  infoBar: { 
    background: 'rgba(0,0,0,0.2)', 
    padding: '12px 40px', 
    display: 'flex', 
    gap: '40px', 
    borderBottom: '1px solid var(--border)', 
    flexShrink: 0, 
    overflowX: 'auto' 
  },
  infoItem: { 
    display: 'flex', 
    gap: '8px', 
    alignItems: 'center', 
    whiteSpace: 'nowrap' 
  },
  infoKey: { 
    fontSize: '11px', 
    color: 'var(--text-muted)', 
    textTransform: 'uppercase', 
    letterSpacing: '1px' 
  },
  infoVal: { 
    fontSize: '13px', 
    color: 'var(--text-main)',
    fontWeight: '500' 
  },
  content: { 
    flex: 1, 
    overflowY: 'auto', 
    padding: '40px' 
  },
}

function decisionColor(d) {
  if (d === 'APPROVED') return 'var(--status-success)'
  if (d === 'CONDITIONAL') return 'var(--status-warning)'
  if (d === 'REJECTED') return 'var(--status-error)'
  return 'var(--text-muted)'
}

export default function ResultsDashboard({ data, onReset }) {
  const [tab, setTab] = useState('overview')
  const scoring  = data?.scoring || {}
  const decision = scoring.decision || 'PENDING'
  const score    = scoring.composite_score || 0

  return (
    <div className="animate-fade-in" style={S.wrap}>
      
      {/* LEFT SIDEBAR */}
      <div style={S.sidebar}>
        <div style={S.sidebarHeader}>
          <div style={S.brandTitle}>
            <div style={S.navDot}></div>
            INTELLI-CREDIT
          </div>
          <div className="mono" style={S.brandSub}>Corporate Dashboard</div>
        </div>

        <div style={S.tabList}>
          {TABS.map(t => (
            <button 
              key={t.id} 
              style={S.tabBtn(tab === t.id)} 
              onClick={() => setTab(t.id)}
              onMouseOver={e => {
                if (tab !== t.id) e.target.style.background = 'var(--bg-input)';
              }}
              onMouseOut={e => {
                if (tab !== t.id) e.target.style.background = 'transparent';
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: tab === t.id ? 1 : 0.6 }}>
                <path d={t.icon}></path>
              </svg>
              {t.label}
            </button>
          ))}
        </div>

        <div style={S.sidebarFooter}>
          <button 
            style={S.resetBtn} 
            onClick={onReset}
            onMouseOver={e => {
              e.currentTarget.style.background = 'var(--bg-card-hover)';
              e.currentTarget.style.borderColor = 'var(--border-focus)';
            }}
            onMouseOut={e => {
              e.currentTarget.style.background = 'var(--bg-input)';
              e.currentTarget.style.borderColor = 'var(--border)';
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ pointerEvents: 'none' }}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
            NEW ANALYSIS
          </button>
        </div>
      </div>

      {/* RIGHT MAIN PANEL */}
      <div style={S.mainPanel}>
        
        {/* TOP HEADER */}
        <div style={S.topbar}>
          <div style={S.topMetaGroup}>
            <div className="mono" style={S.companyName}>{data.company_name}</div>
            <div className="mono" style={S.metaText}>
              <span>ID: {data.analysis_id || 'PENDING'}</span>
              <span style={{ color: 'var(--border)' }}>|</span>
              <span>{data.date}</span>
            </div>
          </div>

          <div style={S.topRight}>
            <div style={S.scoreGroup}>
              <span className="mono" style={{ ...S.scoreVal, color: decisionColor(decision) }}>{score}</span>
              <span className="mono" style={S.scoreLabel}>COMPOSITE SCORE</span>
            </div>
            <div className="mono" style={S.badge(decisionColor(decision))}>{decision}</div>
          </div>
        </div>

        {/* INFO STRIP */}
        <div style={S.infoBar}>
          {[
            ['Facility',  `₹${data.loan_amount_cr} Cr Working Capital`],
            ['Sector',    data.sector],
            ['CIN',       data.cin],
            ['Process Time', `${data.processing_time_seconds}s`],
          ].map(([k, v]) => (
            <div key={k} style={S.infoItem}>
              <span className="mono" style={S.infoKey}>{k}</span>
              <span className="mono" style={S.infoVal}>{v}</span>
            </div>
          ))}
        </div>

        {/* SCROLLABLE CONTENT */}
        <div style={S.content}>
          {tab === 'overview'  && <OverviewTab   data={data} />}
          {tab === 'fraud'     && <FraudTab      data={data} />}
          {tab === 'research'  && <ResearchTab   data={data} />}
          {tab === 'fivecs'    && <FiveCsTab     data={data} />}
          {tab === 'officer'   && <OfficerPortal data={data} />}
        </div>

      </div>
    </div>
  )
}