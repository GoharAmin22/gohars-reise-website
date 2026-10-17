#!/usr/bin/env python3
"""Refresh Germany general-government annual revenue/expenditure from Eurostat."""
import json, datetime, urllib.request, pathlib, sys
BASE="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10a_main"
TARGET=pathlib.Path(__file__).resolve().parents[1]/"deutschland-monitor"/"data.json"
def series(item):
    url=f"{BASE}?geo=DE&sector=S13&unit=MIO_EUR&na_item={item}&lang=EN"
    req=urllib.request.Request(url,headers={"User-Agent":"Deutschland-Monitor/1.0"})
    with urllib.request.urlopen(req,timeout=35) as r: data=json.load(r)
    ids=data["id"]; sizes=data["size"]; dims=data["dimension"]; values=data["value"]
    selected={k: dims[k]["category"]["index"][v] for k,v in (("geo","DE"),("sector","S13"),("unit","MIO_EUR"),("na_item",item)) if k in ids}
    tmap=dims["time"]["category"]["index"]
    out={}
    for year,pos in tmap.items():
        if not (year.isdigit() and len(year)==4):continue
        coords=[]
        for dim in ids:coords.append(pos if dim=="time" else selected[dim])
        idx=0
        for coordinate,size in zip(coords,sizes):idx=idx*size+coordinate
        v=values.get(str(idx))
        if isinstance(v,(float,int)) and v>0:out[year]=v
    return out
try:
    revenues=series("TR")
    expenses=series("TE")
    years=sorted(set(revenues)&set(expenses),reverse=True)
    if not years:raise ValueError("No common year")
    year=years[0]
    inc=revenues[year]*1_000_000
    exp=expenses[year]*1_000_000
    if not (500e9<inc<5e12 and 500e9<exp<5e12):raise ValueError("Unexpected values")
    payload={"source":"Eurostat","dataset":"gov_10a_main","geo":"DE","sector":"S13","unit":"EUR","period":year,"periodType":"annual","income":round(inc),"expense":round(exp),"checkedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),"sourceUrl":"https://ec.europa.eu/eurostat/databrowser/view/gov_10a_main/default/table?lang=en"}
    # Keep timestamp stable when numbers and reporting period did not change.
    if TARGET.exists():
        old=json.loads(TARGET.read_text(encoding="utf-8"))
        if all(old.get(k)==payload[k] for k in ("period","income","expense","dataset")):
            print("No new official values");sys.exit(0)
    TARGET.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Updated Eurostat {year}")
except Exception as exc:
    print(f"Data refresh failed, keeping last verified data: {exc}",file=sys.stderr)
    sys.exit(1)
