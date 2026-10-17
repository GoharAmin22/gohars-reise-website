#!/usr/bin/env python3
"""Refresh demographic annual figures from Eurostat demo_gind. No fabricated fallback."""
import datetime, json, pathlib, re, sys, urllib.request
TARGET=pathlib.Path(__file__).resolve().parents[1]/"deutschland-monitor"/"demography.json"
URL="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_gind?geo=DE&freq=A&lang=EN"
def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"Deutschland-Monitor/1.0"})
    with urllib.request.urlopen(req,timeout=60) as response: data=json.load(response)
    dims=data["dimension"]; ids=data["id"]; sizes=data["size"]
    indicator_key=next((x for x in ids if x.lower() in ("indic_de","indic")),None)
    if not indicator_key:raise ValueError("Indicator dimension missing")
    labels=dims[indicator_key]["category"]["label"]
    patterns={
      "births":[r"^live births",r"^births - total"],
      "deaths":[r"^deaths - total",r"^deaths$"],
      "immigration":[r"^immigration$",r"^immigrants$"],
      "emigration":[r"^emigration$",r"^emigrants$"]
    }
    codes={}
    for key, pats in patterns.items():
        matches=[code for code,label in labels.items() if any(re.search(p,label,re.I) for p in pats)]
        if len(matches)==1:codes[key]=matches[0]
    if "births" not in codes or "deaths" not in codes:
        raise ValueError("Birth/death indicators not identified unambiguously: "+str(labels))
    def get(code,year):
        coords=[]
        for dim in ids:
            val=code if dim==indicator_key else year if dim=="time" else "DE" if dim=="geo" else "A" if dim=="freq" else None
            if val is None:raise ValueError("Unexpected dimension: "+dim)
            coords.append(dims[dim]["category"]["index"][val])
        offset=0
        for i,size in zip(coords,sizes):offset=offset*size+i
        val=data["value"].get(str(offset))
        return round(val) if isinstance(val,(int,float)) and val>=0 else None
    years=sorted((y for y in dims["time"]["category"]["index"] if re.fullmatch(r"20\d{2}",y)),reverse=True)
    metrics={}
    for key,code in codes.items():
        valid=[(year,get(code,year)) for year in years]
        valid=[(year,val) for year,val in valid if val is not None]
        if valid:
            year,val=valid[0]
            if key in ("births","deaths") and not 200000<=val<=2000000:raise ValueError("Implausible "+key)
            metrics[key]={"value":val,"year":year,"indicator":code,"label":labels[code]}
    if not all(x in metrics for x in ("births","deaths")):raise ValueError("Required metrics missing")
    payload={"source":"Eurostat","dataset":"demo_gind","geo":"DE","periodType":"annual","metrics":metrics,"sourceUrl":"https://ec.europa.eu/eurostat/databrowser/view/demo_gind/default/table?lang=en","checkedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    if TARGET.exists():
        old=json.loads(TARGET.read_text(encoding="utf-8"))
        if old.get("metrics")==metrics:print("No changes");return
    TARGET.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Updated",",".join(metrics))
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("Demographic update failed; retaining last verified values:",exc,file=sys.stderr)
        sys.exit(1)
