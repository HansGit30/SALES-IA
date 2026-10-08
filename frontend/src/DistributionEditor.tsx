import { useState } from "react";
export default function DistributionEditor({ value,onChange }: { value:string;onChange:(value:string)=>void }) {
  const [rows,setRows]=useState<{value:string;probability:string}[]>(()=>JSON.parse(value).map((r:{value:number;probability:number})=>({value:String(r.value),probability:String(r.probability)})));
  function update(next:typeof rows){setRows(next);onChange(JSON.stringify(next.map(row=>({value:row.value===""?null:Number(row.value),probability:row.probability===""?null:Number(row.probability)}))));}
  const sum=rows.reduce((total,row)=>total+Number(row.probability||0),0);
  return <div className="distribution-editor"><p className="form-note">Define un valor por fila y su probabilidad entre 0 y 1. Los valores iniciales son un ejemplo editable.</p>
    <div className="table-wrap"><table><thead><tr><th>VALOR</th><th>PROBABILIDAD</th><th></th></tr></thead><tbody>{rows.map((row,index)=><tr key={index}><td><input required aria-label={`Valor ${index+1}`} type="number" step="any" value={row.value} onChange={e=>update(rows.map((r,i)=>i===index?{...r,value:e.target.value}:r))}/></td><td><input required aria-label={`Probabilidad ${index+1}`} type="number" min="0" max="1" step="any" value={row.probability} onChange={e=>update(rows.map((r,i)=>i===index?{...r,probability:e.target.value}:r))}/></td><td><button type="button" className="text-button" disabled={rows.length===1} onClick={()=>update(rows.filter((_,i)=>i!==index))}>Quitar</button></td></tr>)}</tbody></table></div>
    <div className="catalog-pagination"><span role="status">Suma: {sum.toFixed(6)} / 1</span><button type="button" className="btn btn-light" disabled={rows.length>=1000} onClick={()=>update([...rows,{value:"",probability:""}])}>Añadir resultado</button></div>
    {Math.abs(sum-1)>1e-8&&<p className="inline-error">Las probabilidades deben sumar 1.</p>}
    <div className="distribution-chart" aria-label="Distribución de probabilidades">{rows.map((row,index)=><div key={index}><span>{row.value||"—"}</span><progress max={1} value={Math.max(0,Math.min(1,Number(row.probability)||0))}/><span>{(Number(row.probability||0)*100).toFixed(1)} %</span></div>)}</div>
  </div>;
}
