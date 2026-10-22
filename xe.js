/* NEWDAY — tab "Mua bán xe" (bản demo). Module độc lập: chỉ cần có <section id="m4"> trong index.html.
   Dữ liệu 35 tin dưới đây là DỮ LIỆU MẪU tự soạn để xem giao diện, không phải tin đăng thật. */
(()=>{"use strict";
const root=document.getElementById("m4");if(!root)return;
const $=id=>document.getElementById(id);
const store={get(k,d){try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const nf=new Intl.NumberFormat("vi-VN"),n=x=>nf.format(Math.round(x));
const dec=x=>String(Math.round(x*10)/10).replace(".",",");
const tr=x=>x>=1000?`${Math.floor(x/1000)} tỷ${Math.round(x%1000)?` ${Math.round(x%1000)} triệu`:""}`:`${dec(x)} triệu`;
const pc=d=>{const s=(Math.abs(d)*100).toFixed(1).replace(".",",");return(d>0.0005?"+":d<-0.0005?"−":"")+s+"%"};

// ===== Dữ liệu mẫu: [id, hãng, dòng, năm, giá (triệu), km, hộp số, nhiên liệu, màu, tỉnh, người bán, đã xác thực] =====
const AT="Số tự động",MT="Số sàn",CN="Cá nhân",SR="Showroom";
const RAW=[
[1,"Toyota","Vios",2019,395,58000,AT,"Xăng","Trắng","Khánh Hòa",CN,1],[2,"Toyota","Vios",2019,372,81000,MT,"Xăng","Bạc","Đà Nẵng",CN,0],
[3,"Toyota","Vios",2020,418,42000,AT,"Xăng","Đen","TP.HCM",SR,1],[4,"Toyota","Vios",2018,345,96000,MT,"Xăng","Trắng","Hà Nội",CN,0],
[5,"Toyota","Vios",2020,455,36000,AT,"Xăng","Đỏ","Khánh Hòa",SR,1],
[6,"Hyundai","Accent",2020,428,39000,AT,"Xăng","Trắng","TP.HCM",CN,1],[7,"Hyundai","Accent",2019,385,60000,AT,"Xăng","Bạc","Hà Nội",CN,0],
[8,"Hyundai","Accent",2020,398,52000,MT,"Xăng","Đỏ","Đà Nẵng",SR,1],[9,"Hyundai","Accent",2021,455,28000,AT,"Xăng","Xám","Khánh Hòa",SR,1],
[10,"Hyundai","Accent",2019,345,88000,AT,"Xăng","Đen","Hà Nội",CN,0],
[11,"Mazda","Mazda3",2019,560,49000,AT,"Xăng","Đỏ","TP.HCM",SR,1],[12,"Mazda","Mazda3",2020,598,35000,AT,"Xăng","Trắng","Hà Nội",CN,1],
[13,"Mazda","Mazda3",2018,505,78000,AT,"Xăng","Xám","Đà Nẵng",CN,0],[14,"Mazda","Mazda3",2019,538,61000,AT,"Xăng","Xanh","Khánh Hòa",CN,0],
[15,"Mazda","CX-5",2019,735,55000,AT,"Xăng","Trắng","TP.HCM",SR,1],[16,"Mazda","CX-5",2020,790,38000,AT,"Xăng","Đỏ","Hà Nội",SR,1],
[17,"Mazda","CX-5",2018,668,90000,AT,"Xăng","Bạc","Khánh Hòa",CN,0],[18,"Mazda","CX-5",2019,705,67000,AT,"Xăng","Xám","Đà Nẵng",CN,1],
[19,"Mazda","CX-5",2020,845,41000,AT,"Xăng","Đen","TP.HCM",SR,1],
[20,"Toyota","Fortuner",2019,890,72000,AT,"Dầu","Trắng","Khánh Hòa",CN,1],[21,"Toyota","Fortuner",2019,935,54000,AT,"Dầu","Đen","Hà Nội",SR,1],
[22,"Toyota","Fortuner",2020,985,45000,AT,"Dầu","Bạc","TP.HCM",SR,1],[23,"Toyota","Fortuner",2018,830,98000,MT,"Dầu","Trắng","Đà Nẵng",CN,0],
[24,"Honda","City",2020,478,40000,AT,"Xăng","Trắng","TP.HCM",CN,1],[25,"Honda","City",2021,520,25000,AT,"Xăng","Đỏ","Hà Nội",SR,1],
[26,"Honda","City",2020,445,58000,AT,"Xăng","Bạc","Khánh Hòa",CN,0],[27,"Honda","City",2019,430,70000,AT,"Xăng","Xám","Đà Nẵng",CN,0],
[28,"Kia","Morning",2019,262,50000,AT,"Xăng","Trắng","Khánh Hòa",CN,0],[29,"Kia","Morning",2020,285,38000,AT,"Xăng","Đỏ","TP.HCM",SR,1],
[30,"Kia","Morning",2019,248,72000,MT,"Xăng","Bạc","Hà Nội",CN,0],[31,"Kia","Morning",2018,228,90000,AT,"Xăng","Xanh","Đà Nẵng",CN,0],
[32,"Mitsubishi","Xpander",2020,560,47000,AT,"Xăng","Bạc","Khánh Hòa",SR,1],[33,"Mitsubishi","Xpander",2021,598,30000,AT,"Xăng","Trắng","TP.HCM",SR,1],
[34,"Mitsubishi","Xpander",2020,525,66000,MT,"Xăng","Xám","Hà Nội",CN,0],[35,"Mitsubishi","Xpander",2019,505,80000,AT,"Xăng","Nâu","Đà Nẵng",CN,0]];
const BASE=RAW.map(r=>({id:r[0],hang:r[1],dong:r[2],nam:r[3],gia:r[4],km:r[5],so:r[6],nl:r[7],mau:r[8],tinh:r[9],ban:r[10],xt:!!r[11]}));
let CARS=BASE;const YEAR=new Date().getFullYear();
const ten=c=>`${c.hang} ${c.dong} ${c.nam}`;

// ===== Đánh giá giá (Deal Rating): so với TRUNG VỊ các tin cùng dòng, đời ±1 năm; cần ≥3 tin so sánh =====
const TIERS=[{t:"Giá rất tốt",c:"#3fb950",w:23.3},{t:"Giá tốt",c:"#7ee787",w:16.7},{t:"Giá hợp lý",c:"#8b949e",w:20},{t:"Giá cao",c:"#d29922",w:16.7},{t:"Giá quá cao",c:"#f85149",w:23.3}];
const median=a=>{const s=a.slice().sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2};
const same=(a,b)=>a.toLowerCase()===b.toLowerCase();
const deal=c=>{const cp=BASE.filter(o=>o.id!==c.id&&same(o.hang,c.hang)&&same(o.dong,c.dong)&&Math.abs(o.nam-c.nam)<=1);
 if(cp.length<3)return{n:cp.length};
 const med=median(cp.map(o=>o.gia)),d=(c.gia-med)/med,i=d<=-.08?0:d<=-.03?1:d<.03?2:d<.08?3:4;
 return{n:cp.length,med,d,i,tier:TIERS[i]}};

// ===== Thành phần giao diện =====
const MAU={"Trắng":"#e6edf3","Đen":"#2b313a","Bạc":"#a9b3be","Xám":"#6e7681","Đỏ":"#d1453b","Xanh":"#2f6fb5","Nâu":"#8a6a4a"};
const car=m=>`<svg viewBox="0 0 160 64" role="img" aria-label="Minh họa xe màu ${esc(m.toLowerCase())}"><path d="M10 46 L14 36 Q16 32 22 31 L42 28 L56 14 Q60 10 66 10 H102 Q108 10 112 14 L126 28 L144 31 Q150 33 150 40 V46 Z" fill="${MAU[m]||"#6e7681"}" stroke="rgba(120,120,120,.55)"/><path d="M60 17 L48 28 H78 V14 H66 Q62 14 60 17 Z M84 14 V28 H120 L108 16 Q106 14 102 14 Z" fill="#0d1117" opacity=".55"/><circle cx="42" cy="48" r="10" fill="#0d1117"/><circle cx="42" cy="48" r="4.5" fill="#8b949e"/><circle cx="120" cy="48" r="10" fill="#0d1117"/><circle cx="120" cy="48" r="4.5" fill="#8b949e"/></svg>`;
const gauge=(dl,big)=>{
 if(dl.i==null)return`<div class="xe-nd">Chưa đủ tin để so giá (có ${dl.n}/3 tin cùng dòng, đời ±1 năm)</div>`;
 const pos=Math.max(0,Math.min(100,(dl.d+.15)/.30*100));
 return`<div class="xe-g${big?" big":""}"><div class="xe-gw"><div class="xe-gb">${TIERS.map(t=>`<i style="background:${t.c};flex:0 0 ${t.w}%"></i>`).join("")}</div><b style="left:${pos.toFixed(1)}%"></b></div><div class="xe-gl" style="color:var(--xt${dl.i},${dl.tier.c})">${dl.tier.t}<span>${pc(dl.d)} so với trung vị</span></div></div>`};

// ===== Tin người dùng tự đăng (lưu trong trình duyệt của máy này) =====
const txt=(v,m)=>typeof v==="string"?v.replace(/\s+/g," ").trim().slice(0,m):"";
const cleanMine=a=>(Array.isArray(a)?a:[]).map(x=>{if(!x||typeof x!=="object")return null;
 const o={id:Number(x.id),hang:txt(x.hang,30),dong:txt(x.dong,30),nam:Number(x.nam),gia:Number(x.gia),km:Number(x.km),so:x.so,nl:x.nl,mau:x.mau,tinh:txt(x.tinh,30),ban:x.ban,mo:txt(x.mo,300),xt:false,mine:true};
 const ok=Number.isInteger(o.id)&&o.id>=1000&&o.hang&&o.dong&&o.tinh&&Number.isInteger(o.nam)&&o.nam>=1990&&o.nam<=YEAR&&o.gia>0&&o.gia<=50000&&Number.isInteger(o.km)&&o.km>=0&&o.km<=1e6&&[AT,MT].includes(o.so)&&["Xăng","Dầu"].includes(o.nl)&&MAU[o.mau]&&[CN,SR].includes(o.ban);
 return ok?o:null}).filter(Boolean).slice(0,50);
// Giá nhiên liệu mặc định: giá bán tối đa kỳ điều hành 8/10/2026 (E10 RON95-III, dầu diesel 0.05S), thay đổi hằng tuần nên cho nhập lại
const FUEL={"Xăng":{l:7,gia:28254},"Dầu":{l:8,gia:29128}};
// ===== Trạng thái =====
const S={q:"",hang:"",gia:0,nam:0,so:"",tinh:"",sort:"tot",luu:false,chiMine:false,cmp:[],fav:store.get("xe_fav",[]),open:null,loan:{pct:70,rate:9,years:5,kind:"goc"},tco:{km:15000,bh:1.5,bd:12,kh:8,l:7,gia:28254},mine:cleanMine(store.get("xe_mine",[]))};
const rebuild=()=>{CARS=BASE.concat(S.mine);CARS.forEach(c=>{c.dl=deal(c)})};rebuild();
const saveMine=()=>{store.set("xe_mine",S.mine.map(({dl,...r})=>r));const b=store.get("xe_mine",null);return Array.isArray(b)&&b.length===S.mine.length};
const uniq=a=>a.filter((x,i)=>a.indexOf(x)===i).sort((x,y)=>x.localeCompare(y,"vi"));
const opts=(arr,cur)=>arr.map(([v,l])=>`<option value="${esc(v)}"${String(v)===String(cur)?" selected":""}>${esc(l)}</option>`).join("");
const SORTS={nam:["Đời mới nhất",(a,b)=>b.nam-a.nam||a.gia-b.gia],gtang:["Giá thấp → cao",(a,b)=>a.gia-b.gia],ggiam:["Giá cao → thấp",(a,b)=>b.gia-a.gia],km:["Ít km nhất",(a,b)=>a.km-b.km],tot:["Giá tốt nhất",(a,b)=>(a.dl.d==null?9:a.dl.d)-(b.dl.d==null?9:b.dl.d)]};
const list=()=>{const q=S.q.trim().toLowerCase();
 return CARS.filter(c=>(!q||ten(c).toLowerCase().includes(q))&&(!S.hang||c.hang===S.hang)&&(!S.gia||c.gia<=S.gia)&&(!S.nam||c.nam>=S.nam)&&(!S.so||c.so===S.so)&&(!S.tinh||c.tinh===S.tinh)&&(!S.luu||S.fav.includes(c.id))&&(!S.chiMine||c.mine)).sort(SORTS[S.sort][1])};

const card=c=>{const f=S.fav.includes(c.id),k=S.cmp.includes(c.id),t=esc(ten(c));
 return`<article class="xe-card" data-id="${c.id}"><div class="xe-img">${car(c.mau)}${c.mine?`<span class="xe-xt mine">Tin của tôi</span>`:c.xt?`<span class="xe-xt">✔ Đã xác thực giấy tờ</span>`:""}<button class="xe-fav${f?" on":""}" data-xe="fav" data-id="${c.id}" aria-pressed="${f}" aria-label="${f?"Bỏ lưu":"Lưu"} ${t}">${f?"♥":"♡"}</button></div><div class="xe-body"><button class="xe-t" data-xe="open" data-id="${c.id}">${t}</button><div class="xe-p">${tr(c.gia)}</div>${gauge(c.dl)}<div class="xe-m">${n(c.km)} km · ${c.so} · ${c.nl}</div><div class="xe-m">${c.tinh} · ${c.ban}</div><label class="xe-cmp"><input type="checkbox" data-xe="cmp" data-id="${c.id}"${k?" checked":""}> So sánh</label></div></article>`};

const drawList=()=>{const a=list();$("xe-count").textContent=`${a.length}/${CARS.length} xe`;
 $("xe-list").innerHTML=a.length?a.map(card).join(""):`<div class="xe-empty">Không có xe nào khớp bộ lọc. Bỏ bớt điều kiện hoặc bấm “Đặt lại”.</div>`;cbar()};
const cbar=(msg,ok)=>{const b=$("xe-cbar"),k=S.cmp.length;
 b.classList.toggle("hide",!k&&!msg);root.classList.toggle("xe-pad",!!(k||msg));
 b.innerHTML=msg?`<span class="${ok?"xe-okm":"xe-warn"}">${esc(msg)}</span>`:`<span>Đã chọn ${k}/3 xe</span><button class="xe-btn pri" data-xe="cmpgo"${k<2?" disabled":""}>So sánh</button><button class="xe-btn" data-xe="cmpclear">Bỏ chọn</button>`;
 if(msg)setTimeout(()=>cbar(),2600)};

// ===== Ước tính trả góp =====
const loanCalc=c=>{const L=S.loan,pct=parseFloat(L.pct),rate=parseFloat(L.rate),yr=parseInt(L.years,10);
 if(!(pct>=0&&pct<=90)||!(rate>=0&&rate<=40)||!(yr>=1&&yr<=10))return null;
 const P=c.gia*1e6,V=P*pct/100;return{P,V,m:yr*12,r:rate/100/12,kind:L.kind}};
const loanOut=c=>{const k=loanCalc(c);
 if(!k)return`<div class="xe-bad">Nhập vay từ 0–90% giá xe, lãi suất 0–40%/năm, thời hạn 1–10 năm.</div>`;
 const{P,V,m,r}=k;let rows,lai;
 if(k.kind==="goc"){const g=V/m;lai=r*(V*m-g*m*(m-1)/2);rows=[["Trả kỳ đầu (cao nhất)",g+V*r],["Trả kỳ cuối",g+g*r]]}
 else{const p=r===0?V/m:V*r/(1-Math.pow(1+r,-m));lai=p*m-V;rows=[["Trả mỗi tháng",p]]}
 rows=[["Giá xe",P],["Trả trước",P-V],["Số tiền vay",V]].concat(rows,[["Tổng lãi phải trả",lai],["Tổng gốc + lãi",V+lai]]);
 return`<table class="xe-tb"><tbody>${rows.map(([a,b])=>`<tr><td>${a}</td><td class="r">${n(b)} đ</td></tr>`).join("")}</tbody></table>`};
// Lãi phải trả trong 12 tháng đầu của khoản vay
const loanY1=k=>{if(k.kind==="goc"){const g=k.V/k.m;return k.r*(12*k.V-g*66)}
 const p=k.r===0?k.V/k.m:k.V*k.r/(1-Math.pow(1+k.r,-k.m));let bal=k.V,s=0;for(let i=0;i<12;i++){const it=bal*k.r;s+=it;bal-=p-it}return s};
// Chi phí sở hữu mỗi năm (các ô nhập là giả định, người dùng chỉnh)
const tcoOut=c=>{const T=S.tco,km=parseFloat(T.km),l=parseFloat(T.l),g=parseFloat(T.gia),bh=parseFloat(T.bh),bd=parseFloat(T.bd),kh=parseFloat(T.kh);
 if(!(km>=0&&km<=200000)||!(l>=0&&l<=30)||!(g>=0&&g<=200000)||!(bh>=0&&bh<=10)||!(bd>=0&&bd<=500)||!(kh>=0&&kh<=50))
  return`<div class="xe-bad">Nhập km 0–200.000/năm, tiêu hao 0–30 lít/100 km, giá nhiên liệu 0–200.000 đ/lít, bảo hiểm 0–10%, bảo dưỡng 0–500 triệu, mất giá 0–50%.</div>`;
 const P=c.gia*1e6,k=loanCalc(c),fuel=km/100*l*g,ins=P*bh/100,oth=bd*1e6,lai=k?loanY1(k):0,cash=fuel+ins+oth+lai,dep=P*kh/100,tot=cash+dep;
 const rows=[["Nhiên liệu",fuel],["Bảo hiểm thân vỏ",ins],["Bảo dưỡng, phí đường bộ, đăng kiểm…",oth],["Lãi vay (12 tháng đầu)",lai],["Cộng chi phí bằng tiền",cash,1],["Mất giá (không phải tiền mặt)",dep],["Tổng chi phí sở hữu mỗi năm",tot,1],["Bình quân mỗi tháng",tot/12]].concat(km>0?[["Bình quân mỗi km",tot/km]]:[]);
 return`<table class="xe-tb"><tbody>${rows.map(([a,b,t])=>`<tr${t?' class="tot"':""}><td>${a}</td><td class="r">${n(b)} đ</td></tr>`).join("")}</tbody></table>${k?"":`<p class="xe-fine">Chưa tính lãi vay vì thông số trả góp ở trên chưa hợp lệ.</p>`}`};

// ===== Hộp thoại chi tiết / so sánh =====
const dlg=()=>$("xe-dlg");
const show=h=>{const d=dlg();d.innerHTML=h;if(!d.open){try{d.showModal()}catch(e){d.setAttribute("open","")}document.body.style.overflow="hidden"}d.scrollTop=0;const b=d.querySelector(".xe-db");if(b)b.scrollTop=0};
const shell=(t,b)=>`<div class="xe-dh"><h3>${esc(t)}</h3><button class="xe-x" data-xe="close" aria-label="Đóng">✕</button></div><div class="xe-db">${b}</div>`;
const openCar=id=>{const c=CARS.find(x=>x.id===id);if(!c)return;S.open=id;const d=c.dl,L=S.loan,T=S.tco;Object.assign(T,FUEL[c.nl]||FUEL["Xăng"]);
 const spec=[["Năm sản xuất",c.nam],["Số km đã đi",n(c.km)+" km"],["Hộp số",c.so],["Nhiên liệu",c.nl],["Màu ngoại thất",c.mau],["Khu vực",c.tinh],["Người bán",c.ban],["Giấy tờ",c.xt?"✔ Đã xác thực (minh họa)":"Chưa xác thực"]];
 show(shell(ten(c),`<div class="xe-dtop"><div class="xe-dimg">${car(c.mau)}</div><div><div class="xe-p big">${tr(c.gia)}</div>${gauge(d,true)}</div></div>
 ${c.mo?`<p class="xe-mo">${esc(c.mo)}</p>`:""}
 ${d.i==null?"":`<p class="xe-m">Trung vị ${d.n} tin cùng dòng, đời ±1 năm: <b>${tr(d.med)}</b>. Giá tin này ${pc(d.d)} so với mức đó.</p>`}
 <p class="xe-fine">Chỉ là tham khảo: chưa tính phiên bản, số km, tình trạng xe; chưa gồm phí trước bạ, đăng ký. Cần xem xe thực tế trước khi quyết định.</p>
 <table class="xe-tb"><tbody>${spec.map(([a,b])=>`<tr><td>${a}</td><td class="r">${esc(b)}</td></tr>`).join("")}</tbody></table>
 <h4>Ước tính trả góp</h4>
 <div class="xe-loan"><label>Vay (% giá xe)<input id="xe-l-pct" type="number" inputmode="decimal" min="0" max="90" step="5" value="${esc(L.pct)}"></label><label>Lãi suất (%/năm)<input id="xe-l-rate" type="number" inputmode="decimal" min="0" max="40" step="0.1" value="${esc(L.rate)}"></label><label>Thời hạn (năm)<input id="xe-l-years" type="number" inputmode="numeric" min="1" max="10" step="1" value="${esc(L.years)}"></label><label>Cách tính<select id="xe-l-kind"><option value="goc"${L.kind==="goc"?" selected":""}>Gốc chia đều, lãi theo dư nợ giảm dần</option><option value="nk"${L.kind==="nk"?" selected":""}>Niên kim (trả đều mỗi tháng)</option></select></label></div>
 <div id="xe-l-out">${loanOut(c)}</div>
 <p class="xe-fine">Lãi suất là số giả định để thử, không phải của ngân hàng nào. Chưa gồm phí bảo hiểm, phí hồ sơ.</p>
 <h4>Chi phí sở hữu ước tính mỗi năm</h4>
 <div class="xe-loan"><label>Đi bao nhiêu km/năm<input id="xe-t-km" type="number" inputmode="numeric" min="0" max="200000" step="1000" value="${esc(T.km)}"></label><label>Tiêu hao (lít/100 km)<input id="xe-t-l" type="number" inputmode="decimal" min="0" max="30" step="0.1" value="${esc(T.l)}"></label><label>Giá nhiên liệu (đồng/lít)<input id="xe-t-gia" type="number" inputmode="numeric" min="0" max="200000" step="100" value="${esc(T.gia)}"></label><label>Bảo hiểm thân vỏ (%/năm giá xe)<input id="xe-t-bh" type="number" inputmode="decimal" min="0" max="10" step="0.1" value="${esc(T.bh)}"></label><label>Bảo dưỡng, phí khác (triệu/năm)<input id="xe-t-bd" type="number" inputmode="decimal" min="0" max="500" step="0.5" value="${esc(T.bd)}"></label><label>Mất giá (%/năm giá xe)<input id="xe-t-kh" type="number" inputmode="decimal" min="0" max="50" step="0.5" value="${esc(T.kh)}"></label></div>
 <div id="xe-t-out">${tcoOut(c)}</div>
 <p class="xe-fine">Giá nhiên liệu mặc định là giá bán tối đa kỳ điều hành 8/10/2026 (xăng E10 RON95-III 28.254 đ/lít, dầu diesel 0.05S 29.128 đ/lít), thay đổi hằng tuần nên anh nhập lại giá thực tế. Tiêu hao, bảo hiểm, bảo dưỡng, mất giá là số giả định để thử, không phải số liệu thật. Lãi vay lấy từ mục trả góp phía trên.</p>
 <div class="xe-ct"><button class="xe-btn" disabled title="Bản demo chưa có số điện thoại thật">Gọi người bán</button><button class="xe-btn" disabled title="Bản demo chưa có liên kết Zalo thật">Nhắn Zalo</button>${c.mine?`<button class="xe-btn dg" data-xe="del" data-id="${c.id}">Xóa tin này</button>`:""}</div>`))};
const postForm=()=>{const H=uniq(BASE.map(c=>c.hang)),T=uniq(BASE.map(c=>c.tinh)),f=(id,l,inp)=>`<label>${l}${inp}</label>`;
 show(shell("Đăng tin (lưu trên máy này)",`<p class="xe-fine" style="margin-top:0">Tin chỉ lưu trong trình duyệt của máy này, không gửi đi đâu và người khác không thấy. Bản demo chưa có ảnh, xe hiển thị bằng hình minh họa theo màu.</p>
 <div class="xe-loan">
 ${f("","Hãng xe",`<input id="xe-p-hang" list="xe-dl-hang" maxlength="30" autocomplete="off"><datalist id="xe-dl-hang">${H.map(h=>`<option value="${esc(h)}">`).join("")}</datalist>`)}
 ${f("","Dòng xe",`<input id="xe-p-dong" maxlength="30" autocomplete="off">`)}
 ${f("","Năm sản xuất",`<input id="xe-p-nam" type="number" inputmode="numeric" min="1990" max="${YEAR}" step="1">`)}
 ${f("","Giá bán (triệu đồng)",`<input id="xe-p-gia" type="number" inputmode="decimal" min="1" max="50000" step="0.5">`)}
 ${f("","Số km đã đi",`<input id="xe-p-km" type="number" inputmode="numeric" min="0" max="1000000" step="1000">`)}
 ${f("","Hộp số",`<select id="xe-p-so">${opts([[AT,AT],[MT,MT]],AT)}</select>`)}
 ${f("","Nhiên liệu",`<select id="xe-p-nl">${opts([["Xăng","Xăng"],["Dầu","Dầu"]],"Xăng")}</select>`)}
 ${f("","Màu ngoại thất",`<select id="xe-p-mau">${opts(Object.keys(MAU).map(m=>[m,m]),"Trắng")}</select>`)}
 ${f("","Khu vực",`<input id="xe-p-tinh" list="xe-dl-tinh" maxlength="30" autocomplete="off"><datalist id="xe-dl-tinh">${T.map(t=>`<option value="${esc(t)}">`).join("")}</datalist>`)}
 ${f("","Người bán",`<select id="xe-p-ban">${opts([[CN,CN],[SR,SR]],CN)}</select>`)}
 <label style="grid-column:1/-1">Mô tả ngắn (không bắt buộc, tối đa 300 ký tự)<textarea id="xe-p-mo" rows="3" maxlength="300"></textarea></label></div>
 <div id="xe-p-err" class="xe-bad hide" role="alert"></div>
 <div class="xe-ct"><button class="xe-btn pri" data-xe="postsave">Đăng tin</button><button class="xe-btn" data-xe="close">Hủy</button></div>`))};
const postSave=()=>{const v=id=>$(id).value,err=m=>{const e=$("xe-p-err");e.textContent=m;e.classList.remove("hide")};
 const canon=(val,list)=>list.find(x=>same(x,val))||(val&&val===val.toLowerCase()?val.charAt(0).toUpperCase()+val.slice(1):val);
 const hang=canon(txt(v("xe-p-hang"),30),BASE.map(c=>c.hang)),dong=canon(txt(v("xe-p-dong"),30),BASE.filter(c=>same(c.hang,hang)).map(c=>c.dong)),tinh=canon(txt(v("xe-p-tinh"),30),BASE.map(c=>c.tinh));
 const nam=Number(v("xe-p-nam")),gia=Number(v("xe-p-gia")),km=Number(v("xe-p-km"));
 if(!hang||!dong)return err("Nhập hãng xe và dòng xe.");
 if(!tinh)return err("Nhập khu vực.");
 if(v("xe-p-nam")===""||!Number.isInteger(nam)||nam<1990||nam>YEAR)return err(`Năm sản xuất phải là số nguyên từ 1990 đến ${YEAR}.`);
 if(v("xe-p-gia")===""||!(gia>0&&gia<=50000))return err("Giá bán phải lớn hơn 0 và không quá 50.000 triệu đồng.");
 if(v("xe-p-km")===""||!Number.isInteger(km)||km<0||km>1e6)return err("Số km phải là số nguyên từ 0 đến 1.000.000.");
 if(S.mine.length>=50)return err("Đã đủ 50 tin của anh trên máy này, hãy xóa bớt tin cũ.");
 const id=Math.max(1000,...S.mine.map(x=>x.id))+1;
 const o={id,hang,dong,nam,gia:Math.round(gia*10)/10,km,so:v("xe-p-so"),nl:v("xe-p-nl"),mau:v("xe-p-mau"),tinh,ban:v("xe-p-ban"),mo:txt(v("xe-p-mo"),300),xt:false,mine:true};
 S.mine.push(o);
 if(!saveMine()){S.mine.pop();return err("Trình duyệt này không cho lưu dữ liệu (có thể đang ở chế độ riêng tư), nên chưa đăng được tin.")}
 rebuild();dlg().close();S.chiMine=true;build();cbar("Đã lưu tin trên máy này. Đang xem mục “Chỉ tin của tôi”.",true)};
const openCmp=()=>{const cs=S.cmp.map(id=>CARS.find(c=>c.id===id)).filter(Boolean),multi=cs.length>1,minP=Math.min(...cs.map(c=>c.gia)),minK=Math.min(...cs.map(c=>c.km));
 const row=(l,f,cls)=>`<tr><th scope="row">${l}</th>${cs.map(c=>`<td class="${cls?cls(c):""}">${f(c)}</td>`).join("")}</tr>`;
 show(shell("So sánh xe",`<div class="xe-scroll"><table class="xe-tb cmp"><thead><tr><th></th>${cs.map(c=>`<th>${esc(ten(c))}<br><button class="xe-link" data-xe="open" data-id="${c.id}">Xem chi tiết</button></th>`).join("")}</tr></thead><tbody>
 ${row("Giá",c=>tr(c.gia),c=>multi&&c.gia===minP?"up":"")}${row("Đánh giá giá",c=>c.dl.i==null?"Chưa đủ tin":`<span style="color:var(--xt${c.dl.i},${c.dl.tier.c})">${c.dl.tier.t}</span> (${pc(c.dl.d)})`)}${row("Năm",c=>c.nam)}${row("Số km",c=>n(c.km)+" km",c=>multi&&c.km===minK?"up":"")}${row("Hộp số",c=>c.so)}${row("Nhiên liệu",c=>c.nl)}${row("Màu",c=>c.mau)}${row("Khu vực",c=>c.tinh)}${row("Người bán",c=>c.ban)}${row("Giấy tờ",c=>c.xt?"✔ Đã xác thực":"Chưa xác thực")}
 </tbody></table></div><p class="xe-fine">Chữ xanh là giá thấp nhất và số km ít nhất trong các xe đang so sánh.</p>`))};

// ===== Khung giao diện =====
const build=()=>{
 const H=uniq(CARS.map(c=>c.hang)),T=uniq(CARS.map(c=>c.tinh));
 root.innerHTML=`<div class="xe-note">Bản demo: 35 tin mẫu tự soạn để xem giao diện. Giá, số km, khu vực đều là số giả định, không phải tin đăng thật. Tin anh tự đăng chỉ lưu trên máy này. Nút Gọi và Zalo chưa hoạt động.</div>
 <div class="xe-bar"><input id="xe-q" type="search" placeholder="Tìm hãng, dòng xe, đời xe…" aria-label="Tìm xe" autocomplete="off">
 <select id="xe-hang" aria-label="Hãng xe">${opts([["","Tất cả hãng"]].concat(H.map(h=>[h,h])),S.hang)}</select>
 <select id="xe-gia" aria-label="Giá tối đa">${opts([[0,"Mọi mức giá"],[300,"Đến 300 triệu"],[400,"Đến 400 triệu"],[500,"Đến 500 triệu"],[700,"Đến 700 triệu"],[1000,"Đến 1 tỷ"]],S.gia)}</select>
 <select id="xe-nam" aria-label="Đời xe từ năm">${opts([[0,"Mọi đời xe"],[2018,"Từ 2018"],[2019,"Từ 2019"],[2020,"Từ 2020"],[2021,"Từ 2021"]],S.nam)}</select>
 <select id="xe-so" aria-label="Hộp số">${opts([["","Mọi hộp số"],[AT,AT],[MT,MT]],S.so)}</select>
 <select id="xe-tinh" aria-label="Khu vực">${opts([["","Mọi khu vực"]].concat(T.map(t=>[t,t])),S.tinh)}</select>
 <select id="xe-sort" aria-label="Sắp xếp">${opts(Object.keys(SORTS).map(k=>[k,SORTS[k][0]]),S.sort)}</select></div>
 <div class="xe-head"><span id="xe-count"></span><label class="xe-chip"><input type="checkbox" id="xe-luu"${S.luu?" checked":""}> Đã lưu ♥</label><label class="xe-chip"><input type="checkbox" id="xe-mine"${S.chiMine?" checked":""}> Tin của tôi</label><span class="sp"></span><button class="xe-btn pri" data-xe="post">＋ Đăng tin</button><button class="xe-btn" data-xe="reset">Đặt lại</button></div>
 <div id="xe-list" class="xe-grid"></div><div id="xe-cbar" class="xe-cbar hide"></div><dialog id="xe-dlg" class="xe-dlg" aria-label="Chi tiết xe"></dialog>`;
 drawList()};

// ===== Sự kiện (chỉ trong #m4, tiền tố xe- để không đụng code cũ của app) =====
root.addEventListener("click",e=>{const t=e.target,a=t.closest("[data-xe]");
 if(a){const k=a.dataset.xe,id=+a.dataset.id;
  if(k==="open")openCar(id);
  else if(k==="fav"){const i=S.fav.indexOf(id);i>=0?S.fav.splice(i,1):S.fav.push(id);store.set("xe_fav",S.fav);drawList()}
  else if(k==="close")dlg().close();
  else if(k==="post")postForm();
  else if(k==="postsave")postSave();
  else if(k==="del"){if(confirm("Xóa tin này khỏi máy?")){S.mine=S.mine.filter(x=>x.id!==id);S.cmp=S.cmp.filter(x=>x!==id);S.fav=S.fav.filter(x=>x!==id);store.set("xe_fav",S.fav);saveMine();rebuild();dlg().close();drawList()}}
  else if(k==="cmpgo")openCmp();
  else if(k==="cmpclear"){S.cmp=[];drawList()}
  else if(k==="reset"){Object.assign(S,{q:"",hang:"",gia:0,nam:0,so:"",tinh:"",sort:"tot",luu:false,chiMine:false});build()}
  return}
 if(t===dlg()){dlg().close();return}
 const cd=t.closest(".xe-card");if(cd&&!t.closest("label,input"))openCar(+cd.dataset.id)});
root.addEventListener("change",e=>{const t=e.target;
 if(t.dataset.xe==="cmp"){const id=+t.dataset.id,i=S.cmp.indexOf(id);
  if(t.checked){if(S.cmp.length>=3){t.checked=false;cbar("Chỉ so sánh được tối đa 3 xe cùng lúc.");return}S.cmp.push(id)}else if(i>=0)S.cmp.splice(i,1);
  cbar();return}
 const f={"xe-hang":["hang",String],"xe-gia":["gia",Number],"xe-nam":["nam",Number],"xe-so":["so",String],"xe-tinh":["tinh",String],"xe-sort":["sort",String]}[t.id];
 if(f){S[f[0]]=f[1](t.value);drawList()}else if(t.id==="xe-luu"){S.luu=t.checked;drawList()}else if(t.id==="xe-mine"){S.chiMine=t.checked;drawList()}});
root.addEventListener("input",e=>{const t=e.target;
 if(t.id==="xe-q"){S.q=t.value;drawList()}
 else if(t.id&&t.id.startsWith("xe-p-")){const e=$("xe-p-err");if(e)e.classList.add("hide")}
 else if(t.id&&t.id.startsWith("xe-l-")){S.loan[{"xe-l-pct":"pct","xe-l-rate":"rate","xe-l-years":"years","xe-l-kind":"kind"}[t.id]]=t.value;
  const c=CARS.find(x=>x.id===S.open);if(c){$("xe-l-out").innerHTML=loanOut(c);$("xe-t-out").innerHTML=tcoOut(c)}}
 else if(t.id&&t.id.startsWith("xe-t-")){S.tco[{"xe-t-km":"km","xe-t-l":"l","xe-t-gia":"gia","xe-t-bh":"bh","xe-t-bd":"bd","xe-t-kh":"kh"}[t.id]]=t.value;const c=CARS.find(x=>x.id===S.open);if(c)$("xe-t-out").innerHTML=tcoOut(c)}});
root.addEventListener("close",()=>{document.body.style.overflow=""},true);

// ===== CSS (chỉ áp dụng trong #m4) =====
const css=document.createElement("style");css.textContent=`
#m4 .xe-note{font-size:12px;color:var(--k-mu,#8b949e);background:var(--k-card,#161b22);border:1px dashed var(--k-line,#30363d);border-radius:8px;padding:8px 10px;margin:0 0 10px}
#m4 .xe-bar{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:10px}
#m4 .xe-bar input[type=search]{grid-column:1/-1;width:100%;padding:10px;font-size:14px}
#m4 .xe-bar select{width:100%;padding:9px 8px;font-size:13px}
#m4 .xe-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 10px;font-size:13px;color:var(--k-mu,#8b949e)}
#m4 .xe-head .sp{flex:1}
#m4 .xe-chip{cursor:pointer;color:var(--k-tx,#c9d1d9)}#m4 .xe-chip input{width:auto;vertical-align:-2px;margin-right:4px}
#m4 .xe-btn{font:inherit;font-size:13px;background:var(--k-card,#161b22);color:var(--k-tx,#c9d1d9);border:1px solid var(--k-line,#30363d);border-radius:6px;padding:7px 12px;cursor:pointer}
#m4 .xe-btn.pri{background:#d29922;border-color:#d29922;color:#0d1117;font-weight:600}
#m4 .xe-btn:disabled{opacity:.45;cursor:not-allowed}
#m4 .xe-link{font:inherit;font-size:12px;background:none;border:0;color:var(--k-ac,#e3b341);padding:2px 0;cursor:pointer;text-decoration:underline}
#m4 :focus-visible{outline:2px solid #d29922;outline-offset:2px}
#m4 .xe-grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
#m4.xe-pad{padding-bottom:72px}
#m4 .xe-card{background:var(--k-card,#161b22);border:1px solid var(--k-line,#30363d);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;cursor:pointer}
#m4 .xe-card:hover{border-color:var(--k-mu,#484f58)}
#m4 .xe-img{position:relative;background:var(--k-img,#0f141b);padding:26px 22px 8px}
#m4 .xe-img svg{display:block;width:100%;height:76px}
#m4 .xe-xt{position:absolute;left:8px;top:8px;font-size:11px;background:var(--k-okbg,#12351f);color:var(--k-ok,var(--k-up,#3fb950));border-radius:10px;padding:2px 8px}
#m4 .xe-fav{position:absolute;right:4px;top:4px;width:40px;height:40px;background:none;border:0;color:var(--k-mu,#8b949e);font-size:22px;cursor:pointer}
#m4 .xe-fav.on{color:var(--k-dn,#f85149)}
#m4 .xe-body{padding:10px 12px 12px;display:flex;flex-direction:column;gap:4px}
#m4 .xe-t{font:inherit;font-weight:600;font-size:15px;text-align:left;background:none;border:0;color:var(--k-tx,#e6edf3);padding:0;cursor:pointer}
#m4 .xe-p{font-size:20px;font-weight:700;color:var(--k-ac,#e3b341)}#m4 .xe-p.big{font-size:26px}
#m4 .xe-m{font-size:12.5px;color:var(--k-mu,#8b949e)}
#m4 .xe-cmp{margin-top:6px;font-size:13px;color:var(--k-tx,#c9d1d9);cursor:pointer}#m4 .xe-cmp input{width:auto;vertical-align:-2px;margin-right:4px}
#m4 .xe-g{margin:2px 0}
#m4 .xe-gw{position:relative;padding:3px 0}
#m4 .xe-gb{display:flex;height:6px;border-radius:3px;overflow:hidden}#m4 .xe-gb i{display:block;height:100%}
#m4 .xe-gw b{position:absolute;top:0;width:3px;height:12px;margin-left:-1.5px;background:var(--k-tx,#e6edf3);border-radius:2px;box-shadow:0 0 0 1px var(--k-card,#0d1117)}
#m4 .xe-gl{font-size:12px;font-weight:600}#m4 .xe-gl span{color:var(--k-mu,#8b949e);font-weight:400;margin-left:6px}
#m4 .xe-g.big .xe-gb{height:10px}#m4 .xe-g.big .xe-gw b{height:16px}#m4 .xe-g.big .xe-gl{font-size:14px}
#m4 .xe-nd{font-size:12px;color:var(--k-mu,#6e7681);padding:6px 0}
#m4 .xe-empty,#m4 .xe-bad{grid-column:1/-1;padding:18px;text-align:center;color:var(--k-mu,#8b949e);border:1px dashed var(--k-line,#30363d);border-radius:8px}
#m4 .xe-bad{color:var(--k-dn,#f85149);padding:10px;text-align:left}
#m4 .xe-cbar{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;gap:10px;align-items:center;justify-content:center;background:var(--k-card,#161b22);border-top:1px solid var(--k-line,#30363d);padding:10px 12px calc(10px + env(safe-area-inset-bottom,0px));font-size:13px}
#m4 .xe-cbar.hide{display:none}
#m4 .xe-xt.mine{background:var(--k-minebg,#2a2312);color:var(--k-ac,#e3b341)}
#m4 .xe-okm{color:var(--k-ok,#3fb950)}
#m4 .xe-btn.dg{color:var(--k-dn,#f85149);border-color:var(--k-dn,#f85149)}
#m4 .xe-mo{white-space:pre-wrap;margin:6px 0;color:var(--k-tx,#e6edf3)}
#m4 .xe-tb tr.tot td{font-weight:700;border-top:1px solid var(--k-line,#30363d)}
#m4 .xe-loan textarea{width:100%;padding:8px;font:inherit;font-size:14px;background:var(--k-card,#0d1117);color:var(--k-tx,#e6edf3);border:1px solid var(--k-line,#30363d);border-radius:5px;resize:vertical}
#m4 .xe-bad.hide{display:none}
#m4 .xe-warn{color:var(--k-warn,#d29922)}
#m4 .xe-dlg{background:var(--k-card,#161b22);color:var(--k-tx,#e6edf3);border:1px solid var(--k-line,#30363d);border-radius:10px;padding:0;width:calc(100% - 24px);max-width:720px;max-height:calc(100dvh - 24px)}
#m4 .xe-dlg::backdrop{background:rgba(1,4,9,.72)}
#m4 .xe-dlg[open]{display:flex;flex-direction:column}
#m4 .xe-dh{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 12px 10px 16px;border-bottom:1px solid var(--k-line,#30363d)}
#m4 .xe-dh h3{margin:0}
#m4 .xe-x{width:40px;height:40px;background:none;border:0;color:var(--k-mu,#8b949e);font-size:18px;cursor:pointer}
#m4 .xe-db{overflow:auto;padding:14px 16px 18px}
#m4 .xe-db h4{margin:18px 0 8px;font-size:14px}
#m4 .xe-dtop{display:grid;gap:12px;grid-template-columns:minmax(0,150px) 1fr;align-items:center;margin-bottom:8px}
#m4 .xe-dimg{background:var(--k-img,#0f141b);border-radius:8px;padding:12px 8px}#m4 .xe-dimg svg{display:block;width:100%}
#m4 .xe-tb td.r{text-align:right;font-variant-numeric:tabular-nums}
#m4 .xe-tb th{text-align:left;font-weight:600;border-bottom:1px solid var(--k-line2,#21262d);padding:6px}
#m4 .xe-tb td.up{color:var(--k-up,#3fb950);font-weight:600}
#m4 .xe-scroll{overflow-x:auto}#m4 .xe-tb.cmp{min-width:420px}
#m4 .xe-loan{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:10px}
#m4 .xe-loan label{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--k-mu,#8b949e)}
#m4 .xe-loan input,#m4 .xe-loan select{width:100%;padding:8px;font-size:14px}
#m4 .xe-fine{font-size:12px;color:var(--k-mu,#6e7681);margin:6px 0}
#m4 .xe-ct{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
@media(max-width:480px){#m4 .xe-tb.cmp{min-width:0;font-size:12px}#m4 .xe-tb.cmp td,#m4 .xe-tb.cmp th{padding:5px 3px}#m4 .xe-grid{grid-template-columns:minmax(0,1fr)}#m4 .xe-dtop{grid-template-columns:minmax(0,1fr)}}
@media(prefers-reduced-motion:reduce){#m4 *{transition:none!important;animation:none!important}}`;
document.head.appendChild(css);
build();
})();
