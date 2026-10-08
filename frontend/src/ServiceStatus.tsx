import { useEffect, useState } from "react";

export default function ServiceStatus(){
  const [status,setStatus]=useState<"checking"|"ready"|"unavailable">("checking");
  useEffect(()=>{
    let active=true;
    let controller:AbortController|undefined;
    async function check(){
      controller?.abort();
      controller=new AbortController();
      const current=controller;
      const timeout=window.setTimeout(()=>current.abort(),12000);
      try{
        const base=import.meta.env.VITE_API_BASE_URL??"http://localhost:8000/api/v1";
        const url=new URL(base,window.location.href);
        url.pathname=url.pathname.replace(/\/api\/v1\/?$/,"")+"/ready";
        url.search="";url.hash="";
        const response=await fetch(url,{signal:current.signal,cache:"no-store"});
        const body=response.ok?await response.json():null;
        if(active)setStatus(body?.status==="ready"?"ready":"unavailable");
      }catch{if(active)setStatus("unavailable");}
      finally{window.clearTimeout(timeout);}
    }
    void check();
    const interval=window.setInterval(()=>{if(!document.hidden)void check();},60000);
    return()=>{active=false;controller?.abort();window.clearInterval(interval);};
  },[]);
  return <span className={"service-status service-status-"+status} role="status"><span className="live-dot"/><span className="live-label">{status==="ready"?"Servicio disponible":status==="checking"?"Consultando servicio":"Servicio no disponible"}</span></span>;
}
