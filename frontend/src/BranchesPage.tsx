import { useEffect, useRef, useState, type FormEvent } from "react";
import { Building2, MapPin, Mail, Phone, Plus, Search, X } from "lucide-react";
import { api, type Branch, type BranchInput } from "./services/api";
import BranchMap from "./BranchMap";

const empty:BranchInput={code:"",name:"",address:"",city:"",phone:null,manager_name:null,manager_email:null,latitude:null,longitude:null,is_active:true};
export default function BranchesPage({canManage}:{canManage:boolean}){
  const [rows,setRows]=useState<Branch[]>([]),[selected,setSelected]=useState<number|null>(null);
  const [query,setQuery]=useState(""),[state,setState]=useState("all");
  const [error,setError]=useState(""),[loading,setLoading]=useState(true),[revision,setRevision]=useState(0);
  const [editing,setEditing]=useState<Branch|null|undefined>(undefined),[notice,setNotice]=useState("");
  useEffect(()=>{let active=true;setLoading(true);setError("");api.branches().then(data=>{if(active){setRows(data);setSelected(current=>data.some(b=>b.id===current)?current:data[0]?.id??null);}}).catch(e=>{if(active)setError(e instanceof Error?e.message:"No se pudieron cargar las sucursales");}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[revision]);
  const normalize=(value:string)=>value.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
  const visible=rows.filter(b=>normalize(b.name+" "+b.city+" "+b.code).includes(normalize(query))&&(state==="all"||(state==="active")===b.is_active));
  const current=visible.find(b=>b.id===selected)??visible[0]??null;
  return <div className="branches-page">
    <div className="branch-kpis">{[[String(rows.length),"Sucursales registradas"],[String(rows.filter(b=>b.is_active).length),"Sedes activas"],[String(new Set(rows.map(b=>b.city.toLowerCase().trim())).size),"Ciudades"],[String(rows.filter(b=>b.latitude===null).length),"Sin coordenadas"]].map(([value,label])=><article key={label}><span>{label}</span><strong>{loading?"—":value}</strong></article>)}</div>
    <div className="panel branch-toolbar"><div className="search-box"><Search size={16}/><input aria-label="Buscar sucursal" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Nombre, ciudad o código"/></div><select aria-label="Estado de sucursales" value={state} onChange={e=>setState(e.target.value)}><option value="all">Todos los estados</option><option value="active">Activas</option><option value="inactive">Inactivas</option></select><button className="btn btn-light" disabled={loading} onClick={()=>setRevision(v=>v+1)}>Actualizar</button>{canManage&&<button className="btn btn-primary" onClick={()=>setEditing(null)}><Plus size={16}/>Nueva sucursal</button>}</div>
    {error&&<div className="inline-error" role="alert">{error}</div>}{notice&&<div className="catalog-notice" role="status">{notice}</div>}
    <div className="branches-layout"><BranchMap branches={visible} selected={current} onSelect={setSelected}/><aside className="branch-side">
      {current?<section className="panel branch-detail"><div className="branch-detail-heading"><span className="branch-location-icon"><MapPin size={24}/></span><div><h2>{current.name}</h2><p>{current.city} · {current.code}</p></div></div><span className={"status "+(current.is_active?"status-active":"status-inactive")}>{current.is_active?"Sucursal activa":"Sucursal inactiva"}</span>
        <div className="branch-address"><small>UBICACIÓN DE LA SEDE</small><strong>{current.address}</strong><span>{current.city}</span>{current.latitude!==null?<a target="_blank" rel="noopener noreferrer" href={"https://www.openstreetmap.org/?mlat="+current.latitude+"&mlon="+current.longitude+"#map=17/"+current.latitude+"/"+current.longitude}>Abrir ubicación exacta ↗</a>:<p>Sin coordenadas. Edita la sede para situarla en el mapa.</p>}</div>
        <div className="branch-manager"><small>RESPONSABLE DE SEDE</small><h3>{current.manager_name||"Sin responsable registrado"}</h3>{current.manager_email&&<a href={"mailto:"+current.manager_email}><Mail size={14}/>{current.manager_email}</a>}{current.phone&&<span><Phone size={14}/>{current.phone}</span>}</div>
        <BranchMetrics key={current.id} id={current.id}/>
        {canManage&&<button className="btn btn-light" onClick={()=>setEditing(current)}>Editar sucursal</button>}
      </section>:<section className="panel"><Building2 size={28}/><h2>{loading?"Cargando sucursales…":"Sin sucursales para mostrar"}</h2><p className="form-note">{rows.length?"Ajusta los filtros para consultar otras sedes.":"Registra la primera sede con su dirección y coordenadas."}</p></section>}
      <section className="panel branch-directory"><div className="panel-heading"><div><h2>Red de sedes</h2><p>Selecciona una ubicación para ver su ficha</p></div><span className="sku">{visible.length}</span></div>{visible.map(branch=><button className={branch.id===current?.id?"selected":""} key={branch.id} onClick={()=>setSelected(branch.id)}><MapPin size={17}/><span><strong>{branch.name}</strong><small>{branch.city} · {branch.is_active?"Activa":"Inactiva"}</small></span><span>↗</span></button>)}</section>
    </aside></div>
    {editing!==undefined&&<BranchEditor branch={editing} onClose={()=>setEditing(undefined)} onSaved={branch=>{setEditing(undefined);setSelected(branch.id);setRevision(v=>v+1);setNotice("Sucursal guardada correctamente.");}}/>}
  </div>;
}

function BranchEditor({branch,onClose,onSaved}:{branch:Branch|null;onClose:()=>void;onSaved:(branch:Branch)=>void}){
  const [form,setForm]=useState<BranchInput>(()=>branch?Object.fromEntries(Object.keys(empty).map(key=>[key,branch[key as keyof BranchInput]])) as BranchInput:{...empty});
  const [error,setError]=useState(""),[busy,setBusy]=useState(false);const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const previous=document.activeElement as HTMLElement;dialog.current?.showModal();return()=>previous?.focus();},[]);
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError("");try{onSaved(await api.saveBranch(form,branch?.id));}catch(e){setError(e instanceof Error?e.message:"No se pudo guardar");}finally{setBusy(false);}}
  return <dialog ref={dialog} className="branch-editor" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}><form onSubmit={submit}><div className="modal-heading"><div><h2>{branch?"Editar sucursal":"Nueva sucursal"}</h2><p>Identificación, ubicación y responsable</p></div><button type="button" className="icon-button" disabled={busy} onClick={onClose} aria-label="Cerrar"><X size={18}/></button></div><fieldset disabled={busy} className="branch-editor-fields">
    {([["code","Código",40],["name","Nombre de la sede",160],["city","Ciudad",120],["address","Dirección exacta",300],["manager_name","Responsable (opcional)",160],["manager_email","Correo del responsable (opcional)",254],["phone","Teléfono (opcional)",40]] as const).map(([key,label,max])=><label key={key}>{label}<input type={key==="manager_email"?"email":"text"} required={["code","name","city","address"].includes(key)} maxLength={max} value={form[key]??""} onChange={e=>setForm({...form,[key]:e.target.value||null})}/></label>)}
    <label>Latitud<input type="number" step="0.000001" min="-90" max="90" placeholder="-12.046374" value={form.latitude??""} onChange={e=>setForm({...form,latitude:e.target.value||null})}/></label><label>Longitud<input type="number" step="0.000001" min="-180" max="180" placeholder="-77.042793" value={form.longitude??""} onChange={e=>setForm({...form,longitude:e.target.value||null})}/></label>
    <label className="branch-state-check"><input type="checkbox" checked={form.is_active} onChange={e=>setForm({...form,is_active:e.target.checked})}/>Sucursal activa</label></fieldset><p className="form-note">Las coordenadas deben corresponder a la sede. Puedes dejarlas vacías y añadirlas después; no se calcula la ubicación automáticamente por la dirección.</p>{error&&<p className="inline-error" role="alert">{error}</p>}<div className="modal-actions"><button className="btn btn-light" type="button" disabled={busy} onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy}>{busy?"Guardando…":"Guardar sucursal"}</button></div></form></dialog>;
}

function BranchMetrics({id}:{id:number}){
  const [data,setData]=useState<Awaited<ReturnType<typeof api.branchSummary>>|null>(null);
  const [error,setError]=useState("");
  useEffect(()=>{let active=true;api.branchSummary(id).then(value=>{if(active)setData(value);}).catch(()=>{if(active)setError("No se pudieron consultar los indicadores de esta sede.");});return()=>{active=false;};},[id]);
  if(error)return <p className="inline-error" role="alert">{error}</p>;
  if(!data)return <p className="form-note" role="status">Consultando indicadores…</p>;
  return <section aria-label="Indicadores de la sucursal" className="branch-operating-metrics"><div><span>Personal comercial activo</span><strong>{data.staff}</strong></div><div><span>Unidades disponibles</span><strong>{Number(data.units).toLocaleString("es-PE")}</strong></div><div><span>Productos con stock</span><strong>{data.products}</strong></div>{data.sales_visible&&<><h3>Ventas confirmadas · histórico</h3>{data.sales.length?data.sales.map(row=><div key={row.currency}><span>{row.transactions} ventas · {row.currency}</span><strong>{new Intl.NumberFormat("es-PE",{style:"currency",currency:row.currency}).format(Number(row.revenue))}</strong></div>):<p className="form-note">Esta sede aún no tiene ventas confirmadas.</p>}</>}</section>;
}
