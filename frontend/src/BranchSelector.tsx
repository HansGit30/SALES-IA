import { useEffect,useState } from "react";
import { api,type Branch } from "./services/api";
export default function BranchSelector({value,onChange,all=false,disabled=false}:{value:string;onChange:(value:string)=>void;all?:boolean;disabled?:boolean}){
 const [rows,setRows]=useState<Branch[]>([]),[error,setError]=useState(false),[revision,setRevision]=useState(0);
 useEffect(()=>{let active=true;api.branches().then(data=>{if(active){setRows(data);setError(false);}}).catch(()=>{if(active)setError(true);});return()=>{active=false;};},[revision]);
 return <label className="branch-selector">Sucursal<select disabled={disabled} value={value} onChange={e=>onChange(e.target.value)}><option value="">{all?"Todas las sucursales":"Sin sucursal / inventario general"}</option>{rows.filter(b=>all||b.is_active||String(b.id)===value).map(b=><option key={b.id} value={b.id}>{b.name}{b.is_active?"":" (inactiva)"}</option>)}</select>{error&&<span role="alert">No se pudieron cargar las sedes. <button type="button" className="text-button" onClick={()=>setRevision(v=>v+1)}>Reintentar</button></span>}</label>;
}
