"""Build the self-contained Undertow demo page.

Reads backtest/output/results.json and bakes it into demo/index.html as inline data, so the page
opens straight from disk (file://) with no server and no network. Charts are rendered with inline
SVG via vanilla JS — zero external dependencies.

    python demo/build_demo.py
"""
from __future__ import annotations
import os
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(ROOT, "..", "backtest", "output", "results.json")
OUT = os.path.join(ROOT, "index.html")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Undertow — positioning-stress strategy</title>
<style>
  :root{--bg:#06141d;--bg2:#0b2231;--ink:#e8f4f8;--mut:#7fa6b8;--teal:#19c3c8;--gold:#f7931a;
        --red:#ff5d6c;--blue:#3a9bdc;--grid:#15323f;--card:#0e2632;}
  *{box-sizing:border-box}
  body{margin:0;background:linear-gradient(180deg,#06141d,#04101a 60%);color:var(--ink);
       font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:1080px;margin:0 auto;padding:32px 20px 64px}
  header h1{font-size:46px;letter-spacing:.18em;margin:0;font-weight:800;
            background:linear-gradient(90deg,var(--teal),var(--blue));-webkit-background-clip:text;
            background-clip:text;color:transparent}
  header p{color:var(--mut);margin:.3em 0 0;font-size:17px;max-width:760px}
  .tag{display:inline-block;margin-top:10px;font-size:12px;color:var(--teal);border:1px solid #16424f;
       border-radius:20px;padding:3px 12px}
  .grid{display:grid;gap:18px;margin-top:26px}
  .row2{grid-template-columns:1fr 1fr}.row3{grid-template-columns:repeat(3,1fr)}
  @media(max-width:760px){.row2,.row3{grid-template-columns:1fr}}
  .card{background:var(--card);border:1px solid #143240;border-radius:14px;padding:20px}
  .card h2{margin:0 0 4px;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut)}
  .big{font-size:30px;font-weight:700}
  .sel{margin:6px 0 0;background:#0a1e29;color:var(--ink);border:1px solid #1b3d4b;border-radius:8px;
       padding:6px 10px;font-size:14px}
  .badge{display:inline-block;padding:5px 12px;border-radius:8px;font-weight:700;font-size:14px}
  .reading{font-size:22px;font-weight:700;margin-top:8px}
  table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}
  th,td{text-align:right;padding:8px 6px;border-bottom:1px solid var(--grid)}
  th:first-child,td:first-child{text-align:left}
  .win{color:var(--teal);font-weight:700}.lose{color:var(--mut)}
  .legend span{display:inline-flex;align-items:center;gap:6px;margin-right:16px;font-size:13px;color:var(--mut)}
  .sw{width:14px;height:3px;display:inline-block;border-radius:2px}
  .dcard{background:#0a1e29;border:1px solid #143240;border-radius:10px;padding:14px}
  .dcard .d{color:var(--mut);font-size:12px}.dcard .s{font-size:22px;font-weight:700}
  .note{color:var(--mut);font-size:13px;margin-top:8px}
  footer{color:var(--mut);font-size:12.5px;margin-top:34px;border-top:1px solid var(--grid);padding-top:16px}
  a{color:var(--teal)}
  .kpi{font-size:13px;color:var(--mut)}.kpi b{color:var(--ink);font-size:15px}
</style></head>
<body><div class="wrap">
<header>
  <h1>UNDERTOW</h1>
  <p>The edge is the gap between what the crowd <em>feels</em> (surface sentiment) and how it is
     <em>positioned</em> (the undertow beneath) — read through the lens of market regime.</p>
  <span class="tag">Powered by CoinMarketCap · Agent Hub (MCP · x402 · Skill Hub)</span>
</header>

<div class="grid row3">
  <div class="card">
    <h2>Positioning stress · S</h2>
    <select id="asset" class="sel"></select>
    <div id="dial"></div>
    <div id="reading" class="reading"></div>
    <div id="components" class="note"></div>
  </div>
  <div class="card">
    <h2>Regime · R</h2>
    <div id="regime"></div>
    <div id="surface" class="note" style="margin-top:14px"></div>
    <div id="undertow" class="note"></div>
    <div id="decision" style="margin-top:14px"></div>
  </div>
  <div class="card">
    <h2>Out-of-sample edge</h2>
    <div id="kpis"></div>
    <div class="note" id="kpinote"></div>
  </div>
</div>

<div class="grid" style="margin-top:18px">
  <div class="card">
    <h2>Walk-forward equity — Undertow vs benchmarks (rebased to 1.0)</h2>
    <div class="legend" id="legend"></div>
    <div id="chart"></div>
    <div class="note" id="chartnote"></div>
  </div>
</div>

<div class="grid" style="margin-top:18px">
  <div class="card">
    <h2>Out-of-sample metrics · walk-forward window</h2>
    <table id="mtable"></table>
    <div class="note">Headline OOS is the continuous walk-forward (weights re-tuned on expanding
      train windows only). Undertow more than halves max drawdown and beats the naive Fear &amp; Greed
      contrarian decisively; over a post-cycle-top window it trades some raw return for far lower
      drawdown (higher Calmar). Over the full cycle its Sharpe beats buy &amp; hold.</div>
  </div>
</div>

<div class="grid" style="margin-top:18px">
  <div class="card">
    <h2>Annotated historical divergences (BTC)</h2>
    <div class="grid row3" id="divs" style="margin-top:10px"></div>
    <div class="note">Days where the stress score S was extreme and the next 14 days reversed the
      crowd — the pattern Undertow is built to harvest.</div>
  </div>
</div>

<footer id="footer"></footer>
</div>
<script>const DATA = /*DATA*/;</script>
<script>
const fmtP=x=>x==null?"—":(x*100).toFixed(1)+"%";
const f2=x=>x==null?"—":(+x).toFixed(2);
const $=id=>document.getElementById(id);

// ---------- Stress dial ----------
function dial(S){
  const w=240,h=140,cx=120,cy=130,r=100, lo=-3,hi=3, cl=Math.max(lo,Math.min(hi,S));
  const a=Math.PI*(1-(cl-lo)/(hi-lo)); // pi..0 left->right
  const nx=cx+r*Math.cos(a), ny=cy-r*Math.sin(a);
  const arc=(f,t,c)=>{const a0=Math.PI*(1-(f-lo)/(hi-lo)),a1=Math.PI*(1-(t-lo)/(hi-lo));
    const x0=cx+r*Math.cos(a0),y0=cy-r*Math.sin(a0),x1=cx+r*Math.cos(a1),y1=cy-r*Math.sin(a1);
    return `<path d="M${x0} ${y0} A${r} ${r} 0 0 1 ${x1} ${y1}" stroke="${c}" stroke-width="14" fill="none"/>`;};
  return `<svg viewBox="0 0 ${w} ${h}" width="100%">
    ${arc(-3,-1,'#3a9bdc')}${arc(-1,1,'#2b6f63')}${arc(1,3,'#ff5d6c')}
    <line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" stroke="#e8f4f8" stroke-width="3"/>
    <circle cx="${cx}" cy="${cy}" r="5" fill="#e8f4f8"/>
    <text x="14" y="135" fill="#3a9bdc" font-size="11">FEAR</text>
    <text x="200" y="135" fill="#ff5d6c" font-size="11">FROTH</text>
    <text x="${cx}" y="70" fill="#e8f4f8" font-size="30" font-weight="700" text-anchor="middle">${S.toFixed(2)}</text>
  </svg>`;
}
function renderAsset(sym){
  const c=DATA.current[sym]; if(!c)return;
  $("dial").innerHTML=dial(c.S);
  const rd=Math.abs(c.S)>=1.5?(c.S>0?"EUPHORIC":"CAPITULATION"):Math.abs(c.S)>=0.5?(c.S>0?"FROTHY":"FEARFUL"):"NEUTRAL";
  const col=c.S>0.5?'#ff5d6c':c.S<-0.5?'#3a9bdc':'#7fa6b8';
  $("reading").innerHTML=`<span style="color:${col}">${rd}</span>`;
  $("components").innerHTML=`z(F&amp;G) ${f2(c.z_fng)} · z(funding) ${f2(c.z_funding)} · z(stretch) ${f2(c.z_stretch)} &nbsp; <span style="color:#7fa6b8">(as of ${c.date})</span>`;
  const tcol=c.regime==='TREND'?'#19c3c8':'#f7931a', bcol=c.macro_trend==='bull'?'#19c3c8':'#ff5d6c';
  $("regime").innerHTML=`<span class="badge" style="background:#0a2a30;color:${tcol};border:1px solid ${tcol}">${c.regime}</span>
     <span class="badge" style="background:#0a2030;color:${bcol};border:1px solid ${bcol};margin-left:8px">${c.macro_trend.toUpperCase()} trend</span>
     <div class="note" style="margin-top:8px">Efficiency ratio ${f2(c.er)} · Skill-Hub regime: <b style="color:#e8f4f8">${DATA._hub_regime||'mixed_transition'}</b></div>`;
  $("surface").innerHTML=`<b style="color:#e8f4f8">Surface</b> — Fear &amp; Greed ${c.fng}`;
  $("undertow").innerHTML=`<b style="color:#e8f4f8">Undertow</b> — funding z ${f2(c.z_funding)} · stretch z ${f2(c.z_stretch)}`;
  const st=c.target_position>=0.5?'LONG':c.target_position>0.05?'REDUCE':c.target_position<-0.05?'SHORT':'FLAT';
  $("decision").innerHTML=`<span class="kpi">Spec stance</span> <span class="big" style="font-size:22px">${st}</span>
     <span class="kpi">· target position ${f2(c.target_position)}</span>`;
}

// ---------- Equity chart ----------
function chart(){
  const e=DATA.equity_walk_forward, dates=e.dates, n=dates.length;
  const series=[["strategy","Undertow","#19c3c8",3],["btc_bh","BTC buy&hold","#f7931a",1.6],
                ["basket_bh","Basket buy&hold","#5f7d8c",1.4],["fng_contrarian","F&G contrarian","#ff5d6c",1.4]];
  let mn=Infinity,mx=-Infinity;
  series.forEach(s=>e[s[0]].forEach(v=>{if(v<mn)mn=v;if(v>mx)mx=v;}));
  const W=1020,H=340,pl=46,pr=14,pt=14,pb=26, iw=W-pl-pr, ih=H-pt-pb;
  const sx=i=>pl+iw*i/(n-1), sy=v=>pt+ih*(1-(v-mn)/(mx-mn));
  let g="";
  for(let k=0;k<=4;k++){const v=mn+(mx-mn)*k/4,y=sy(v);
    g+=`<line x1="${pl}" y1="${y}" x2="${W-pr}" y2="${y}" stroke="#15323f"/><text x="6" y="${y+4}" fill="#7fa6b8" font-size="11">${v.toFixed(2)}x</text>`;}
  // year ticks
  let prev="";
  dates.forEach((d,i)=>{const y=d.slice(0,4); if(y!==prev){prev=y; const x=sx(i);
    g+=`<line x1="${x}" y1="${pt}" x2="${x}" y2="${H-pb}" stroke="#0f2733"/><text x="${x+3}" y="${H-10}" fill="#7fa6b8" font-size="11">${y}</text>`;}});
  let paths="";
  series.forEach(s=>{const pts=e[s[0]].map((v,i)=>`${sx(i).toFixed(1)},${sy(v).toFixed(1)}`).join(" ");
    paths+=`<polyline points="${pts}" fill="none" stroke="${s[2]}" stroke-width="${s[3]}" opacity="0.95"/>`;});
  $("chart").innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%">${g}${paths}</svg>`;
  $("legend").innerHTML=series.map(s=>`<span><i class="sw" style="background:${s[2]}"></i>${s[1]}</span>`).join("");
  $("chartnote").innerHTML=`Window ${dates[0]} → ${dates[n-1]} · ${n} days. All series rebased to 1.0 at window start.`;
}

// ---------- Metrics table ----------
function table(){
  const m=DATA.metrics, rows=[["strategy_walk_forward","Undertow"],["btc_buy_hold_wf","BTC buy&hold"],
    ["basket_buy_hold_wf","Basket buy&hold"],["fng_contrarian_wf","Fear&Greed contrarian"]];
  const cols=[["total_return","Total",fmtP],["cagr","CAGR",fmtP],["sharpe","Sharpe",f2],
    ["sortino","Sortino",f2],["max_drawdown","Max DD",fmtP],["calmar","Calmar",f2]];
  let h=`<tr><th>Strategy</th>${cols.map(c=>`<th>${c[1]}</th>`).join("")}</tr>`;
  rows.forEach(r=>{const d=m[r[0]]||{};const win=r[0]==="strategy_walk_forward";
    h+=`<tr><td class="${win?'win':''}">${r[1]}</td>${cols.map(c=>{
      const cls=(c[0]==='max_drawdown'&&win)||(c[0]==='calmar'&&win)?'win':'';
      return `<td class="${cls}">${c[2](d[c[0]])}</td>`;}).join("")}</tr>`;});
  $("mtable").innerHTML=h;
}

// ---------- KPIs ----------
function kpis(){
  const s=DATA.metrics.strategy_walk_forward, b=DATA.metrics.btc_buy_hold_wf, f=DATA.metrics.strategy_full;
  $("kpis").innerHTML=`
    <div class="big" style="color:#19c3c8">${(s.max_drawdown*100).toFixed(0)}%</div>
    <div class="kpi">max drawdown vs BTC <b>${(b.max_drawdown*100).toFixed(0)}%</b> (≈ half)</div>
    <div style="margin-top:12px"><span class="kpi">Calmar</span> <b class="win">${f2(s.calmar)}</b>
       <span class="kpi">vs BTC ${f2(b.calmar)}</span></div>
    <div><span class="kpi">Full-cycle Sharpe</span> <b class="win">${f2(f.sharpe)}</b>
       <span class="kpi">vs BTC ${f2(DATA.metrics.btc_buy_hold_full.sharpe)}</span></div>`;
  $("kpinote").innerHTML="Costs + slippage modeled · no leverage · weights tuned on train only.";
}

// ---------- Divergences ----------
function divs(){
  $("divs").innerHTML=(DATA.divergence_examples||[]).map(d=>{
    const up=d.fwd_14d_return>0,col=up?'#19c3c8':'#ff5d6c';
    return `<div class="dcard"><div class="d">${d.date} · ${d.regime}</div>
      <div class="s" style="color:${d.S>0?'#ff5d6c':'#3a9bdc'}">S ${d.S.toFixed(2)}</div>
      <div class="d">${d.note}</div>
      <div style="color:${col};font-weight:700;margin-top:4px">14d: ${fmtP(d.fwd_14d_return)}</div></div>`;}).join("");
}

// ---------- init ----------
const sel=$("asset");
Object.keys(DATA.current).forEach(s=>{const o=document.createElement("option");o.value=s;o.textContent=s.replace("USDT","");sel.appendChild(o);});
sel.onchange=()=>renderAsset(sel.value);
sel.value=Object.keys(DATA.current)[0];
renderAsset(sel.value); chart(); table(); kpis(); divs();
const meta=DATA.meta;
$("footer").innerHTML=`Data window ${meta.data_window[0]} → ${meta.data_window[1]} · assets ${meta.assets_used.map(a=>a.replace('USDT','')).join(', ')}
  · frozen weights F&amp;G ${meta.frozen_weights.w_fng}/funding ${meta.frozen_weights.w_funding}/stretch ${meta.frozen_weights.w_stretch}
  · cost ${meta.cost_bps_one_way}bps/side. <br/>Research artifact, not investment advice. Backtested core = Fear &amp; Greed + funding + price-stretch;
  open-interest, social/KOL and on-chain flow are live-only enhancements (never backtested with fabricated history).`;
</script>
</body></html>
"""


def main():
    results = json.load(open(RESULTS))
    # carry the captured live Skill-Hub regime label into the page
    try:
        fx = json.load(open(os.path.join(ROOT, "..", "agent_hub", "fixtures", "detect_market_regime_30d.json")))
        results["_hub_regime"] = fx["result"]["data"]["report"]["market_regime"]
    except Exception:
        results["_hub_regime"] = "mixed_transition"
    html = TEMPLATE.replace("/*DATA*/", json.dumps(results))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {os.path.abspath(OUT)} ({os.path.getsize(OUT)//1024} KB)")


if __name__ == "__main__":
    main()
