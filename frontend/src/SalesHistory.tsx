import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { api, type Sale } from "./services/api";
import SaleForm from "./SaleForm";
import SaleReceipt from "./SaleReceipt";

export default function SalesHistory({canCreate=false}:{canCreate?:boolean}) {
  const [rows,setRows]=useState<Sale[]>([]);
  const [page,setPage]=useState(0);
  const [start,setStart]=useState("");
  const [end,setEnd]=useState("");
  const [status,setStatus]=useState("");
  const [show,setShow]=useState(false);
  const [selected,setSelected]=useState<number|null>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  const [revision,setRevision]=useState(0);
  useEffect(()=>{
    let current=true; setError(""); setLoading(true);
    if(start&&end&&end<start){setError("La fecha final debe ser igual o posterior a la inicial.");setRows([]);setLoading(false);return;}
    api.salesPage(page*25,start,end,status).then(data=>{if(current)setRows(data);})
      .catch(e=>{if(current){setRows([]);setError(e instanceof Error?e.message:"No se pudieron cargar las ventas");}})
      .finally(()=>{if(current)setLoading(false);});
    return()=>{current=false;};
  },[page,start,end,status,revision]);
  const money=(sale:Sale)=>new Intl.NumberFormat("es-PE",{style:"currency",currency:sale.currency}).format(Number(sale.total));
  return <>
    <section className="panel data-panel" aria-busy={loading}>
      <div className="data-toolbar"><div><strong>Historial de ventas</strong><p>Consulta el detalle, los pagos y el recibo de cada operación</p></div>{canCreate&&<button className="btn btn-primary" onClick={()=>setShow(true)}><Plus size={15}/> Nueva venta</button>}</div>
      <div className="sales-filters"><label>Desde<input type="date" value={start} max={end||undefined} onChange={e=>{setStart(e.target.value);setPage(0);}}/></label><label>Hasta<input type="date" value={end} min={start||undefined} onChange={e=>{setEnd(e.target.value);setPage(0);}}/></label><label>Estado<select value={status} onChange={e=>{setStatus(e.target.value);setPage(0);}}><option value="">Todos</option><option value="confirmed">Confirmadas</option><option value="voided">Anuladas</option></select></label><button className="btn btn-light" onClick={()=>{setStart("");setEnd("");setStatus("");setPage(0);}}>Limpiar filtros</button></div>
      {error&&<div className="inline-error" role="alert">{error} <button className="text-button" onClick={()=>setRevision(v=>v+1)}>Reintentar</button></div>}
      <div className="table-wrap"><table><thead><tr><th>VENTA</th><th>FECHA</th><th>CLIENTE</th><th>VENDEDOR</th><th>TOTAL</th><th>ESTADO</th><th>ACCIONES</th></tr></thead><tbody>{!loading&&rows.slice(0,25).map(row=><tr key={row.id}><td><strong>#{String(row.id).padStart(5,"0")}</strong></td><td>{new Date(row.sold_at).toLocaleString("es-PE",{dateStyle:"medium",timeStyle:"short"})}</td><td>{row.customer_name??"Cliente general"}</td><td>{row.seller_name}</td><td>{money(row)}</td><td><span className={`status ${row.status==="confirmed"?"status-active":"status-inactive"}`}>{row.status==="confirmed"?"Confirmada":row.status==="voided"?"Anulada":row.status}</span></td><td><button className="text-button" onClick={()=>setSelected(row.id)}>Ver recibo</button></td></tr>)}</tbody></table></div>
      {loading?<div className="table-empty" role="status">Cargando ventas…</div>:!rows.length&&!error&&<div className="table-empty">No hay ventas que coincidan con estos filtros.</div>}
      <div className="catalog-pagination"><span>Página {page+1} · 25 ventas por página</span><div><button className="btn btn-light" disabled={loading||page===0} onClick={()=>setPage(p=>p-1)}>Anterior</button><button className="btn btn-light" disabled={loading||rows.length<=25} onClick={()=>setPage(p=>p+1)}>Siguiente</button></div></div>
    </section>
    {show&&<SaleForm onClose={()=>setShow(false)} onCreated={()=>{setShow(false);setPage(0);setRevision(v=>v+1);}}/>}
    {selected!==null&&<SaleReceipt id={selected} canVoid={canCreate} onClose={()=>setSelected(null)} onVoided={()=>setRevision(v=>v+1)}/>}
  </>;
}
