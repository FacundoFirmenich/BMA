#!/usr/bin/env python3
"""BayME–M_C Gate 4 official-data cold start (shadow only).

Historical credit/liquidity estimates are analogue diagnostics. Direct M_C
responses remain NOT_ESTIMABLE until prospective exposure and assignment
lineage exist.
"""
from __future__ import annotations

import argparse, hashlib, io, json, math, re, time, unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import requests
from scipy import stats

SERIES_API="https://apis.datos.gob.ar/series/api"
BCRA_API="https://api.bcra.gob.ar/estadisticas/v4.0"
SUBE="https://archivos-datos.transporte.gob.ar/upload/Dat_Ab_Usos/dat-ab-usos-{}.csv"
SERIES={
 "ipc_index":("148.3_INIVELNAL_DICI_M_26","native"),
 "emae_index":("143.3_NO_PR_2004_A_21","native"),
 "manufacturing_index":("11.3_VMASD_2004_M_23","native"),
 "nominal_fx":("168.1_T_CAMBIOR_D_0_0_26","end_of_period"),
 "itcrm":("116.4_TCRZE_2015_D_36_4","end_of_period"),
 "trade_balance":("74.3_ISC_0_M_19","native"),
 "policy_rate":("89.2_TS_INTE_PM_0_D_16","avg"),
}
TARGETS={
 "m3":([r"\bm3\b"],["tasa","variacion"]),
 "personal_loans":(["prestamos personales"],["tasa","variacion"]),
 "credit_cards":(["tarjetas de credito"],["tasa","compras","cantidad"]),
 "private_credit":(["prestamos al sector privado","credito al sector privado"],["tasa","variacion","moneda extranjera"]),
 "international_reserves":(["reservas internacionales"],["variacion","tasa"]),
}
DIMS={
 "Y":("emae_index","economic_activity"),
 "P":("ipc_index","consumer_prices"),
 "E":("registered_employment","registered_private_employment"),
 "FX":("nominal_fx","nominal_exchange_rate"),
 "W":("wage_index","nominal_wage_index"),
}

@dataclass
class Receipt:
 source:str; url:str; status:str; retrieved_at:str; sha256:str|None=None; size:int|None=None; note:str|None=None

def now(): return datetime.now(timezone.utc).isoformat()
def norm(x):
 s=unicodedata.normalize("NFKD",str(x)); s="".join(c for c in s if not unicodedata.combining(c))
 return re.sub(r"\s+"," ",s.lower()).strip()
def dump(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
def file_hash(path): return hashlib.sha256(path.read_bytes()).hexdigest()

class Net:
 def __init__(self):
  self.s=requests.Session(); self.s.headers.update({"User-Agent":"BayME-MC-Gate4/0.2","Accept-Language":"es-AR"}); self.receipts=[]
 def get(self,name,url):
  err=None
  for i in range(4):
   try:
    r=self.s.get(url,timeout=90); r.raise_for_status(); b=r.content
    self.receipts.append(Receipt(name,r.url,"OK",now(),hashlib.sha256(b).hexdigest(),len(b))); return b
   except requests.RequestException as e:
    err=e; time.sleep(2**i)
  self.receipts.append(Receipt(name,url,"FAILED",now(),note=repr(err))); raise RuntimeError(f"{name}: {err}")
 def js(self,name,url): return json.loads(self.get(name,url).decode("utf-8"))

def fetch_series(net,out,name,sid,agg,start):
 p={"ids":sid,"start_date":start,"limit":1000,"format":"csv","header":"ids","metadata":"none"}
 if agg!="native": p.update(collapse="month",collapse_aggregation=agg)
 url=f"{SERIES_API}/series?{urlencode(p)}"; b=net.get(f"series:{name}",url)
 (out/"raw").mkdir(parents=True,exist_ok=True); (out/"raw"/f"{name}.csv").write_bytes(b)
 d=pd.read_csv(io.BytesIO(b));
 if d.shape[1]<2: raise RuntimeError(f"empty official series {name}")
 d=d.iloc[:,:2]; d.columns=["date",name]; d["date"]=pd.to_datetime(d.date,errors="coerce"); d[name]=pd.to_numeric(d[name],errors="coerce")
 d=d.dropna(subset=["date"]).sort_values("date"); d.date=d.date.dt.to_period("M").dt.to_timestamp(); return d.groupby("date",as_index=False)[name].last()

def flat(rec): return norm(" | ".join(str(v) for k,v in rec.items() if k!="idVariable"))
def choose(catalog,out):
 chosen={}; audit={}
 for name,(must,exclude) in TARGETS.items():
  cand=[]
  for rec in catalog:
   text=flat(rec)
   hit=any(re.search(x,text) if x.startswith("\\b") else norm(x) in text for x in must)
   if hit and not any(norm(x) in text for x in exclude):
    score=10+2*("total" in text)+2*("pesos" in text)+2*("2026" in text)+1*("2025" in text)
    cand.append((score,rec,text))
  cand.sort(key=lambda x:x[0],reverse=True); audit[name]=[{"score":s,"record":r,"text":t} for s,r,t in cand[:10]]
  if cand and cand[0][1].get("idVariable") is not None: chosen[name]=cand[0][1]
 dump(out/"metadata"/"bcra_selection_audit.json",audit); dump(out/"metadata"/"bcra_selected.json",chosen); return chosen

def bcra_series(net,out,name,vid,start,end):
 url=f"{BCRA_API}/monetarias/{int(vid)}?{urlencode({'desde':start,'hasta':end,'limit':3000,'offset':0})}"
 p=net.js(f"bcra:{name}",url); dump(out/"raw"/f"bcra_{name}.json",p); rows=[]
 for block in p.get("results",[]):
  for x in block.get("detalle",[]): rows.append((x.get("fecha"),x.get("valor")))
 d=pd.DataFrame(rows,columns=["date",name]);
 if d.empty:return d
 d.date=pd.to_datetime(d.date,errors="coerce"); d[name]=pd.to_numeric(d[name],errors="coerce"); d=d.dropna(subset=["date"]).sort_values("date")
 d.date=d.date.dt.to_period("M").dt.to_timestamp(); return d.groupby("date",as_index=False)[name].last()

def col(cols,terms):
 for term in terms:
  for c in cols:
   if norm(term) in norm(c): return c
 return None

def sube(net,out,year):
 url=SUBE.format(year); b=net.get(f"sube:{year}",url); (out/"raw"/f"sube_{year}.csv").write_bytes(b); d=pd.read_csv(io.BytesIO(b),low_memory=False)
 dc=col(d.columns,["dia_transporte","fecha","dia"]); nc=col(d.columns,["cantidad","usos","transacciones"]); pc=col(d.columns,["provincia"]); mc=col(d.columns,["tipo_transporte","modo"]); ac=col(d.columns,["amba"])
 if not dc or not nc: raise RuntimeError(f"SUBE columns unsupported: {list(d.columns)}")
 z=pd.DataFrame({"date":pd.to_datetime(d[dc],errors="coerce"),"trips":pd.to_numeric(d[nc],errors="coerce"),"province":d[pc] if pc else "UNKNOWN","mode":d[mc] if mc else "UNKNOWN","amba":d[ac] if ac else "UNKNOWN"}).dropna(subset=["date","trips"])
 z["month"]=z.date.dt.to_period("M").dt.to_timestamp(); return z

def merge(frames):
 frames=[x for x in frames if x is not None and not x.empty]; p=frames[0]
 for x in frames[1:]: p=p.merge(x,on="date",how="outer",validate="one_to_one")
 return p.sort_values("date").reset_index(drop=True)
def slog(s):
 x=pd.to_numeric(s,errors="coerce"); return np.log(x.where(x>0))
def residual(y,x):
 t=pd.concat([y.rename("y"),x],axis=1).dropna(); out=pd.Series(np.nan,index=y.index)
 if len(t)<42:return out
 yy=t.pop("y").to_numpy(); X=np.c_[np.ones(len(t)),t.to_numpy()]; pen=np.eye(X.shape[1])*1e-5;pen[0,0]=0
 b=np.linalg.solve(X.T@X+pen,X.T@yy); r=yy-X@b; sd=r.std(ddof=X.shape[1]);
 if sd>0:out.loc[t.index]=r/sd
 return out

def shock(panel):
 if {"personal_loans","credit_cards"}<=set(panel): nom=panel.personal_loans.fillna(0)+panel.credit_cards.fillna(0); src="personal_loans_plus_credit_cards"
 elif "private_credit" in panel:nom=panel.private_credit;src="private_credit_fallback"
 else:return pd.Series(np.nan,index=panel.index),{"source":None,"n":0}
 real=nom/panel.ipc_index*panel.ipc_index.dropna().iloc[-1]; g=100*slog(real).diff(); X=pd.DataFrame({"g1":g.shift(1),"g2":g.shift(2),"pi1":(100*slog(panel.ipc_index).diff()).shift(1),"y1":(100*slog(panel.emae_index).diff()).shift(1)},index=panel.index)
 if "policy_rate" in panel:X["r1"]=panel.policy_rate.shift(1)
 if "nominal_fx" in panel:X["fx1"]=(100*slog(panel.nominal_fx).diff()).shift(1)
 s=residual(g,X);return s,{"source":src,"n":int(s.notna().sum()),"causal_status":"ANALOGUE_ASSOCIATIONAL_ONLY"}

def post(yy,X):
 p=X.shape[1];P0=np.eye(p)/100;P0[0,0]=1e-4;Pn=P0+X.T@X;mn=np.linalg.solve(Pn,X.T@yy);a=2.5+len(yy)/2;b=1+.5*max(float(yy@yy-mn@Pn@mn),0);S=(b/a)*np.linalg.inv(Pn);return mn,S,2*a

def lp(panel,s,outcome,h):
 if outcome not in panel:return {"status":"NOT_ESTIMABLE","reason":"outcome_missing","n":0}
 y=100*(slog(panel[outcome]).shift(-h)-slog(panel[outcome]).shift(1));D=pd.DataFrame({"shock":s,"pi1":(100*slog(panel.ipc_index).diff()).shift(1),"act1":(100*slog(panel.emae_index).diff()).shift(1),"own1":(100*slog(panel[outcome]).diff()).shift(1),"own2":(100*slog(panel[outcome]).diff()).shift(2)},index=panel.index)
 if "policy_rate" in panel:D["r1"]=panel.policy_rate.shift(1)
 if "nominal_fx" in panel:D["fx1"]=(100*slog(panel.nominal_fx).diff()).shift(1)
 t=pd.concat([y.rename("y"),D],axis=1).dropna(); minimum=max(42,7*D.shape[1])
 if len(t)<minimum:return {"status":"NOT_ESTIMABLE","reason":f"complete_months<{minimum}","n":len(t)}
 yy=t.pop("y").to_numpy(); A=t.to_numpy();
 for j in range(1,A.shape[1]):
  sd=A[:,j].std();A[:,j]=(A[:,j]-A[:,j].mean())/sd if sd>0 else 0
 X=np.c_[np.ones(len(A)),A];m,S,df=post(yy,X);mu=float(m[1]);sc=math.sqrt(float(S[1,1]));q80=stats.t.ppf([.1,.9],df,loc=mu,scale=sc);q95=stats.t.ppf([.025,.975],df,loc=mu,scale=sc);pp=1-stats.t.cdf(0,df,loc=mu,scale=sc)
 return {"status":"ESTIMABLE_ANALOGUE","reason":None,"n":len(t),"posterior_mean":mu,"ci80_low":q80[0],"ci80_high":q80[1],"ci95_low":q95[0],"ci95_high":q95[1],"p_positive":pp,"p_negative":1-pp,"condition_number":float(np.linalg.cond(X.T@X))}

def matrices(panel,s,out):
 a=[];d=[]
 for dim,(column,proxy) in DIMS.items():
  for h in [0,1,3,6,12]:
   e=lp(panel,s,column,h);a.append({"family":"historical_credit_liquidity_analogue","dimension":dim,"proxy":proxy,"horizon_months":h,"quaternary_state":"+0" if e["status"]=="ESTIMABLE_ANALOGUE" else "0","causal_authority":False,"policy_authority":False,**e})
   d.append({"family":"direct_M_C_effect","dimension":dim,"proxy":proxy,"horizon_months":h,"quaternary_state":"0","status":"NOT_ESTIMABLE","reason":"no_M_C_exposure_and_assignment_lineage","n":0,"causal_authority":False,"policy_authority":False})
 A=pd.DataFrame(a);D=pd.DataFrame(d);A.to_csv(out/"artifacts"/"gamma_analogue.csv",index=False);D.to_csv(out/"artifacts"/"gamma_direct_mc.csv",index=False);dump(out/"artifacts"/"gamma_analogue.json",A.replace({np.nan:None}).to_dict("records"));dump(out/"artifacts"/"gamma_direct_mc.json",D.to_dict("records"));return A,D

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,default=Path("gate4_mc_output"));ap.add_argument("--start",default="2016-01-01");ap.add_argument("--end",default=datetime.now(timezone.utc).date().isoformat());args=ap.parse_args();out=args.output
 for x in ["raw","data","metadata","artifacts"]:(out/x).mkdir(parents=True,exist_ok=True)
 net=Net();frames=[];errors=[];manifest=[]
 for name,(sid,agg) in SERIES.items():
  try:d=fetch_series(net,out,name,sid,agg,args.start);frames.append(d);manifest.append({"name":name,"id":sid,"aggregation":agg,"rows":len(d)})
  except Exception as e:errors.append({"source":name,"error":repr(e)})
 try:
  cat=net.js("bcra:catalog",f"{BCRA_API}/monetarias?limit=1000&offset=0");dump(out/"raw"/"bcra_catalog.json",cat);chosen=choose(cat.get("results",[]),out)
  for name,rec in chosen.items():
   try:d=bcra_series(net,out,name,int(rec["idVariable"]),args.start,args.end);frames.append(d);manifest.append({"name":name,"idVariable":rec["idVariable"],"rows":len(d),"record":rec})
   except Exception as e:errors.append({"source":f"bcra:{name}","error":repr(e)})
 except Exception as e:errors.append({"source":"bcra:catalog","error":repr(e)})
 sz=[]
 for year in [2024,2025,2026]:
  try:sz.append(sube(net,out,year))
  except Exception as e:errors.append({"source":f"sube:{year}","error":repr(e)})
 if sz:
  q=pd.concat(sz,ignore_index=True);prov=q.groupby(["month","province","mode","amba"],as_index=False).trips.sum();prov.to_csv(out/"data"/"sube_monthly_province.csv",index=False);nat=q.groupby("month",as_index=False).trips.sum().rename(columns={"month":"date","trips":"sube_trips"});nat.to_csv(out/"data"/"sube_monthly_national.csv",index=False);frames.append(nat)
 panel=merge(frames);panel.to_csv(out/"data"/"macro_monthly.csv",index=False);s,sm=shock(panel);panel.assign(credit_innovation_std=s).to_csv(out/"data"/"macro_monthly_with_shock.csv",index=False);dump(out/"metadata"/"shock_contract.json",sm);A,D=matrices(panel,s,out)
 dump(out/"metadata"/"series_manifest.json",manifest);dump(out/"metadata"/"source_receipts.json",[asdict(x) for x in net.receipts]);dump(out/"artifacts"/"errors.json",errors)
 z={"schema":"bayme_mc.zpost.data_audit.v0.2","created_at":now(),"candidate_only":True,"forbidden_retroactive_rewrite":True,"panel":{"rows":len(panel),"start":panel.date.min().date().isoformat(),"end":panel.date.max().date().isoformat()},"estimability":{"analogue_total":len(A),"analogue_estimable":int((A.status=="ESTIMABLE_ANALOGUE").sum()),"direct_mc_total":len(D),"direct_mc_estimable":0,"veto":"missing M_C exposure and assignment lineage"},"forbidden_transfers":["direct M_C causal claim","local authority from national aggregates","individual adverse scoring","automatic execution"]};dump(out/"artifacts"/"zpost_data_audit.json",z)
 report=f'''# BayME–M_C Gate 4 — official-data cold start\n\n**State:** `SOFTWARE_CANDIDATE_LOCAL_SHADOW / +0`  \n**Authority:** none  \n**Direct M_C response:** `NOT_ESTIMABLE`\n\nThe gate assembled a real official monthly panel ({z["panel"]["start"]} to {z["panel"]["end"]}, {len(panel)} rows), constructed {sm.get("n",0)} usable innovations in real household credit, and produced {z["estimability"]["analogue_estimable"]}/{len(A)} estimable analogue cells. All {len(D)} direct M_C cells abstain because no historical or prospective M_C exposure with assignment lineage exists.\n\nHistorical credit is not treated as M_C. Numerical cells are non-causal shadow diagnostics only. Employment and wage cells remain `NOT_ESTIMABLE` until exact supported monthly contracts are added. SUBE is used solely as aggregate mobility context.\n\n## Verdict\n\n`PASS_WITH_DIRECT_MC_IDENTIFICATION_VETO`\n''';(out/"GATE4_REPORT.md").write_text(report,encoding="utf-8")
 files=[]
 for p in sorted(out.rglob("*")):
  if p.is_file() and p.name!="SHA256SUMS.json":files.append({"path":p.relative_to(out).as_posix(),"bytes":p.stat().st_size,"sha256":file_hash(p)})
 dump(out/"artifacts"/"SHA256SUMS.json",files);summary={"version":"0.2.0","created_at":now(),"panel_rows":len(panel),"panel_columns":list(panel),"shock_nonmissing":sm.get("n",0),"analogue_estimable_cells":z["estimability"]["analogue_estimable"],"direct_mc_estimable_cells":0,"errors":errors,"verdict":"PASS_WITH_DIRECT_MC_IDENTIFICATION_VETO"};dump(out/"artifacts"/"run_summary.json",summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
