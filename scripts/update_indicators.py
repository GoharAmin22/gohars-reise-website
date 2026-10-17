#!/usr/bin/env python3
"""Fetch official monthly rates. Fail closed on missing/ambiguous Eurostat observations."""
import datetime,json,pathlib,urllib.parse,urllib.request,sys,re
TARGET=pathlib.Path(__file__).resolve().parents[1]/"deutschland-monitor"/"indicators.json"
BASE="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
SPECS={
"inflation":{"dataset":"prc_hicp_manr","filters":{"geo":"DE","coicop":"CP00"},"unit":"percent","label":"Inflation (HVPI, Vorjahresmonat)","bounds":(-20,100)},
"unemployment":{"dataset":"une_rt_m","filters":{"geo":"DE","sex":"T","age":"Y15-74","unit":"PC_ACT","s_adj":"SA"},"unit":"percent","label":"Erwerbslosenquote (saisonbereinigt)","bounds":(0,50)}
}
def fetch(spec):
    url=BASE+spec["dataset"]+"?"+urllib.parse.urlencode({**spec["filters"],"lang":"EN"})
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Deutschland-Monitor/1.0"}),timeout=55) as r:d=json.load(r)
    ids=d["id"]; dims=d["dimension"]; sizes=d["size"]
    selected={}
    for key,value in spec["filters"].items():
        if key not in dims or value not in dims[key]["category"]["index"]:raise ValueError("Unknown category "+key+"="+value)
        selected[key]=dims[key]["category"]["index"][value]
    if set(ids)-set(selected)-{"time"}:raise ValueError("Unfiltered dimensions "+str(set(ids)-set(selected)-{"time"}))
    points=[]
    for period,pos in dims["time"]["category"]["index"].items():
        if not re.fullmatch(r"20\\d{2}-\\d{2}",period):continue
        ix=0
        for dim,size in zip(ids,sizes):ix=ix*size+(pos if dim=="time" else selected[dim])
        val=d["value"].get(str(ix))
        if isinstance(val,(float,int)) and spec["bounds"][0]<=val<=spec["bounds"][1]:points.append((period,val))
    if not points:raise ValueError("No usable monthly observations")
    period,val=max(points)
    return {"value":val,"period":period,"unit":spec["unit"],"label":spec["label"],"dataset":spec["dataset"],"sourceUrl":"https://ec.europa.eu/eurostat/databrowser/view/"+spec["dataset"]+"/default/table?lang=en"}
def main():
    previous=json.loads(TARGET.read_text()) if TARGET.exists() else {"metrics":{}}
    metrics=previous.get("metrics",{}).copy()
    for key,spec in SPECS.items():
        try:metrics[key]=fetch(spec);print("Updated",key,metrics[key]["period"])
        except Exception as e:print("Unavailable",key,e,file=sys.stderr)
    if not metrics:raise RuntimeError("No verified data available")
    if previous.get("metrics")==metrics:return
    TARGET.write_text(json.dumps({"source":"Eurostat","metrics":metrics,"checkedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")},indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":
    try:main()
    except Exception as e:print(e,file=sys.stderr);sys.exit(1)
