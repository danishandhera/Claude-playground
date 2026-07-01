import { useState } from "react";
import { P, F, CSS_VARS } from "./theme.js";
import { LOCATIONS } from "./data/locations.js";
import { scoreMatch } from "./scoring.js";
import { useCaregivers, useCenters, useProducts } from "./data/hooks.js";

const TOTAL = 7; // steps in the Find-a-Carer intake wizard

/* Hoisted out of FindPage so it is not redefined every render (avoids remounts). */
const Card = ({ sel, onClick, title, sub, desc, small = false }) => (
  <div onClick={onClick} style={{border:sel?`1.5px solid ${P.sage}`:`1px solid ${P.sand}`,borderRadius:12,
    padding:small?"10px 12px":"14px 16px",cursor:"pointer",background:sel?P.sageL:P.white,transition:"all .15s"}}>
    <div style={{fontFamily:F.display,fontSize:small?13:14,fontWeight:600,color:sel?P.sage:P.ink,marginBottom:2}}>{title}</div>
    {sub&&<div style={{fontFamily:F.body,fontSize:11,color:P.bark,marginBottom:3}}>{sub}</div>}
    {desc&&<div style={{fontFamily:F.body,fontSize:11,color:sel?P.sage:P.bark}}>{desc}</div>}
  </div>
);

function Stars({n,size=14}){
  return <span style={{color:P.gold,fontSize:size,lineHeight:1,fontFamily:F.body}}>
    {"★".repeat(Math.floor(n))}{"☆".repeat(5-Math.floor(n))}
  </span>;
}

function Tag({children,color=P.sage,bg=P.sageL}){
  return <span style={{display:"inline-block",background:bg,color,fontSize:10,fontFamily:F.body,
    fontWeight:700,padding:"3px 9px",borderRadius:20,letterSpacing:"0.06em"}}>{children}</span>;
}

function Btn({children,onClick,variant="primary",small=false,style={}}){
  const base={border:"none",cursor:"pointer",fontFamily:F.body,fontWeight:700,borderRadius:8,
    letterSpacing:"0.04em",transition:"all .2s",...style};
  const variants={
    primary:{background:P.sage,color:P.white,padding:small?"8px 16px":"12px 28px",fontSize:small?12:14},
    secondary:{background:"transparent",color:P.bark,border:`1px solid ${P.sand}`,padding:small?"8px 14px":"11px 24px",fontSize:small?12:14},
    blush:{background:P.blush,color:P.white,padding:small?"8px 16px":"12px 28px",fontSize:small?12:14},
    gold:{background:P.gold,color:P.white,padding:small?"8px 16px":"12px 28px",fontSize:small?12:14},
  };
  return <button onClick={onClick} style={{...base,...variants[variant]}}>{children}</button>;
}

/* ─── CALENDAR PICKER ─────────────────────────────────────────────────────── */
function CalendarPicker({value,onChange}){
  const today=new Date(); today.setHours(0,0,0,0);
  const [vm,setVm]=useState(()=>{
    if(value){const v=new Date(value);v.setDate(1);return v;}
    const d=new Date();d.setDate(1);return d;
  });
  const sel=value?new Date(value):null;
  const wS=sel?new Date(sel.getTime()-14*86400000):null;
  const wE=sel?new Date(sel.getTime()+14*86400000):null;
  const y=vm.getFullYear(),m=vm.getMonth();
  const fd=(new Date(y,m,1).getDay()+6)%7;
  const dim=new Date(y,m+1,0).getDate();
  const MONTHS=["January","February","March","April","May","June","July","August","September","October","November","December"];
  const cells=[];
  for(let i=0;i<fd;i++) cells.push(null);
  for(let d=1;d<=dim;d++) cells.push(new Date(y,m,d));
  const isSel=d=>sel&&d&&d.toDateString()===sel.toDateString();
  const inW=d=>d&&wS&&wE&&d>=wS&&d<=wE;
  const isPast=d=>d&&d<today;

  return(
    <div style={{background:P.white,border:`1px solid ${P.sand}`,borderRadius:14,padding:20,maxWidth:340}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:16}}>
        <button onClick={()=>setVm(new Date(y,m-1,1))} style={{background:"none",border:"none",cursor:"pointer",fontSize:20,color:P.bark,padding:"2px 8px",lineHeight:1}}>‹</button>
        <span style={{fontFamily:F.display,fontWeight:600,fontSize:15,color:P.ink}}>{MONTHS[m]} {y}</span>
        <button onClick={()=>setVm(new Date(y,m+1,1))} style={{background:"none",border:"none",cursor:"pointer",fontSize:20,color:P.bark,padding:"2px 8px",lineHeight:1}}>›</button>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(7,1fr)",gap:2,marginBottom:4}}>
        {["M","T","W","T","F","S","S"].map((d,i)=>(
          <div key={i} style={{textAlign:"center",fontSize:10,color:P.bark,fontFamily:F.body,padding:"3px 0"}}>{d}</div>
        ))}
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(7,1fr)",gap:2}}>
        {cells.map((d,i)=>{
          if(!d) return <div key={i}/>;
          const past=isPast(d),sel2=isSel(d),win=inW(d);
          return(
            <button key={i} onClick={()=>!past&&onChange(d.toISOString().split("T")[0])}
              style={{border:"none",borderRadius:6,padding:"7px 0",fontSize:12,cursor:past?"not-allowed":"pointer",
                background:sel2?P.sage:win?P.sageM:"transparent",
                color:sel2?P.white:win?P.ink:past?P.sand:P.ink,
                fontWeight:sel2?"bold":"normal",fontFamily:F.body}}>
              {d.getDate()}
            </button>
          );
        })}
      </div>
      {sel&&(
        <div style={{marginTop:14,padding:"10px 14px",background:P.sageL,borderRadius:8,fontSize:12,fontFamily:F.body,color:P.sage,lineHeight:1.6}}>
          <strong>Due date: {sel.toLocaleDateString("en-GB",{day:"numeric",month:"long",year:"numeric"})}</strong><br/>
          Window: {wS.toLocaleDateString("en-GB",{day:"numeric",month:"short"})} – {wE.toLocaleDateString("en-GB",{day:"numeric",month:"short"})}<br/>
          <span style={{color:P.bark}}>We recommend booking at least 6 weeks before your earliest window date.</span>
        </div>
      )}
    </div>
  );
}

/* ─── NAV ─────────────────────────────────────────────────────────────────── */
function Nav({page,setPage}){
  const tabs=[
    {id:"home",label:"Home"},
    {id:"find",label:"Find a Carer"},
    {id:"centers",label:"Wellness Centers"},
    {id:"shop",label:"Shop"},
  ];
  return(
    <header style={{background:P.white,borderBottom:`1px solid ${P.sand}`,position:"sticky",top:0,zIndex:100,
      boxShadow:"0 2px 12px rgba(107,143,113,0.08)"}}>
      <div style={{maxWidth:960,margin:"0 auto",padding:"0 24px",display:"flex",alignItems:"center",justifyContent:"space-between",height:64}}>
        <button onClick={()=>setPage("home")} style={{background:"none",border:"none",cursor:"pointer",display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:36,height:36,borderRadius:"50%",background:`linear-gradient(135deg,${P.sage},${P.blush})`,
            display:"flex",alignItems:"center",justifyContent:"center",fontSize:16}}>🌿</div>
          <div>
            <div style={{fontFamily:F.display,fontSize:18,fontWeight:700,color:P.ink,lineHeight:1.1}}>firsttimemoms</div>
            <div style={{fontFamily:F.body,fontSize:10,color:P.bark,letterSpacing:"0.06em",lineHeight:1}}>POSTNATAL CARE PLATFORM</div>
          </div>
        </button>
        <nav style={{display:"flex",gap:4}}>
          {tabs.map(t=>(
            <button key={t.id} onClick={()=>setPage(t.id)}
              style={{background:page===t.id?P.sageL:"none",color:page===t.id?P.sage:P.bark,
                border:page===t.id?`1px solid ${P.sageM}`:"1px solid transparent",
                borderRadius:8,padding:"7px 14px",fontSize:13,fontFamily:F.body,cursor:"pointer",fontWeight:page===t.id?700:400}}>
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}

/* ─── HOME PAGE ───────────────────────────────────────────────────────────── */
function HomePage({setPage}){
  return(
    <div>
      {/* Hero */}
      <div style={{background:`linear-gradient(160deg,${P.sageL} 0%,${P.blushL} 60%,${P.parchment} 100%)`,
        padding:"72px 24px 56px",textAlign:"center",borderBottom:`1px solid ${P.sand}`}}>
        <div style={{maxWidth:560,margin:"0 auto"}}>
          <div style={{fontFamily:F.body,fontSize:11,color:P.sage,letterSpacing:"0.12em",fontWeight:700,marginBottom:16}}>
            CULTURALLY-MATCHED POSTNATAL CARE IN THE UAE
          </div>
          <h1 style={{fontFamily:F.display,fontSize:44,fontWeight:700,color:P.ink,lineHeight:1.2,marginBottom:16,letterSpacing:"-0.02em"}}>
            You just had a baby.<br/><em style={{color:P.sage,fontStyle:"italic"}}>Someone's got to take care of you.</em>
          </h1>
          <p style={{fontFamily:F.body,fontSize:16,color:P.bark,lineHeight:1.75,marginBottom:32}}>
            Every culture has a name for the woman who helps a new mother through her first 40 days.
            She knows your food, your rituals, your language — and your traditions.
            We help you find her in the UAE.
          </p>
          <div style={{display:"flex",gap:12,justifyContent:"center",flexWrap:"wrap"}}>
            <Btn onClick={()=>setPage("find")}>Find a Carer →</Btn>
            <Btn onClick={()=>setPage("centers")} variant="secondary">Browse Wellness Centers</Btn>
          </div>
        </div>
      </div>

      <div style={{maxWidth:900,margin:"0 auto",padding:"0 24px"}}>

        {/* How it works */}
        <section style={{padding:"56px 0 40px"}}>
          <div style={{fontFamily:F.body,fontSize:11,color:P.sage,letterSpacing:"0.1em",fontWeight:700,marginBottom:8}}>HOW IT WORKS</div>
          <h2 style={{fontFamily:F.display,fontSize:28,fontWeight:700,color:P.ink,marginBottom:32}}>
            From search to settled — in 4 steps
          </h2>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",gap:20}}>
            {[
              {n:"01",icon:"🎯",title:"Tell us what you need",desc:"7 questions about your tradition, priorities, location, and due date."},
              {n:"02",icon:"✨",title:"See your matches",desc:"Scored by culture fit, budget, location, and availability. No guessing."},
              {n:"03",icon:"⭐",title:"Read verified reviews",desc:"Only from mothers who completed the full care cycle. No unverified ratings."},
              {n:"04",icon:"📅",title:"Pre-book with a fee",desc:"A small deposit holds her calendar around your ±2 week delivery window."},
            ].map(s=>(
              <div key={s.n} style={{background:P.white,border:`1px solid ${P.sand}`,borderRadius:14,padding:"22px 20px"}}>
                <div style={{fontSize:24,marginBottom:10}}>{s.icon}</div>
                <div style={{fontFamily:F.body,fontSize:11,color:P.blush,fontWeight:700,letterSpacing:"0.06em",marginBottom:6}}>{s.n}</div>
                <div style={{fontFamily:F.display,fontSize:16,fontWeight:600,color:P.ink,marginBottom:8}}>{s.title}</div>
                <div style={{fontFamily:F.body,fontSize:13,color:P.bark,lineHeight:1.6}}>{s.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Feature cards */}
        <section style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:16,paddingBottom:56}}>
          {[
            {icon:"🌿",title:"Find Your Carer",desc:"Matched by tradition, language, location & budget.",page:"find",label:"Start matching",color:P.sage,bg:P.sageL},
            {icon:"🏥",title:"Wellness Centers",desc:"Partner Ayurvedic centers offering home service + exclusive discounts.",page:"centers",label:"See partners",color:P.gold,bg:P.goldL},
            {icon:"🛒",title:"The Shop",desc:"Hard-to-find postnatal ingredients — sourced from origin, priced fairly.",page:"shop",label:"Browse items",color:P.blush,bg:P.blushL},
          ].map(f=>(
            <div key={f.page} style={{background:f.bg,border:`1px solid ${f.color}25`,borderRadius:14,padding:"24px 20px"}}>
              <div style={{fontSize:28,marginBottom:12}}>{f.icon}</div>
              <div style={{fontFamily:F.display,fontSize:17,fontWeight:600,color:P.ink,marginBottom:8}}>{f.title}</div>
              <div style={{fontFamily:F.body,fontSize:13,color:P.bark,lineHeight:1.6,marginBottom:16}}>{f.desc}</div>
              <Btn onClick={()=>setPage(f.page)} variant="secondary" small>{f.label} →</Btn>
            </div>
          ))}
        </section>

        {/* Reviews banner */}
        <section style={{background:`linear-gradient(135deg,${P.sage},${P.sageL})`,borderRadius:16,
          padding:"36px 32px",marginBottom:56,display:"flex",gap:32,alignItems:"center",
          border:`1px solid ${P.sageM}`,flexWrap:"wrap"}}>
          <div style={{flex:1,minWidth:200}}>
            <div style={{fontFamily:F.body,fontSize:11,color:P.sageM,letterSpacing:"0.1em",fontWeight:700,marginBottom:8}}>OUR REVIEW PROMISE</div>
            <div style={{fontFamily:F.display,fontSize:22,fontWeight:700,color:P.white,lineHeight:1.3,marginBottom:12}}>
              Reviews only from mothers who<br/>completed the full care cycle
            </div>
            <div style={{fontFamily:F.body,fontSize:14,color:P.sageL,lineHeight:1.7}}>
              We never show early or unverified ratings. A review appears only after a mother completes the full postnatal period with that carer and fills in our in-depth feedback form. You see the real picture — because that's what you deserve when choosing someone to care for you at your most vulnerable.
            </div>
          </div>
          <div style={{background:"rgba(255,255,255,0.15)",borderRadius:12,padding:"20px 24px",minWidth:180}}>
            <div style={{fontFamily:F.display,fontSize:42,fontWeight:700,color:P.white,lineHeight:1}}>4.9</div>
            <Stars n={4.9} size={18}/>
            <div style={{fontFamily:F.body,fontSize:12,color:P.sageL,marginTop:6}}>Average across 171<br/>full-cycle reviews</div>
          </div>
        </section>

        {/* Traditions */}
        <section style={{paddingBottom:64}}>
          <div style={{fontFamily:F.body,fontSize:11,color:P.sage,letterSpacing:"0.1em",fontWeight:700,marginBottom:8}}>TRADITIONS WE SUPPORT</div>
          <h2 style={{fontFamily:F.display,fontSize:24,fontWeight:700,color:P.ink,marginBottom:24}}>Every tradition. One platform.</h2>
          <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12}}>
            {[
              {icon:"🌿",name:"South Indian / Ayurvedic",sub:"Sutika Kala — 42 days"},
              {icon:"🍯",name:"Pakistani / North Indian",sub:"Sawa Mahina & Jaapa — 40 days"},
              {icon:"🍜",name:"Korean Sanhujori",sub:"산후조리 — 21–30 days"},
              {icon:"🔥",name:"Thai Yu Fai",sub:"อยู่ไฟ — 5–30 days"},
              {icon:"🌺",name:"Malay Berpantang",sub:"44 days"},
              {icon:"✨",name:"Mixed / Other",sub:"Flexible & adapts to you"},
            ].map(t=>(
              <div key={t.name} style={{background:P.white,border:`1px solid ${P.sand}`,borderRadius:10,padding:"14px 16px",cursor:"pointer"}}
                onClick={()=>setPage("find")}>
                <div style={{fontSize:20,marginBottom:6}}>{t.icon}</div>
                <div style={{fontFamily:F.display,fontSize:13,fontWeight:600,color:P.ink,marginBottom:2}}>{t.name}</div>
                <div style={{fontFamily:F.body,fontSize:11,color:P.bark}}>{t.sub}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ─── FIND PAGE (intake + results) ───────────────────────────────────────── */
const PRIORITIES=[
  {id:"cooking",label:"Traditional cooking",icon:"🍲"},
  {id:"massage",label:"Mother massage",icon:"🫙"},
  {id:"baby",label:"Baby care & massage",icon:"👶"},
  {id:"herbal",label:"Herbal remedies",icon:"🌿"},
  {id:"binding",label:"Belly binding",icon:"🩹"},
  {id:"night",label:"Night support",icon:"🌙"},
  {id:"lactation",label:"Breastfeeding",icon:"🤱"},
  {id:"religious",label:"Religious rituals",icon:"🕌"},
  {id:"household",label:"Household help",icon:"🏠"},
  {id:"emotional",label:"Emotional support",icon:"🫂"},
];
const BUDGET_OPTS=[
  {id:"<1000",label:"Under AED 1,000",sub:"Part-time / occasional"},
  {id:"1000-2000",label:"AED 1,000 – 2,000",sub:"Regular day visits"},
  {id:"2000-3000",label:"AED 2,000 – 3,000",sub:"Full-time day care"},
  {id:"3000-4000",label:"AED 3,000 – 4,000",sub:"Premium / live-in"},
  {id:">5000",label:"AED 5,000+",sub:"Top-tier specialised care"},
];
const LANGS=["Arabic","English","Hindi","Urdu","Tamil","Malayalam","Kannada","Telugu","Punjabi","Korean","Thai","Malay","Indonesian","Bengali"];

function FindPage(){
  const [step,setStep]=useState(0);
  const [ans,setAns]=useState({});
  const [done,setDone]=useState(false);
  const [city,setCity]=useState("");
  const [district,setDistrict]=useState("");
  const set=(k,v)=>setAns(a=>({...a,[k]:v}));
  const a=k=>ans[k];

  const goNext=()=>{ if(step>=TOTAL-1) setDone(true); else setStep(s=>s+1); };
  const goBack=()=>{ if(step===0) return; setStep(s=>s-1); };

  // Card is hoisted to module scope. Frame stays here because it closes over
  // goBack/goNext; hoist it (passing those as props) before adding any free-text
  // input to the wizard, to avoid remount/focus-loss.
  const Frame=({idx,title,sub,children,canGo,optional,isLast})=>(
    <div className="fade-up">
      <div style={{marginBottom:28}}>
        <div style={{height:2,background:P.sand,borderRadius:1,marginBottom:10}}>
          <div style={{height:2,width:`${Math.round(idx/TOTAL*100)}%`,background:P.sage,borderRadius:1,transition:"width .4s"}}/>
        </div>
        <div style={{display:"flex",justifyContent:"space-between"}}>
          <span style={{fontFamily:F.body,fontSize:11,color:P.bark,letterSpacing:"0.06em"}}>STEP {idx+1} OF {TOTAL}</span>
          <span style={{fontFamily:F.body,fontSize:11,color:P.bark}}>{Math.round(idx/TOTAL*100)}%</span>
        </div>
      </div>
      <h2 style={{fontFamily:F.display,fontSize:24,fontWeight:700,color:P.ink,marginBottom:6,letterSpacing:"-0.01em"}}>{title}</h2>
      <p style={{fontFamily:F.body,fontSize:14,color:P.bark,lineHeight:1.65,marginBottom:24}}>{sub}</p>
      {children}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginTop:28}}>
        <Btn onClick={goBack} variant="secondary" style={{opacity:idx===0?0.3:1,pointerEvents:idx===0?"none":"auto"}}>← Back</Btn>
        <div style={{display:"flex",gap:12,alignItems:"center"}}>
          {optional&&<button onClick={goNext} style={{background:"none",border:"none",fontSize:13,color:P.bark,cursor:"pointer",fontFamily:F.body,textDecoration:"underline"}}>Skip</button>}
          <Btn onClick={canGo?goNext:undefined} style={{opacity:canGo?1:0.4,cursor:canGo?"pointer":"not-allowed"}}>
            {isLast?"Find my matches →":"Continue →"}
          </Btn>
        </div>
      </div>
    </div>
  );

  if(done) return <ResultsView ans={ans} onReset={()=>{setStep(0);setAns({});setDone(false);}}/>;

  const steps=[
    // 0 — priorities
    <Frame key={0} idx={0} title="What matters most to you?" sub="Pick up to 3 — this shapes which skills we weight most heavily in your match." canGo={(a("priorities")||[]).length>0} isLast={false}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
        {PRIORITIES.map(p=>{
          const sel=(a("priorities")||[]).includes(p.id);
          const dis=!sel&&(a("priorities")||[]).length>=3;
          return(
            <div key={p.id} onClick={()=>!dis&&set("priorities",sel?(a("priorities")||[]).filter(x=>x!==p.id):[...(a("priorities")||[]),p.id])}
              style={{display:"flex",alignItems:"center",gap:10,border:sel?`1.5px solid ${P.sage}`:`1px solid ${P.sand}`,
                borderRadius:10,padding:"11px 14px",cursor:dis?"not-allowed":"pointer",background:sel?P.sageL:P.white,opacity:dis?0.4:1}}>
              <span style={{fontSize:18}}>{p.icon}</span>
              <span style={{fontFamily:F.body,fontSize:13,color:sel?P.sage:P.ink,fontWeight:sel?700:400}}>{p.label}</span>
            </div>
          );
        })}
      </div>
    </Frame>,

    // 1 — tradition
    <Frame key={1} idx={1} title="What background are you looking for in a caregiver?" sub="The single most important factor. A carer who knows your traditions by heart — not by explanation." canGo={!!a("tradition")} isLast={false}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
        {[
          {id:"south-indian",label:"South Indian",sub:"Tamil · Malayali · Kannada · Telugu",desc:"Ayurvedic oil massage, herbal baths, Sutika diet"},
          {id:"north-indian",label:"North Indian",sub:"Punjabi · UP · Rajasthani · Hindi belt",desc:"Panjiri, ladoo, mustard oil massage, chilla"},
          {id:"pakistani",label:"Pakistani",sub:"Punjabi · Sindhi · Urdu · Pashtun",desc:"Sawa mahina, desi ghee, Islamic birth rituals"},
          {id:"korean",label:"Korean",sub:"Korean diaspora",desc:"Sanhujori, miyeokguk, warmth protocol, total rest"},
          {id:"thai",label:"Thai",sub:"Thai diaspora",desc:"Yu Fai, herbal compress, abdominal massage"},
          {id:"malay",label:"Malay / Indonesian",sub:"Malay · Javanese",desc:"Berpantang, jamu herbs, bengkung binding"},
          {id:"mixed",label:"Mixed / Open",sub:"Multi-cultural or other",desc:"A flexible carer who adapts to your family"},
        ].map(o=><Card key={o.id} sel={a("tradition")===o.id} onClick={()=>set("tradition",o.id)} title={o.label} sub={o.sub} desc={o.desc}/>)}
      </div>
    </Frame>,

    // 2 — location
    <Frame key={2} idx={2} title="Where are you based?" sub="Carers typically work within 20–30 minutes of their home. We show who's actually nearby." canGo={!!city} isLast={false}>
      <div style={{display:"flex",flexDirection:"column",gap:14}}>
        {[
          {label:"EMIRATE / CITY", val:city, opts:Object.keys(LOCATIONS), placeholder:"Select city…",
            onChange:v=>{setCity(v);setDistrict("");set("city",v);set("district","");set("area","");}},
          city&&{label:"DISTRICT / AREA", val:district, opts:Object.keys(LOCATIONS[city]||{}), placeholder:"Select district…",
            onChange:v=>{setDistrict(v);set("district",v);set("area","");}},
          district&&{label:"COMMUNITY", val:a("area")||"", opts:LOCATIONS[city]?.[district]||[], placeholder:"Select neighbourhood…",
            onChange:v=>set("area",v)},
        ].filter(Boolean).map((f,i)=>(
          <div key={i}>
            <div style={{fontFamily:F.body,fontSize:11,color:P.bark,fontWeight:700,letterSpacing:"0.06em",marginBottom:6}}>{f.label}</div>
            <div style={{position:"relative"}}>
              <select value={f.val} onChange={e=>f.onChange(e.target.value)}
                style={{width:"100%",padding:"11px 36px 11px 14px",border:`1px solid ${P.sand}`,borderRadius:8,
                  fontSize:14,fontFamily:F.body,background:P.white,color:f.val?P.ink:P.bark}}>
                <option value="">{f.placeholder}</option>
                {f.opts.map(o=><option key={o} value={o}>{o}</option>)}
              </select>
              <span style={{position:"absolute",right:12,top:"50%",transform:"translateY(-50%)",pointerEvents:"none",color:P.bark}}>▾</span>
            </div>
          </div>
        ))}
      </div>
    </Frame>,

    // 3 — calendar
    <Frame key={3} idx={3} title="When is your baby due?" sub="Select your tentative due date. We highlight a ±2 week window since delivery dates vary — and only show carers who are free for your entire window." canGo={!!a("dueDate")} isLast={false}>
      <CalendarPicker value={a("dueDate")} onChange={v=>set("dueDate",v)}/>
    </Frame>,

    // 4 — budget
    <Frame key={4} idx={4} title="What is your monthly budget?" sub="Rates vary by experience, tradition, and whether the carer is live-in or day visits." canGo={!!a("budget")} isLast={false}>
      <div style={{display:"flex",flexDirection:"column",gap:10}}>
        {BUDGET_OPTS.map(b=>{
          const sel=a("budget")===b.id;
          return(
            <div key={b.id} onClick={()=>set("budget",b.id)}
              style={{border:sel?`1.5px solid ${P.sage}`:`1px solid ${P.sand}`,borderRadius:10,padding:"14px 18px",
                cursor:"pointer",background:sel?P.sageL:P.white,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <div>
                <div style={{fontFamily:F.display,fontSize:15,fontWeight:600,color:sel?P.sage:P.ink}}>{b.label}</div>
                <div style={{fontFamily:F.body,fontSize:12,color:P.bark,marginTop:2}}>{b.sub}</div>
              </div>
              {sel&&<span style={{color:P.sage,fontSize:18}}>✓</span>}
            </div>
          );
        })}
      </div>
    </Frame>,

    // 5 — live-in
    <Frame key={5} idx={5} title="Do you need live-in care?" sub="Korean and Malay traditions work best with live-in care. Others are equally effective with daily visits." canGo={!!a("liveIn")} isLast={false}>
      <div style={{display:"flex",flexDirection:"column",gap:10}}>
        {[
          {id:"yes",label:"Live-in preferred",sub:"Carer stays in the home for the full engagement"},
          {id:"no",label:"Daily visits",sub:"Carer comes each morning, leaves in the evening"},
          {id:"flexible",label:"Flexible",sub:"Open to either — show me all options"},
        ].map(o=><Card key={o.id} sel={a("liveIn")===o.id} onClick={()=>set("liveIn",o.id)} title={o.label} sub={o.sub}/>)}
      </div>
    </Frame>,

    // 6 — languages
    <Frame key={6} idx={6} title="Preferred language(s) for communication?" sub="Select all that apply — many families in the UAE speak multiple languages. Inter-cultural marriages are the norm here, not the exception." canGo={true} optional isLast={true}>
      <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
        {LANGS.map(l=>{
          const sel=(a("languages")||[]).includes(l);
          return(
            <div key={l} onClick={()=>set("languages",sel?(a("languages")||[]).filter(x=>x!==l):[...(a("languages")||[]),l])}
              style={{padding:"8px 16px",borderRadius:24,border:sel?`1.5px solid ${P.sage}`:`1px solid ${P.sand}`,
                background:sel?P.sageL:P.white,cursor:"pointer",fontSize:13,fontFamily:F.body,color:sel?P.sage:P.ink,fontWeight:sel?700:400}}>
              {l}
            </div>
          );
        })}
      </div>
    </Frame>,
  ];

  return <div style={{maxWidth:640,margin:"0 auto",padding:"40px 24px"}}>{steps[step]}</div>;
}

function ScoreBar({label,val}){
  const c=val>=80?P.sage:val>=60?P.gold:P.blush;
  return(
    <div style={{marginBottom:7}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
        <span style={{fontFamily:F.body,fontSize:11,color:P.bark}}>{label}</span>
        <span style={{fontFamily:F.body,fontSize:11,fontWeight:700,color:c}}>{val}%</span>
      </div>
      <div style={{height:4,background:P.sand,borderRadius:2}}>
        <div style={{height:4,width:`${val}%`,background:c,borderRadius:2,transition:"width .6s"}}/>
      </div>
    </div>
  );
}

function ResultsView({ans,onReset}){
  const {data:caregivers}=useCaregivers();
  const scored=caregivers.map(c=>({c,s:scoreMatch(c,ans)})).sort((a,b)=>b.s.total-a.s.total).slice(0,4);
  const [expanded,setExpanded]=useState(null);

  return(
    <div style={{maxWidth:720,margin:"0 auto",padding:"40px 24px"}} className="fade-up">
      <div style={{fontFamily:F.body,fontSize:11,color:P.sage,letterSpacing:"0.1em",fontWeight:700,marginBottom:4}}>YOUR MATCHES</div>
      <h2 style={{fontFamily:F.display,fontSize:26,fontWeight:700,color:P.ink,marginBottom:6}}>Your top {scored.length} matches</h2>
      <p style={{fontFamily:F.body,fontSize:13,color:P.bark,marginBottom:28,lineHeight:1.6}}>
        Scored by: tradition fit (40%) · budget (20%) · location (20%) · availability (15%) · live-in preference (5%) · language bonus.
      </p>

      {scored.map(({c,s},i)=>(
        <div key={c.id} style={{background:P.white,border:i===0?`1.5px solid ${P.sage}`:`1px solid ${P.sand}`,
          borderRadius:14,padding:22,marginBottom:14}}>
          {i===0&&<Tag color={P.white} bg={P.sage}>✦ BEST MATCH</Tag>}
          {i===0&&<div style={{height:10}}/>}

          <div style={{display:"flex",gap:14,alignItems:"flex-start",marginBottom:14}}>
            <div style={{width:50,height:50,borderRadius:"50%",background:`linear-gradient(135deg,${c.hue}22,${c.hue}44)`,
              color:c.hue,display:"flex",alignItems:"center",justifyContent:"center",fontSize:14,fontWeight:700,flexShrink:0,fontFamily:F.body,border:`2px solid ${c.hue}40`}}>
              {c.initials}
            </div>
            <div style={{flex:1}}>
              <div style={{fontFamily:F.display,fontSize:17,fontWeight:600,color:P.ink,marginBottom:2}}>{c.name}</div>
              <div style={{fontFamily:F.body,fontSize:12,color:P.bark,marginBottom:4}}>{c.tagline} · {c.area}, {c.city}</div>
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                <Stars n={c.rating}/>
                <span style={{fontFamily:F.body,fontSize:12,color:P.bark}}>{c.rating} ({c.reviews} reviews · full-cycle verified)</span>
              </div>
            </div>
            <div style={{textAlign:"right",flexShrink:0}}>
              <div style={{fontFamily:F.display,fontSize:30,fontWeight:700,color:s.total>=80?P.sage:s.total>=60?P.gold:P.blush}}>{s.total}%</div>
              <div style={{fontFamily:F.body,fontSize:10,color:P.bark}}>MATCH</div>
            </div>
          </div>

          <div style={{marginBottom:14}}>
            {[["Tradition",s.br.tradition],["Budget",s.br.budget],["Location",s.br.location],["Availability",s.br.availability],["Live-in",s.br.liveIn]].map(([l,v])=>(
              <ScoreBar key={l} label={l} val={v}/>
            ))}
          </div>

          <div style={{display:"flex",gap:10,marginBottom:14}}>
            <div style={{background:P.sageL,borderRadius:8,padding:"8px 14px",flex:1}}>
              <div style={{fontFamily:F.body,fontSize:10,color:P.bark,fontWeight:700}}>MONTHLY RATE</div>
              <div style={{fontFamily:F.display,fontSize:16,fontWeight:600}}>AED {c.rate.toLocaleString()}</div>
            </div>
            <div style={{background:P.sageL,borderRadius:8,padding:"8px 14px",flex:1}}>
              <div style={{fontFamily:F.body,fontSize:10,color:P.bark,fontWeight:700}}>AVAILABLE IN</div>
              <div style={{fontFamily:F.display,fontSize:16,fontWeight:600,color:P.sage}}>{c.availDays} days</div>
            </div>
            <div style={{background:P.sageL,borderRadius:8,padding:"8px 14px",flex:1}}>
              <div style={{fontFamily:F.body,fontSize:10,color:P.bark,fontWeight:700}}>FOUND VIA</div>
              <div style={{fontFamily:F.body,fontSize:11,color:P.sage,marginTop:2}}>{c.sources[0]}</div>
            </div>
          </div>

          {/* Review */}
          <div style={{background:P.parchment,borderRadius:10,padding:"14px 16px",marginBottom:14}}>
            <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
              <div style={{display:"flex",alignItems:"center",gap:8}}>
                <Stars n={c.review.stars} size={12}/>
                <span style={{fontFamily:F.body,fontSize:12,fontWeight:700,color:P.ink}}>{c.review.by}</span>
              </div>
              <span style={{fontFamily:F.body,fontSize:11,color:P.bark}}>{c.review.when}</span>
            </div>
            <div style={{fontFamily:F.body,fontSize:13,color:P.ink,lineHeight:1.65,fontStyle:"italic"}}>"{c.review.text}"</div>
            <div style={{fontFamily:F.body,fontSize:10,color:P.sage,marginTop:8,fontWeight:700}}>✓ VERIFIED FULL-CYCLE REVIEW</div>
          </div>

          {expanded===c.id&&(
            <div style={{marginBottom:14}}>
              <div style={{fontFamily:F.body,fontSize:11,color:P.bark,fontWeight:700,letterSpacing:"0.05em",marginBottom:8}}>CERTIFICATIONS</div>
              <div style={{display:"flex",flexWrap:"wrap",gap:6,marginBottom:12}}>
                {c.certs.map(ct=><Tag key={ct}>{ct}</Tag>)}
              </div>
              <div style={{fontFamily:F.body,fontSize:11,color:P.bark,fontWeight:700,letterSpacing:"0.05em",marginBottom:8}}>LANGUAGES</div>
              <div style={{fontFamily:F.body,fontSize:13,color:P.ink,marginBottom:12}}>{c.langs.join(" · ")}</div>
              <div style={{fontFamily:F.body,fontSize:11,color:P.bark,fontWeight:700,letterSpacing:"0.05em",marginBottom:8}}>FOUND THROUGH</div>
              <div style={{fontFamily:F.body,fontSize:12,color:P.bark}}>{c.sources.join(", ")}</div>
            </div>
          )}

          <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
            <Btn small>Request booking</Btn>
            <Btn small variant="secondary">Send message</Btn>
            <Btn small variant="secondary" onClick={()=>setExpanded(expanded===c.id?null:c.id)}>
              {expanded===c.id?"Hide details ↑":"Details ↓"}
            </Btn>
          </div>
        </div>
      ))}

      <div style={{textAlign:"center",marginTop:16}}>
        <Btn onClick={onReset} variant="secondary">← Start over</Btn>
      </div>
    </div>
  );
}

/* ─── CENTERS PAGE ────────────────────────────────────────────────────────── */
function CentersPage(){
  const {data:centers}=useCenters();
  const [active,setActive]=useState(null);
  return(
    <div style={{maxWidth:900,margin:"0 auto",padding:"40px 24px"}}>
      <div style={{fontFamily:F.body,fontSize:11,color:P.gold,letterSpacing:"0.1em",fontWeight:700,marginBottom:8}}>PARTNER WELLNESS CENTERS</div>
      <h1 style={{fontFamily:F.display,fontSize:30,fontWeight:700,color:P.ink,marginBottom:8,letterSpacing:"-0.02em"}}>Ayurvedic centers offering home service</h1>
      <p style={{fontFamily:F.body,fontSize:15,color:P.bark,lineHeight:1.75,marginBottom:8,maxWidth:600}}>
        We've partnered with UAE's most respected Ayurvedic centers. All offer postnatal massage and some provide home service. firsttimemoms users get exclusive discounts on booking.
      </p>
      <div style={{background:P.goldL,border:`1px solid ${P.gold}30`,borderRadius:10,padding:"12px 16px",marginBottom:36,
        fontFamily:F.body,fontSize:13,color:P.bark,lineHeight:1.6,display:"inline-block"}}>
        🎁 <strong>Partner discount:</strong> All centers below offer an exclusive firsttimemoms rate. Mention the platform when booking.
      </div>

      <div style={{display:"grid",gap:20}}>
        {centers.map(c=>(
          <div key={c.id} style={{background:P.white,border:`1px solid ${P.sand}`,borderRadius:14,overflow:"hidden"}}>
            <div style={{display:"flex",gap:0}}>
              <div style={{width:6,background:c.hue,flexShrink:0}}/>
              <div style={{padding:"22px 24px",flex:1}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:10,flexWrap:"wrap",gap:8}}>
                  <div>
                    <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:6,flexWrap:"wrap"}}>
                      <span style={{fontFamily:F.display,fontSize:18,fontWeight:700,color:P.ink}}>{c.name}</span>
                      <Tag color={c.hue} bg={c.hue+"18"}>{c.badge}</Tag>
                      {c.homeService&&<Tag color={P.sage} bg={P.sageL}>🏠 Home Service</Tag>}
                    </div>
                    <div style={{fontFamily:F.body,fontSize:13,color:P.bark,marginBottom:8}}>{c.tagline}</div>
                    <div style={{display:"flex",alignItems:"center",gap:8}}>
                      <Stars n={c.rating}/>
                      <span style={{fontFamily:F.body,fontSize:12,color:P.bark}}>{c.rating} ({c.reviews} ratings)</span>
                    </div>
                  </div>
                  <div style={{textAlign:"right"}}>
                    <div style={{fontFamily:F.body,fontSize:11,color:P.bark,marginBottom:4}}>📞 {c.phone}</div>
                    <div style={{display:"flex",flexWrap:"wrap",gap:4,justifyContent:"flex-end"}}>
                      {c.locations.map(l=><Tag key={l} color={P.bark} bg={P.parchment}>{l}</Tag>)}
                    </div>
                  </div>
                </div>

                <p style={{fontFamily:F.body,fontSize:14,color:P.bark,lineHeight:1.7,marginBottom:14}}>{c.desc}</p>

                <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:14}}>
                  {c.services.map(s=><Tag key={s} color={P.bark} bg={P.parchment}>{s}</Tag>)}
                </div>

                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:14}}>
                  <div style={{background:P.parchment,borderRadius:8,padding:"10px 14px"}}>
                    <div style={{fontFamily:F.body,fontSize:10,color:P.bark,fontWeight:700,marginBottom:4}}>STANDARD PRICING</div>
                    <div style={{fontFamily:F.body,fontSize:13,color:P.ink}}>{c.pricing}</div>
                  </div>
                  <div style={{background:P.goldL,border:`1px solid ${P.gold}25`,borderRadius:8,padding:"10px 14px"}}>
                    <div style={{fontFamily:F.body,fontSize:10,color:P.gold,fontWeight:700,marginBottom:4}}>🎁 FIRSTTIMEMOMS EXCLUSIVE</div>
                    <div style={{fontFamily:F.body,fontSize:13,color:P.ink,fontWeight:700}}>{c.partnerDiscount}</div>
                  </div>
                </div>

                <div style={{display:"flex",gap:8}}>
                  <Btn small variant="gold">Book with discount</Btn>
                  <Btn small variant="secondary">Call center</Btn>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── SHOP PAGE ───────────────────────────────────────────────────────────── */
function ShopPage(){
  const {data:products}=useProducts();
  const [filter,setFilter]=useState("All");
  const [cart,setCart]=useState([]);
  const cats=["All","Oils","Healing Foods","Herbal Care","Ayurvedic Medicines","Recovery","Equipment"];
  const shown=filter==="All"?products:products.filter(p=>p.category===filter);
  const addCart=id=>setCart(c=>c.includes(id)?c.filter(x=>x!==id):[...c,id]);

  return(
    <div style={{maxWidth:900,margin:"0 auto",padding:"40px 24px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:8,flexWrap:"wrap",gap:12}}>
        <div>
          <div style={{fontFamily:F.body,fontSize:11,color:P.blush,letterSpacing:"0.1em",fontWeight:700,marginBottom:8}}>THE SHOP</div>
          <h1 style={{fontFamily:F.display,fontSize:30,fontWeight:700,color:P.ink,marginBottom:8,letterSpacing:"-0.02em"}}>Postnatal ingredients, sourced from origin</h1>
          <p style={{fontFamily:F.body,fontSize:14,color:P.bark,lineHeight:1.75,maxWidth:580}}>
            The traditional ingredients that are hard to find in the UAE — or priced 2–3× what they cost at source. We import directly from India, Malaysia, Indonesia, and Korea to offer fair prices and guaranteed authenticity.
          </p>
        </div>
        {cart.length>0&&(
          <div style={{background:P.sage,color:P.white,borderRadius:10,padding:"10px 18px",fontFamily:F.body,fontSize:13,fontWeight:700,cursor:"pointer"}}>
            🛒 {cart.length} item{cart.length>1?"s":""} in bag
          </div>
        )}
      </div>

      <div style={{background:P.blushL,border:`1px solid ${P.blushM}`,borderRadius:10,padding:"12px 16px",marginBottom:28,
        fontFamily:F.body,fontSize:13,color:P.bark,lineHeight:1.6}}>
        🌿 <strong>Coming soon:</strong> We're building partnerships with regional suppliers to import these items regularly. Sign up to be notified when each item becomes available for shipping within UAE.
      </div>

      {/* Category filter */}
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:28}}>
        {cats.map(c=>(
          <button key={c} onClick={()=>setFilter(c)}
            style={{padding:"7px 14px",borderRadius:20,border:filter===c?`1.5px solid ${P.blush}`:`1px solid ${P.sand}`,
              background:filter===c?P.blushL:P.white,fontFamily:F.body,fontSize:12,cursor:"pointer",
              color:filter===c?P.blush:P.bark,fontWeight:filter===c?700:400}}>
            {c}
          </button>
        ))}
      </div>

      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(270px,1fr))",gap:16}}>
        {shown.map(p=>{
          const inCart=cart.includes(p.id);
          return(
            <div key={p.id} style={{background:P.white,border:`1px solid ${P.sand}`,borderRadius:14,overflow:"hidden",display:"flex",flexDirection:"column"}}>
              <div style={{background:P.parchment,padding:"28px 20px",textAlign:"center",fontSize:40,borderBottom:`1px solid ${P.sand}`}}>
                {p.icon}
              </div>
              <div style={{padding:"18px 18px 16px",flex:1,display:"flex",flexDirection:"column"}}>
                <div style={{display:"flex",gap:6,marginBottom:8,flexWrap:"wrap"}}>
                  <Tag color={P.bark} bg={P.parchment}>{p.category}</Tag>
                  <Tag color={P.sage} bg={P.sageL}>📍 {p.origin}</Tag>
                </div>
                <div style={{fontFamily:F.display,fontSize:15,fontWeight:600,color:P.ink,marginBottom:8,lineHeight:1.3}}>{p.name}</div>
                <div style={{fontFamily:F.body,fontSize:12,color:P.bark,lineHeight:1.65,marginBottom:12,flex:1}}>{p.desc}</div>

                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:12}}>
                  <div style={{background:P.blushL,borderRadius:7,padding:"8px 10px"}}>
                    <div style={{fontFamily:F.body,fontSize:9,color:P.blush,fontWeight:700,marginBottom:2}}>UAE RETAIL</div>
                    <div style={{fontFamily:F.body,fontSize:11,color:P.bark,textDecoration:"line-through"}}>{p.uaePrice}</div>
                  </div>
                  <div style={{background:P.sageL,borderRadius:7,padding:"8px 10px"}}>
                    <div style={{fontFamily:F.body,fontSize:9,color:P.sage,fontWeight:700,marginBottom:2}}>OUR PRICE</div>
                    <div style={{fontFamily:F.body,fontSize:13,fontWeight:700,color:P.sage}}>{p.ourPrice}</div>
                  </div>
                </div>

                <div style={{background:P.goldL,borderRadius:7,padding:"6px 10px",marginBottom:12,fontFamily:F.body,fontSize:11,color:P.gold,fontWeight:700}}>
                  💰 {p.saving}
                </div>

                <div style={{fontFamily:F.body,fontSize:11,color:P.bark,lineHeight:1.5,marginBottom:14,fontStyle:"italic"}}>{p.note}</div>

                <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:14}}>
                  {p.traditions.map(t=><Tag key={t} color={P.bark} bg={P.parchment}>{t}</Tag>)}
                </div>

                <Btn onClick={()=>addCart(p.id)} variant={inCart?"secondary":"blush"} small style={{width:"100%"}}>
                  {inCart?"✓ Added to bag":"Add to bag"}
                </Btn>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── ROOT ────────────────────────────────────────────────────────────────── */
export default function App(){
  const [page,setPage]=useState("home");

  return(
    <>
      <style>{CSS_VARS}</style>
      <div style={{minHeight:"100vh",background:P.cream,fontFamily:F.body,color:P.ink}}>
        <Nav page={page} setPage={setPage}/>
        {page==="home"    && <HomePage setPage={setPage}/>}
        {page==="find"    && <FindPage/>}
        {page==="centers" && <CentersPage/>}
        {page==="shop"    && <ShopPage/>}
        <footer style={{borderTop:`1px solid ${P.sand}`,padding:"32px 24px",marginTop:40,textAlign:"center",
          fontFamily:F.body,fontSize:12,color:P.bark,background:P.parchment}}>
          <div style={{fontFamily:F.display,fontSize:16,fontWeight:600,color:P.ink,marginBottom:6}}>firsttimemoms</div>
          <div style={{marginBottom:8}}>Culturally-matched postnatal care in the UAE · Dubai · Abu Dhabi · Sharjah</div>
          <div style={{color:P.sand}}>© 2026 firsttimemoms. Reviews verified. Traditions respected.</div>
        </footer>
      </div>
    </>
  );
}
