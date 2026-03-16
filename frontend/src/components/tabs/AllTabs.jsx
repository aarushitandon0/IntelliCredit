// OverviewTab.jsx
import { useState } from 'react'

const MONO = "'JetBrains Mono', monospace"
const RED  = '#b91c1c'
const AMB  = '#92400e'
const GRN  = '#14532d'
const GRY  = '#6b7280'
const BOR  = '#cdc9c1'
const LIG  = '#f3f0eb'
const BLK  = '#0d0d0d'
const WHT  = '#ffffff'

function scoreColor(s) { return s < 4 ? RED : s < 6.5 ? AMB : GRN }
function decColor(d)   { return d === 'APPROVED' ? GRN : d === 'REJECTED' ? RED : AMB }

function Card({ children, style={} }) {
  return <div style={{ background:WHT, border:`1.5px solid ${BOR}`, padding:20, ...style }}>{children}</div>
}

function SLabel({ children }) {
  return <div style={{ fontFamily:MONO, fontSize:8.5, letterSpacing:2.5, textTransform:'uppercase', color:GRY, marginBottom:14 }}>{children}</div>
}

function ScoreGauge({ score=0 }) {
  const r=72, cx=100, cy=96
  const pct = Math.min(score/100, 1)
  const rad  = a => a * Math.PI / 180
  const endAngle = 180 - pct*180
  const ex = cx + r*Math.cos(rad(endAngle))
  const ey = cy - r*Math.sin(rad(endAngle))
  const largeArc = pct > 0.5 ? 1 : 0
  const trackPath = `M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}`
  const fillPath  = `M ${cx-r} ${cy} A ${r} ${r} 0 ${largeArc} 1 ${ex.toFixed(2)} ${ey.toFixed(2)}`
  const dc = scoreColor(score/10)
  return (
    <div style={{ textAlign:'center' }}>
      <svg width={200} height={116} viewBox="0 0 200 116">
        <path d={trackPath} fill="none" stroke={BOR} strokeWidth={10} />
        <path d={fillPath}  fill="none" stroke={dc}  strokeWidth={10} />
        <text x={cx} y={cy-10} textAnchor="middle" style={{ fontFamily:MONO, fontSize:28, fontWeight:600, fill:BLK }}>{score}</text>
        <text x={cx} y={cy+10} textAnchor="middle" style={{ fontFamily:MONO, fontSize:10, fill:GRY }}>out of 100</text>
      </svg>
      <div style={{ display:'inline-block', background:dc, color:'#fff', fontFamily:MONO, fontSize:11, fontWeight:600, letterSpacing:2, padding:'5px 18px' }}>
        {/* decision shown in parent */}
      </div>
    </div>
  )
}

export function OverviewTab({ data }) {
  const scoring  = data?.scoring || {}
  const cc       = data?.cross_checks || {}
  const research = data?.research || {}
  const decision = scoring.decision || 'PENDING'
  const score    = scoring.composite_score || 0

  const metrics = [
    { label:'Circular Trading',  value: cc.circular_trading_instances > 0 ? `${cc.circular_trading_instances} instances` : 'None', bad: cc.circular_trading_instances > 0 },
    { label:'Circular Volume',   value: `₹${cc.circular_trading_cr || 0}Cr`, bad: cc.circular_trading_cr > 0 },
    { label:'Cheque Bounces',    value: cc.cheque_bounces || 0, bad: cc.cheque_bounces > 2 },
    { label:'Hidden EMIs',       value: cc.hidden_emis || 0, bad: cc.hidden_emis > 0 },
    { label:'HIGH Risk Flags',   value: research.high_flags || 0, bad: research.high_flags > 0 },
    { label:'Research Queries',  value: research.total_queries || 0, bad: false },
  ]

  return (
    <div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:20 }}>
        <Card style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center' }}>
          <SLabel>Credit Score</SLabel>
          <ScoreGauge score={score} />
          <div style={{ background:decColor(decision), color:'#fff', fontFamily:MONO, fontSize:11, fontWeight:600, letterSpacing:2, padding:'5px 18px', marginTop:8 }}>
            {decision}
          </div>
        </Card>
        <Card>
          <SLabel>Decision Rationale</SLabel>
          <p style={{ fontSize:11, color:'#333', lineHeight:1.75, fontStyle:'italic' }}>
            "{scoring.rationale}"
          </p>
        </Card>
      </div>

      <Card>
        <SLabel>Key Metrics</SLabel>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:1, background:BOR }}>
          {metrics.map((m,i) => (
            <div key={i} style={{ background:WHT, padding:'14px 16px' }}>
              <div style={{ fontFamily:MONO, fontSize:8, color:GRY, letterSpacing:1.5, textTransform:'uppercase', marginBottom:5 }}>{m.label}</div>
              <div style={{ fontFamily:MONO, fontSize:18, fontWeight:600, color: m.bad ? RED : BLK }}>{m.value}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export function FraudTab({ data }) {
  const bank = data?.bank_analysis || {}
  const cc   = data?.cross_checks  || {}
  const th   = { fontFamily:MONO, fontSize:8.5, letterSpacing:1.5, textTransform:'uppercase', color:GRY, padding:'9px 12px', borderBottom:`1.5px solid ${BOR}`, textAlign:'left', background:LIG }
  const td   = (bad=false) => ({ fontFamily:MONO, fontSize:10, color: bad ? RED : BLK, padding:'10px 12px', borderBottom:`1px solid ${BOR}` })

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
      {/* Summary */}
      <Card>
        <SLabel>Bank Statement Summary</SLabel>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:1, background:BOR }}>
          {[
            ['Total Credits',    `₹${bank.total_credits_cr || 0}Cr`,    false],
            ['Total Debits',     `₹${bank.total_debits_cr  || 0}Cr`,    false],
            ['Transactions',     bank.total_transactions || 0,          false],
            ['Months Covered',   bank.months_covered || 0,              false],
            ['Circular Instances', cc.circular_trading_instances || 0,  cc.circular_trading_instances > 2],
            ['Bounces',          cc.cheque_bounces || 0,                 cc.cheque_bounces > 2],
          ].map(([l,v,bad],i) => (
            <div key={i} style={{ background:WHT, padding:'12px 14px' }}>
              <div style={{ fontFamily:MONO, fontSize:8, color:GRY, letterSpacing:1.5, textTransform:'uppercase', marginBottom:4 }}>{l}</div>
              <div style={{ fontFamily:MONO, fontSize:16, fontWeight:600, color: bad ? RED : BLK }}>{String(v)}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Flags */}
      <Card>
        <SLabel>Fraud Detection Flags</SLabel>
        <p style={{ fontFamily:MONO, fontSize:9, color:GRY }}>
          Detailed transaction-level analysis available in the full CAM report. Key signals detected by rule-based Pandas algorithms — no LLM involved.
        </p>
      </Card>
    </div>
  )
}

export function ResearchTab({ data }) {
  const research = data?.research || {}
  const flags    = research.risk_flags || []
  const sevColor = s => s === 'HIGH' ? RED : s === 'MEDIUM' ? AMB : GRY

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
      {/* Summary bar */}
      <div style={{ background:'#111', padding:'12px 18px', display:'flex', gap:20, alignItems:'center' }}>
        {[['HIGH', research.high_flags||0, RED],['MEDIUM', research.medium_flags||0, AMB]].map(([l,v,c])=>(
          <div key={l} style={{ textAlign:'center' }}>
            <div style={{ fontFamily:MONO, fontSize:22, fontWeight:600, color:c }}>{v}</div>
            <div style={{ fontFamily:MONO, fontSize:8, color:'#666', letterSpacing:1.5, textTransform:'uppercase' }}>{l}</div>
          </div>
        ))}
        <div style={{ width:1, background:'#333', height:40 }} />
        <div style={{ fontFamily:MONO, fontSize:9, color:'#777', lineHeight:1.6 }}>
          {research.total_queries || 0} live web queries across news, MCA, eCourts &amp; sector databases. Every finding has a verifiable source URL.
        </div>
      </div>

      {/* Flags */}
      {flags.length === 0 && (
        <Card><p style={{ fontFamily:MONO, fontSize:10, color:GRY }}>No significant risk flags identified through research.</p></Card>
      )}
      {flags.map((f,i) => (
        <div key={i} style={{ background:WHT, border:`1.5px solid ${BOR}`, borderLeft:`4px solid ${sevColor(f.severity)}` }}>
          <div style={{ padding:'14px 18px', borderBottom:`1px solid ${BOR}` }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:8 }}>
              <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                <span style={{ fontFamily:MONO, fontSize:8.5, letterSpacing:1.5, padding:'2px 8px', background:sevColor(f.severity)+'18', color:sevColor(f.severity), border:`1px solid ${sevColor(f.severity)}44` }}>{f.severity}</span>
                <span style={{ fontFamily:MONO, fontSize:8.5, color:GRY, textTransform:'uppercase', letterSpacing:1 }}>{f.type}</span>
              </div>
              <span style={{ fontFamily:MONO, fontSize:9, color:sevColor(f.severity), fontWeight:600 }}>{parseFloat(f.score_impact||0).toFixed(1)} pts</span>
            </div>
            <div style={{ fontSize:13, fontWeight:600, color:BLK, marginBottom:6 }}>{f.title}</div>
            <div style={{ fontSize:11, color:GRY, lineHeight:1.65 }}>{f.description}</div>
          </div>
          <div style={{ padding:'9px 18px', background:LIG, display:'flex', justifyContent:'space-between' }}>
            <div style={{ display:'flex', gap:16 }}>
              <span style={{ fontFamily:MONO, fontSize:8.5, color:GRY }}>Source: <strong style={{ color:BLK }}>{f.source}</strong></span>
              {f.date && <span style={{ fontFamily:MONO, fontSize:8.5, color:GRY }}>{f.date}</span>}
            </div>
            {f.source_url && (
              <a href={f.source_url} target="_blank" rel="noreferrer"
                style={{ fontFamily:MONO, fontSize:8.5, color:GRY, textDecoration:'underline' }}>
                View Source
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export function FiveCsTab({ data }) {
  const scoring = data?.scoring || {}
  const pillars = scoring.pillars || {}

  return (
    <div>
      {/* Composite header */}
      <div style={{ background:'#111', padding:'12px 18px', marginBottom:16, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <div>
          <div style={{ fontFamily:MONO, fontSize:8.5, color:'#555', letterSpacing:2, textTransform:'uppercase', marginBottom:3 }}>Composite Score</div>
          <div style={{ fontFamily:MONO, fontSize:24, fontWeight:700, color: scoreColor((scoring.composite_score||0)/10) }}>
            {scoring.composite_score || 0}<span style={{ fontSize:13, color:'#555', marginLeft:4 }}>/ 100</span>
          </div>
        </div>
        <div style={{ textAlign:'right' }}>
          <div style={{ fontFamily:MONO, fontSize:8.5, color:'#555', letterSpacing:2, textTransform:'uppercase', marginBottom:3 }}>Decision</div>
          <div style={{ fontFamily:MONO, fontSize:13, fontWeight:700, color: decColor(scoring.decision) }}>{scoring.decision}</div>
        </div>
      </div>

      {/* Pillars */}
      {Object.entries(pillars).map(([name, pillar], i) => {
        const raw     = pillar.raw_score || 0
        const contrib = pillar.weighted_contribution || 0
        const barW    = (raw/10)*100
        return (
          <div key={name} style={{ background:WHT, border:`1.5px solid ${BOR}`, borderTop: i>0?'none':undefined, padding:'16px 18px' }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:10 }}>
              <div>
                <div style={{ display:'flex', gap:10, alignItems:'center', marginBottom:4 }}>
                  <span style={{ fontSize:12, fontWeight:600, color:BLK }}>{name}</span>
                  <span style={{ fontFamily:MONO, fontSize:8.5, color:GRY }}>Weight: {pillar.weight_pct}%</span>
                </div>
                <div style={{ fontFamily:MONO, fontSize:8.5, color:GRY }}>
                  {pillar.score_lines?.length || 0} factors assessed
                </div>
              </div>
              <div style={{ textAlign:'right', flexShrink:0, marginLeft:16 }}>
                <div style={{ fontFamily:MONO, fontSize:20, fontWeight:700, color:scoreColor(raw) }}>{raw.toFixed(1)}</div>
                <div style={{ fontFamily:MONO, fontSize:8.5, color:GRY }}>+{contrib.toFixed(1)} pts</div>
              </div>
            </div>
            <div style={{ height:6, background:LIG, border:`1px solid ${BOR}`, overflow:'hidden' }}>
              <div style={{ height:'100%', width:`${barW}%`, background:scoreColor(raw), transition:'width 0.4s ease' }} />
            </div>
            {/* Score lines */}
            {(pillar.score_lines||[]).filter(l => l.adjustment !== 0 || l.base_score > 0).map((l,j) => (
              <div key={j} style={{ display:'flex', justifyContent:'space-between', padding:'6px 0', borderBottom:`1px solid ${LIG}` }}>
                <div>
                  <div style={{ fontSize:10, fontWeight:500, color:BLK, marginBottom:2 }}>{l.sub_factor}</div>
                  <div style={{ fontFamily:MONO, fontSize:8.5, color:GRY }}>{l.data_point}</div>
                </div>
                <div style={{ textAlign:'right', flexShrink:0, marginLeft:12 }}>
                  <div style={{ fontFamily:MONO, fontSize:10, fontWeight:600, color: l.adjustment < 0 ? RED : GRN }}>
                    {l.adjustment !== 0 ? `${l.adjustment > 0 ? '+' : ''}${l.adjustment}` : `${l.base_score}`}
                  </div>
                  <div style={{ fontFamily:MONO, fontSize:8, color:GRY, maxWidth:120, textAlign:'right' }}>{l.source}</div>
                </div>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

export function OfficerPortal({ data }) {
  const [adj, setAdj] = useState({
    factory_utilization_pct: 70,
    collateral_verified: true,
    management_responsiveness: 'adequate',
    machinery_condition: 'good',
    inventory_level: 'normal',
    factory_activity: 'full',
    contradictions_noted: false,
    macro_outlook: 'neutral',
    notes: '',
  })
  const [submitted, setSubmitted] = useState(false)
  const [loading,   setLoading]   = useState(false)
  const { api } = require('../api/client') // dynamic to avoid circular

  const inp    = { width:'100%', border:`1.5px solid ${BOR}`, padding:'8px 12px', fontSize:11, background:LIG, color:BLK }
  const lbl    = { display:'block', fontFamily:MONO, fontSize:8.5, letterSpacing:2, textTransform:'uppercase', color:GRY, marginBottom:6 }
  const selOpt = { ...inp, cursor:'pointer', marginBottom:14 }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      await fetch(`http://localhost:8000/api/qualitative`, {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        body: JSON.stringify({ analysis_id: data.analysis_id, ...adj }),
      })
      setSubmitted(true)
    } catch(e) { console.error(e) }
    finally { setLoading(false) }
  }

  return (
    <div>
      {submitted && (
        <div style={{ background:'#f0fdf4', border:`1.5px solid ${GRN}`, padding:'10px 16px', marginBottom:16 }}>
          <span style={{ fontFamily:MONO, fontSize:9, color:GRN }}>Observations submitted. Score has been adjusted accordingly.</span>
        </div>
      )}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14 }}>
        {/* Site visit */}
        <div style={{ background:WHT, border:`1.5px solid ${BOR}`, padding:18 }}>
          <div className="section-label">Site Visit Observations</div>

          <label style={lbl}>Factory Utilization: {adj.factory_utilization_pct}%</label>
          <input type="range" min={0} max={100} value={adj.factory_utilization_pct}
            onChange={e => setAdj(a => ({ ...a, factory_utilization_pct: Number(e.target.value) }))}
            style={{ width:'100%', marginBottom:4, accentColor:BLK }} />
          <div style={{ display:'flex', justifyContent:'space-between', fontFamily:MONO, fontSize:8, color:GRY, marginBottom:14 }}>
            <span>0%</span>
            <span style={{ color: adj.factory_utilization_pct < 50 ? RED : adj.factory_utilization_pct < 70 ? AMB : GRN, fontWeight:600 }}>
              {adj.factory_utilization_pct < 50 ? 'Capacity −1.5 pts' : adj.factory_utilization_pct < 70 ? 'Capacity −0.5 pts' : 'No adjustment'}
            </span>
            <span>100%</span>
          </div>

          <label style={lbl}>Collateral Verified</label>
          <div style={{ display:'flex', gap:8, marginBottom:14 }}>
            {[true,false].map(v => (
              <button key={String(v)} onClick={() => setAdj(a=>({...a,collateral_verified:v}))}
                style={{ flex:1, padding:'8px', border:`1.5px solid ${adj.collateral_verified===v ? BLK : BOR}`, background: adj.collateral_verified===v ? BLK : LIG, color: adj.collateral_verified===v ? '#fff' : GRY, fontFamily:MONO, fontSize:9, letterSpacing:1, cursor:'pointer' }}>
                {v ? 'VERIFIED' : 'NOT FOUND'}
              </button>
            ))}
          </div>

          <label style={lbl}>Factory Activity</label>
          <select value={adj.factory_activity} onChange={e=>setAdj(a=>({...a,factory_activity:e.target.value}))} style={selOpt}>
            {['full','partial','minimal','shut'].map(o=><option key={o}>{o}</option>)}
          </select>

          <label style={lbl}>Inventory Level</label>
          <select value={adj.inventory_level} onChange={e=>setAdj(a=>({...a,inventory_level:e.target.value}))} style={{...selOpt,marginBottom:0}}>
            {['normal','low','high','very high'].map(o=><option key={o}>{o}</option>)}
          </select>
        </div>

        {/* Interview */}
        <div style={{ background:WHT, border:`1.5px solid ${BOR}`, padding:18 }}>
          <div className="section-label">Management Interview</div>

          <label style={lbl}>Management Responsiveness</label>
          <select value={adj.management_responsiveness} onChange={e=>setAdj(a=>({...a,management_responsiveness:e.target.value}))} style={selOpt}>
            {[['cooperative','Cooperative'],['adequate','Adequate'],['evasive','Evasive'],['hostile','Hostile']].map(([v,l])=>(
              <option key={v} value={v}>{l}</option>
            ))}
          </select>

          <label style={lbl}>Machinery Condition</label>
          <select value={adj.machinery_condition} onChange={e=>setAdj(a=>({...a,machinery_condition:e.target.value}))} style={selOpt}>
            {['new','good','aged','defunct'].map(o=><option key={o}>{o}</option>)}
          </select>

          <label style={lbl}>Contradictions Noted</label>
          <div style={{ display:'flex', gap:8, marginBottom:14 }}>
            {[false,true].map(v=>(
              <button key={String(v)} onClick={()=>setAdj(a=>({...a,contradictions_noted:v}))}
                style={{ flex:1, padding:'8px', border:`1.5px solid ${adj.contradictions_noted===v ? BLK : BOR}`, background: adj.contradictions_noted===v ? BLK : LIG, color: adj.contradictions_noted===v ? '#fff' : GRY, fontFamily:MONO, fontSize:9, letterSpacing:1, cursor:'pointer' }}>
                {v ? 'YES' : 'NONE'}
              </button>
            ))}
          </div>

          <label style={lbl}>Officer Notes</label>
          <textarea value={adj.notes} onChange={e=>setAdj(a=>({...a,notes:e.target.value}))}
            rows={4} placeholder="e.g. Factory operating at 40% capacity. Several sections locked..."
            style={{ ...inp, resize:'vertical', fontSize:10, lineHeight:1.6 }} />
        </div>
      </div>

      <div style={{ marginTop:14, background:WHT, border:`1.5px solid ${BOR}`, padding:'12px 18px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <div style={{ fontFamily:MONO, fontSize:9, color:GRY }}>
          Score adjustments are locked into the CAM upon submission.
        </div>
        <button onClick={handleSubmit} disabled={loading}
          style={{ background:BLK, color:'#fff', border:'none', padding:'9px 22px', fontFamily:MONO, fontSize:9, letterSpacing:2, textTransform:'uppercase', cursor:'pointer', opacity: loading ? 0.5 : 1 }}>
          {loading ? 'Submitting...' : 'Lock Observations'}
        </button>
      </div>
    </div>
  )
}