import DashboardBreakdown from "./DashboardBreakdown";
import BranchSelector from "./BranchSelector";
import { useEffect, useState } from "react";
import { Activity, CreditCard, TrendingUp, Users } from "lucide-react";
import { api, type Summary, type DashboardOptions, type Breakdown } from "./services/api";
import { bucketSales, dashboardWindow, relativeChange, type SalesDay } from "./services/dashboard";

type DashboardData = { breakdown:Breakdown; current:Summary; previous:Summary; series:SalesDay[]; period:ReturnType<typeof dashboardWindow> };
const dateLabel=(day:string)=>new Date(day+"T12:00:00Z").toLocaleDateString("es-PE",{timeZone:"UTC",day:"2-digit",month:"short",year:"numeric"});
const navigate=(page:string)=>window.dispatchEvent(new CustomEvent("salesia:navigate",{detail:page}));
export default function BusinessDashboard({days,role}:{days:number;role:string}) {
  const [data,setData]=useState<DashboardData|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [revision,setRevision]=useState(0);
  const [branch,setBranch]=useState("");
  const [employee,setEmployee]=useState("");
  const [product,setProduct]=useState("");
  const [category,setCategory]=useState("");
  const [options,setOptions]=useState<DashboardOptions>({employees:[],products:[],categories:[]});
  const [optionsError,setOptionsError]=useState("");
  useEffect(()=>{
    let current=true;
    api.dashboardOptions().then(value=>{if(current){setOptions(value);setOptionsError("");}})
      .catch(()=>{if(current)setOptionsError("No se pudieron cargar los filtros. Pulsa Reintentar filtros.");});
    return()=>{current=false;};
  },[revision]);
  useEffect(()=>{
    let current=true;
    setLoading(true);setError("");setData(null);
    const period=dashboardWindow(days);
    const filters={branch_id:branch,employee_id:employee,product_id:product,category_id:category};
    Promise.all([api.dashboardSummary(period.start,period.end,filters),api.dashboardSummary(period.previousStart,period.previousEnd,filters),api.dashboardSeries(period.start,period.end,filters),api.dashboardBreakdown(period.start,period.end,filters)])
      .then(([summary,previous,series,breakdown])=>{if(current)setData({current:summary,previous,series,period,breakdown});})
      .catch(e=>{if(current)setError(e instanceof Error?e.message:"No se pudo cargar el dashboard");})
      .finally(()=>{if(current)setLoading(false);});
    return()=>{current=false;};
  },[days,revision,employee,product,category,branch]);
  const currency=data?.current.currency??"PEN";
  const money=(value:string|number)=>new Intl.NumberFormat("es-PE",{style:"currency",currency,maximumFractionDigits:2}).format(Number(value));
  const grain=days<=30?"day":days<=90?"week":"month";
  const grainLabel=grain==="day"?"día":grain==="week"?"semana":"mes";
  const buckets=data?bucketSales(data.series,data.period.start,data.period.end,grain):[];
  const max=Math.max(1,...buckets.map(b=>Number(b.revenue)));
  const metrics=[
    {key:"customer_count" as const,label:"Clientes con compras",icon:Users,money:false},
    {key:"revenue" as const,label:"Ingresos confirmados",icon:CreditCard,money:true},
    {key:"transaction_count" as const,label:"Ventas confirmadas",icon:Activity,money:false},
    {key:"average_ticket" as const,label:"Ticket promedio",icon:TrendingUp,money:true},
    {key:"median_ticket" as const,label:"Mediana de venta",icon:Users,money:true},
  ];
  return <div className="dashboard-content" aria-busy={loading}>
    <section className="panel dashboard-filter-panel"><div className="sales-filters"><BranchSelector all value={branch} onChange={setBranch}/>
      {role!=="seller"&&<label>Vendedor<select value={employee} onChange={e=>setEmployee(e.target.value)}><option value="">Todo el equipo</option>{options.employees.map(item=><option key={item.id} value={item.id}>{item.name}{!item.is_active?" (inactivo)":""}</option>)}</select></label>}
      <label>Categoría<select value={category} onChange={e=>{setCategory(e.target.value);setProduct("");}}><option value="">Todas las categorías</option>{options.categories.map(item=><option key={item.id} value={item.id}>{item.name}{!item.is_active?" (inactiva)":""}</option>)}</select></label>
      <label>Producto<select value={product} onChange={e=>setProduct(e.target.value)}><option value="">Todos los productos</option>{options.products.filter(item=>!category||String(item.category_id)===category).map(item=><option key={item.id} value={item.id}>{item.name} · {item.sku}{!item.is_active?" (inactivo)":""}</option>)}</select></label>
      <button className="btn btn-light" onClick={()=>{setEmployee("");setProduct("");setCategory("");setBranch("");}}>Limpiar filtros</button>
    </div>{optionsError&&<div className="inline-error" role="alert">{optionsError} <button className="text-button" onClick={()=>setRevision(v=>v+1)}>Reintentar filtros</button></div>}
      <p className="dashboard-filter-explanation">{product||category?"Se incluyen ventas que contienen los artículos seleccionados. Los ingresos corresponden al total completo de esas ventas, contadas una sola vez. La categoría corresponde al catálogo actual.":"Los filtros se aplican al periodo actual, al periodo anterior y al gráfico."}</p>
    </section>
    {error&&<div className="inline-error" role="alert">{error} <button className="text-button" onClick={()=>setRevision(v=>v+1)}>Reintentar</button></div>}
    <div className="dashboard-period-note">{data?<><strong>{dateLabel(data.period.start)} — {dateLabel(data.period.end)}</strong><span>Comparado con {dateLabel(data.period.previousStart)} — {dateLabel(data.period.previousEnd)} · America/Lima</span></>:loading?"Cargando el periodo seleccionado…":"Sin información disponible"}</div>
    <div className="kpi-grid">{metrics.map(metric=>{
      const value=data?.current[metric.key],previous=data?.previous[metric.key];
      const change=value!==undefined&&previous!==undefined?relativeChange(Number(value),Number(previous)):null;
      return <article className="kpi-card" key={metric.key}><div className="kpi-top"><span>{metric.label}</span><span className="kpi-icon blue"><metric.icon size={17}/></span></div><strong className="kpi-value">{loading?"···":value===undefined?"—":metric.money?money(value):Number(value).toLocaleString("es-PE")}</strong><div className="kpi-foot"><span className="kpi-period">{!data?"Periodo seleccionado":change===null?"Sin base previa para comparar":`${change>0?"+":""}${change.toLocaleString("es-PE",{maximumFractionDigits:1})}% frente al periodo anterior`}</span></div>{data&&<small className="comparison-baseline">Anterior: {metric.money?money(previous!):Number(previous).toLocaleString("es-PE")}</small>}</article>;
    })}</div>
    <section className="panel dashboard-trend"><div className="panel-heading"><div><h2>Rendimiento de ventas</h2><p>Ingresos por {grainLabel} · incluye días sin ventas</p></div><span className="dashboard-grain">{grain==="day"?"Diario":grain==="week"?"Semanal":"Mensual"}</span></div>
      {loading?<div className="table-empty" role="status">Cargando la evolución del periodo…</div>:data?<><div className="complete-chart-scroll"><div className="complete-chart" style={{gridTemplateColumns:`repeat(${buckets.length},minmax(36px,1fr))`}} aria-label={`Ingresos agrupados por ${grainLabel}; datos disponibles en la tabla inferior`}>
        {buckets.map(bucket=><div className="complete-chart-column" key={bucket.start}><div className="complete-chart-track"><div className="complete-chart-bar" style={{height:`${Number(bucket.revenue)/max*100}%`}} title={`${dateLabel(bucket.start)} — ${dateLabel(bucket.end)}: ${money(bucket.revenue)} · ${bucket.transactions} ventas`}/></div><small>{new Date(bucket.start+"T12:00:00Z").toLocaleDateString("es-PE",{timeZone:"UTC",day:grain==="month"?undefined:"2-digit",month:"short"})}</small></div>)}
      </div></div><div className="chart-legend"><span>Escala máxima: {money(max)}</span><span>Fuente: ventas confirmadas · {currency}</span></div>
      {data.current.transaction_count===0&&<p className="dashboard-period-note">No hay ventas confirmadas en este periodo.</p>}
      <details className="dashboard-data-table"><summary>Ver datos del gráfico</summary><div className="table-wrap"><table><thead><tr><th>PERIODO</th><th>VENTAS</th><th>INGRESOS</th></tr></thead><tbody>{buckets.map(bucket=><tr key={bucket.start}><td>{dateLabel(bucket.start)}{bucket.end!==bucket.start&&` — ${dateLabel(bucket.end)}`}</td><td>{bucket.transactions}</td><td>{money(bucket.revenue)}</td></tr>)}</tbody></table></div></details></>:<div className="table-empty">Reintenta la consulta para ver el gráfico.</div>}
    </section>
    {data&&<DashboardBreakdown data={data.breakdown}/>}
    <div className="dashboard-bottom-panels"><section className="panel dashboard-explanation"><h2>Cómo leer estos indicadores</h2><p>El promedio reparte los ingresos entre las ventas. La mediana muestra el valor central y ayuda a reconocer si unas pocas operaciones elevan el promedio.</p><p>La comparación usa otro periodo de {days} días inmediatamente anterior. El día actual todavía puede estar en curso. Las ventas anuladas se excluyen.</p>{role==="seller"&&<p>Los indicadores incluyen únicamente tus ventas.</p>}</section>
      <section className="panel dashboard-explanation"><h2>Continuar trabajando</h2><div className="dashboard-shortcuts">{["admin","manager","seller"].includes(role)&&<button className="btn btn-light" onClick={()=>navigate("sales")}>Consultar ventas</button>}{["admin","manager","analyst"].includes(role)&&<><button className="btn btn-primary" onClick={()=>navigate("analytics")}>Abrir laboratorio</button><button className="btn btn-light" onClick={()=>navigate("reports")}>Generar reporte</button><button className="btn btn-light" onClick={()=>navigate("insights")}>Consultar insights</button></>}</div></section></div>
  </div>;
}
