import { useEffect, useState, type FormEvent } from "react";
import { api, type AuditEvent } from "./services/api";

const labels:Record<string,string>={"auth.login_succeeded":"Inicio de sesión","auth.login_failed":"Acceso fallido","auth.password_changed":"Contraseña cambiada","auth.sessions_revoked":"Sesiones cerradas","user.password_reset":"Acceso restablecido","user.created":"Usuario creado","report.created":"Reporte generado"};
export default function AuditTrail({revision}:{revision:number}){
  const [actions,setActions]=useState<string[]>([]);
  const [draft,setDraft]=useState({action:"",start:"",end:""});
  const [query,setQuery]=useState({...draft,offset:0});
  const [rows,setRows]=useState<AuditEvent[]>([]);
  const [busy,setBusy]=useState(true);
  const [error,setError]=useState("");
  const [refresh,setRefresh]=useState(0);
  useEffect(()=>{let active=true;api.auditActions().then(data=>{if(active)setActions(data);}).catch(()=>{if(active)setActions([]);});return()=>{active=false;};},[revision,refresh]);
  useEffect(()=>{let active=true;setBusy(true);setError("");setRows([]);
    api.auditLogs(query.offset,query.action,query.start,query.end).then(data=>{if(active)setRows(data);}).catch(e=>{if(active)setError(e instanceof Error?e.message:"No se pudo cargar la auditoría.");}).finally(()=>{if(active)setBusy(false);});
    return()=>{active=false;};
  },[query,revision,refresh]);
  function filter(e:FormEvent){e.preventDefault();if(draft.start&&draft.end&&draft.end<draft.start){setError("Revisa el intervalo de fechas.");return;}setQuery({...draft,offset:0});}
  return <section className="panel audit-explorer">
    <div className="panel-heading"><div><h2>Registro de auditoría</h2><p>Actividad de esta empresa · Fechas en Lima</p></div><button className="btn btn-light" disabled={busy} onClick={()=>setRefresh(v=>v+1)}>Actualizar</button></div>
    <form className="audit-filters" onSubmit={filter}><label>Evento<select value={draft.action} onChange={e=>setDraft({...draft,action:e.target.value})}><option value="">Todos los eventos</option>{actions.map(action=><option key={action} value={action}>{labels[action]??action}</option>)}</select></label><label>Desde<input type="date" value={draft.start} max={draft.end||undefined} onChange={e=>setDraft({...draft,start:e.target.value})}/></label><label>Hasta<input type="date" value={draft.end} min={draft.start||undefined} onChange={e=>setDraft({...draft,end:e.target.value})}/></label><button className="btn btn-primary" disabled={busy}>Filtrar</button><button type="button" className="btn btn-light" disabled={busy} onClick={()=>{const empty={action:"",start:"",end:""};setDraft(empty);setQuery({...empty,offset:0});}}>Limpiar</button></form>
    {error&&<p className="inline-error" role="alert">{error}</p>}
    {busy?<p className="table-empty" role="status">Cargando eventos…</p>:!rows.length&&!error?<p className="table-empty">No hay eventos para estos filtros.</p>:<div className="table-wrap"><table><thead><tr><th>FECHA</th><th>EVENTO</th><th>USUARIO</th><th>REFERENCIA</th><th>DETALLE</th></tr></thead><tbody>{rows.slice(0,25).map(row=><tr key={row.id}><td>{new Date(row.created_at).toLocaleString("es-PE",{timeZone:"America/Lima"})}</td><td><strong>{labels[row.action]??row.action}</strong><small className="movement-reference">#{row.id} · {row.action}</small></td><td>{row.actor_email??"Sistema / usuario no disponible"}</td><td>{row.entity_type} {row.entity_id?"#"+row.entity_id:""}</td><td>{row.details&&Object.keys(row.details).length?<details><summary>Ver datos</summary><dl className="audit-details">{Object.entries(row.details).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{typeof value==="object"?JSON.stringify(value,null,2):String(value)}</dd></div>)}</dl></details>:"Sin datos adicionales"}</td></tr>)}</tbody></table></div>}
    <div className="catalog-pagination"><span>Página {query.offset/25+1}</span><div><button className="btn btn-light" disabled={busy||query.offset===0} onClick={()=>setQuery({...query,offset:Math.max(0,query.offset-25)})}>Anterior</button><button className="btn btn-light" disabled={busy||!!error||rows.length<=25} onClick={()=>setQuery({...query,offset:query.offset+25})}>Siguiente</button></div></div>
  </section>;
}
