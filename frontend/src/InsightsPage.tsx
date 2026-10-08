import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { api, type Insight, type InsightTrace } from "./services/api";
import { dashboardWindow, shiftDay } from "./services/dashboard";
import InsightEvidence from "./InsightEvidence";

export default function InsightsPage({canGenerate=false}:{canGenerate?:boolean}) {
  const yesterday=shiftDay(dashboardWindow(1).end,-1);
  const [end,setEnd]=useState(yesterday);
  const [items,setItems]=useState<Insight[]>([]);
  const [page,setPage]=useState(0);
  const [revision,setRevision]=useState(0);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    let current=true;setLoading(true);setError("");
    api.insights(page*25).then(rows=>{if(current)setItems(rows);})
      .catch(e=>{if(current)setError(e instanceof Error?e.message:"No se pudieron cargar los insights");})
      .finally(()=>{if(current)setLoading(false);});
    return()=>{current=false;};
  },[page,revision]);
  async function generate(){
    if(!end||end>yesterday){setError("Selecciona una fecha hasta ayer.");return;}
    setBusy(true);setError("");setNotice("");
    try{
      const result=await api.generateInsights(end);
      setNotice(`${result.matched} reglas activadas · ${result.created} nuevos · ${result.updated} actualizados · ${result.unchanged} sin cambios · ${result.resolved} resueltos.`);
      setPage(0);setRevision(v=>v+1);
    }catch(e){setError(e instanceof Error?e.message:"No se pudieron generar insights");}
    finally{setBusy(false);}
  }
  return <section className="panel insights-page">
    <div className="data-toolbar"><div><strong>Hallazgos comerciales explicables</strong><p>Reglas con evidencia y fecha de evaluación</p></div></div>
    <div className="sales-filters"><label>Último día de la semana analizada<input type="date" max={yesterday} required value={end} disabled={busy} onChange={e=>setEnd(e.target.value)}/></label>{canGenerate&&<button className="btn btn-primary" onClick={generate} disabled={busy||!end}><Sparkles size={15}/>{busy?"Analizando…":"Evaluar reglas"}</button>}</div>
    <p className="dashboard-filter-explanation">Se comparan siete días completos con los siete anteriores. El stock se revisa con las existencias actuales. La evaluación se ejecuta al pulsar el botón; repetirla actualiza el mismo registro del periodo.</p>
    {notice&&<p className="catalog-notice" role="status">{notice}</p>}
    {error&&<div className="inline-error" role="alert">{error} <button className="text-button" onClick={()=>setRevision(v=>v+1)}>Recargar historial</button></div>}
    {loading?<div className="table-empty" role="status">Cargando historial…</div>:items.length?<div className="insight-list">{items.slice(0,25).map(item=><article className="insight-card" key={item.id}><div className="insight-badge warning"><Sparkles size={18}/></div><div className="insight-copy"><div className="insight-title-row"><strong>{item.title}</strong><span className={`status ${item.status==="resolved"?"status-inactive":"status-active"}`}>{item.status==="resolved"?"Resuelto al reevaluar":"Detectado al evaluar"}</span></div><p>{item.message}</p><details><summary>Ver evidencia y periodo</summary><InsightEvidence item={item}/><Trace id={item.id}/></details><small>Última evaluación: {new Date(item.evaluated_at??item.created_at).toLocaleString("es-PE",{timeZone:"America/Lima"})} · Lima</small>{item.resolved_at&&<small>Resolución: {new Date(item.resolved_at).toLocaleString("es-PE",{timeZone:"America/Lima"})}</small>}</div></article>)}</div>:!error&&<div className="table-empty">Todavía no hay hallazgos. Una evaluación sin alertas también es un resultado válido.</div>}
    <div className="catalog-pagination"><span>Página {page+1} · 25 registros por página</span><div><button className="btn btn-light" disabled={busy||loading||page===0} onClick={()=>setPage(p=>p-1)}>Anterior</button><button className="btn btn-light" disabled={busy||loading||items.length<=25} onClick={()=>setPage(p=>p+1)}>Siguiente</button></div></div>
  </section>;
}

function Trace({id}:{id:number}){
 const [data,setData]=useState<InsightTrace|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function load(){setBusy(true);setError("");try{setData(await api.insightTrace(id));}catch(e){setError(e instanceof Error?e.message:"No se pudo consultar el análisis");}finally{setBusy(false);}}
 return <section className="insight-evidence"><button className="btn btn-light" disabled={busy} onClick={load}>{busy?"Consultando…":"Consultar datos del análisis"}</button>{error&&<p role="alert" className="inline-error">{error}</p>}{data&&(data.available?<><p>Análisis #{data.analysis_id} · Conjunto de datos #{data.dataset_id}</p><p className="form-note">Copia de los valores utilizados al evaluar la regla. Las reglas de stock guardan hasta 50 productos del inventario general.</p><div className="table-wrap"><table><thead><tr><th>OBSERVACIÓN</th><th>VALOR</th><th>UNIDAD</th></tr></thead><tbody>{data.observations.map((row,index)=><tr key={index}><td>{row.source_ref==="previous_week"?"Semana anterior":row.source_ref==="current_week"?"Semana evaluada":row.source_ref.replace("product:","Producto #")}</td><td>{Number(row.numeric_value).toLocaleString("es-PE",{maximumFractionDigits:6})}</td><td>{row.unit}</td></tr>)}</tbody></table></div></>:<p>Registro histórico sin análisis vinculado. Una nueva evaluación incorporará el vínculo si la regla vuelve a activarse.</p>)}</section>;
}
