import ReportGroups, { reportTitle } from "./ReportGroups";
import { useEffect,useState,type FormEvent } from "react";
import { Download,FileBarChart2 } from "lucide-react";
import { api,type Report,type ReportSnapshot,type ReportFilterOptions,type ReportFilterKey,type ReportKind } from "./services/api";
import ReportPrint from "./ReportPrint";
import { dashboardWindow } from "./services/dashboard";

const money=(value:string,currency:string)=>new Intl.NumberFormat("es-PE",{style:"currency",currency}).format(Number(value));
export default function ReportsPage(){
  const [printing,setPrinting]=useState(false);
  const [options,setOptions]=useState<ReportFilterOptions>({branch_id:[],customer_id:[],employee_id:[],product_id:[]});
  const [filters,setFilters]=useState<Partial<Record<ReportFilterKey,number>>>({});
  const [optionsError,setOptionsError]=useState("");
  useEffect(()=>{let active=true;api.reportFilterOptions().then(data=>{if(active)setOptions(data);}).catch(()=>{if(active)setOptionsError("No se pudieron cargar los filtros. Puedes generar el reporte general o recargar la página.");});return()=>{active=false;};},[]);
  const initial=dashboardWindow(30);
  const [start,setStart]=useState(initial.start);
  const [end,setEnd]=useState(initial.end);
  const [type,setType]=useState<ReportKind>("sales");
  const [items,setItems]=useState<Report[]>([]);
  const [page,setPage]=useState(0);
  const [revision,setRevision]=useState(0);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [historyError,setHistoryError]=useState("");
  const [result,setResult]=useState<ReportSnapshot|null>(null);
  const [detailPage,setDetailPage]=useState(0);
  useEffect(()=>{
    let current=true;setLoading(true);setHistoryError("");
    api.reports(page*25).then(data=>{if(current)setItems(data);}).catch(e=>{if(current)setHistoryError(e instanceof Error?e.message:"No se pudo cargar el historial");}).finally(()=>{if(current)setLoading(false);});
    return()=>{current=false;};
  },[page,revision]);
  async function create(event:FormEvent){
    event.preventDefault();setError("");
    if(start&&end&&end<start){setError("La fecha final debe ser igual o posterior a la inicial.");return;}
    setBusy(true);
    try{setResult(await api.createSalesReport(start,end,type,filters));setDetailPage(0);setPage(0);setRevision(v=>v+1);}catch(e){setError(e instanceof Error?e.message:"No se pudo generar el reporte");}finally{setBusy(false);}
  }
  async function view(id:number){setBusy(true);setError("");try{setResult(await api.report(id));setDetailPage(0);}catch(e){setError(e instanceof Error?e.message:"No se pudo abrir el reporte");}finally{setBusy(false);}}
  async function download(id:number){setBusy(true);setError("");try{await api.downloadReport(id);}catch(e){setError(e instanceof Error?e.message:"No se pudo descargar");}finally{setBusy(false);}}
  return <div className="reports-layout">
    <section className="panel report-builder"><div className="report-icon"><FileBarChart2 size={20}/></div><h2>Generar reporte</h2><p>Guarda una copia de los resultados para consultarla y descargarla después.</p>
      <form onSubmit={create}><label>Tipo de reporte<select disabled={busy} value={type} onChange={e=>setType(e.target.value as typeof type)}><option value="sales">Ventas y transacciones</option><option value="statistical">Resumen estadístico de ventas</option><option value="products">Rendimiento de productos</option><option value="customers">Actividad por cliente</option><option value="sellers">Rendimiento de vendedores</option></select></label>
        <div className="date-fields"><label>Desde<input type="date" disabled={busy} value={start} max={end||undefined} onChange={e=>setStart(e.target.value)}/></label><label>Hasta<input type="date" disabled={busy} value={end} min={start||undefined} onChange={e=>setEnd(e.target.value)}/></label></div>
        <div className="report-filter-fields">{([["branch_id","Sucursal"],["customer_id","Cliente"],["employee_id","Vendedor"],["product_id","Producto"]] as const).map(([key,label])=><label key={key}>{label}<select disabled={busy} value={filters[key]??""} onChange={e=>setFilters(current=>({...current,[key]:e.target.value?Number(e.target.value):undefined}))}><option value="">Todos</option>{options[key].map(option=><option key={option.id} value={option.id}>{option.name}</option>)}</select></label>)}</div>
        {optionsError&&<p className="inline-error" role="alert">{optionsError}</p>}
        {filters.product_id&&<p className="form-note">Se incluyen los totales completos de las ventas que contienen este producto.</p>}
        <p className="form-note">Fechas en Lima. Las anuladas se identifican y se excluyen de los totales. Máximo 10 000 ventas por reporte; reduce el periodo si se supera.</p>
        <button className="btn btn-primary" disabled={busy}>{busy?"Procesando…":"Generar y guardar"}</button>
      </form>{error&&<div className="inline-error" role="alert">{error}</div>}
    </section>
    <section className="panel history-panel"><div className="panel-heading"><div><h2>Reportes guardados</h2><p>La descarga conserva el contenido generado</p></div></div>
      {historyError&&<div className="inline-error">{historyError}<button className="text-button" onClick={()=>setRevision(v=>v+1)}>Reintentar</button></div>}
      {loading?<div className="table-empty" role="status">Cargando historial…</div>:items.length?items.slice(0,25).map(item=><article className="history-item" key={item.id}><div className="history-icon"><FileBarChart2 size={15}/></div><div><strong>{reportTitle(item.report_type)} #{item.id}</strong><span>{new Date(item.created_at).toLocaleString("es-PE",{timeZone:"America/Lima"})}</span><small>{String(item.parameters.start??"Desde el inicio")} — {String(item.parameters.end??"Sin fecha final")}</small><div className="report-history-actions">{item.available?<><button className="text-button" disabled={busy} onClick={()=>view(item.id)}>Ver resultado</button><button className="text-button" disabled={busy} onClick={()=>download(item.id)}>Descargar CSV</button></>:<button className="text-button" disabled={busy} onClick={()=>{setStart(String(item.parameters.start??""));setEnd(String(item.parameters.end??""));setType(item.report_type==="statistical"?"statistical":"sales");}}>Usar fechas del registro antiguo</button>}</div>{!item.available&&<small>Este registro anterior no conserva una copia descargable.</small>}</div></article>):!historyError&&<div className="table-empty">Aún no hay reportes guardados.</div>}
      <div className="catalog-pagination"><span>Página {page+1}</span><div><button className="btn btn-light" disabled={loading||page===0} onClick={()=>setPage(v=>v-1)}>Anterior</button><button className="btn btn-light" disabled={loading||items.length<=25} onClick={()=>setPage(v=>v+1)}>Siguiente</button></div></div>
    </section>
    {result&&<section className="panel report-preview"><div className="data-toolbar"><div><strong>{reportTitle(result.report_type)} #{result.id}</strong><p>{result.parameters.start??"Desde el inicio"} — {result.parameters.end??"Sin fecha final"} · Lima</p><p>Generado: {new Date(result.generated_at).toLocaleString("es-PE",{timeZone:"America/Lima"})}</p></div><button className="btn btn-light" onClick={()=>setPrinting(true)}>Vista PDF / imprimir</button><button className="btn btn-primary" disabled={busy} onClick={()=>download(result.id)}><Download size={15}/> Descargar copia CSV</button></div>
      <p className="dashboard-filter-explanation">Filtros: {Object.values(result.parameters.filters??{}).map(value=>value?.name).join(" · ")||"Todos"}</p>
      <p className="dashboard-filter-explanation">{result.summary.sales_count} ventas confirmadas · {result.summary.voided_count} anuladas. Se conservan los estados que tenían al generar este reporte.</p>
      {!result.summary.by_currency.length&&<div className="table-empty">No hay ventas confirmadas para calcular indicadores en este periodo.</div>}
      {result.summary.by_currency.map(group=><div className="report-currency-group" key={group.currency}><h3>{group.currency} · {group.sales_count} ventas confirmadas</h3><div className="stat-result-grid">{([["Ingresos",group.revenue],["Ticket promedio",group.average_ticket],["Mediana",group.median_ticket],["Mínimo",group.minimum],["Máximo",group.maximum]] as const).map(([label,value])=><div key={label}><small>{label}</small><strong>{money(value,group.currency)}</strong></div>)}</div></div>)}
      {result.groups&&<ReportGroups groups={result.groups} type={result.report_type}/>}
      {result.report_type==="sales"&&<><div className="table-wrap"><table><thead><tr><th>VENTA</th><th>FECHA</th><th>CLIENTE</th><th>VENDEDOR</th><th>ESTADO</th><th>TOTAL</th></tr></thead><tbody>{result.rows.slice(detailPage*25,detailPage*25+25).map(row=><tr key={row.id}><td>#{row.id}</td><td>{new Date(row.sold_at).toLocaleString("es-PE",{timeZone:"America/Lima"})}</td><td>{row.customer??"Cliente general"}</td><td>{row.seller}</td><td>{row.status==="confirmed"?"Confirmada":"Anulada"}</td><td>{money(row.total,row.currency)}</td></tr>)}</tbody></table></div><div className="catalog-pagination"><span>{result.rows.length} registros · Página {detailPage+1}</span><div><button className="btn btn-light" disabled={detailPage===0} onClick={()=>setDetailPage(v=>v-1)}>Anterior</button><button className="btn btn-light" disabled={(detailPage+1)*25>=result.rows.length} onClick={()=>setDetailPage(v=>v+1)}>Siguiente</button></div></div></>}
    </section>}
    {printing&&result&&<ReportPrint report={result} onClose={()=>setPrinting(false)}/>}
  </div>;
}
