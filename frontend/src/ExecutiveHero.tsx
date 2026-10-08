import { ArrowUpRight, Layers3, ShieldCheck } from "lucide-react";

export function DataSculpture(){
  return <div className="data-sculpture" aria-hidden="true"><div className="sculpture-orbit"/><div className="sculpture-scene"><div className="sculpture-floor"/>{[0,1,2,3].map(i=><div key={i} className={"sculpture-pillar pillar-"+i}><i/><b/><span/></div>)}<div className="sculpture-glass"><Layers3 size={23}/><span>SALESIA</span><i/></div></div></div>;
}

export default function ExecutiveHero({role}:{role:string}){
  const target=role==="warehouse"?"inventory":role==="seller"?"sales":"analytics";
  return <section className="executive-hero">
    <div className="executive-copy"><div className="executive-label"><span/> CENTRO DE OPERACIONES</div><h2>Una visión clara.<br/><em>Decisiones con respaldo.</em></h2><p>Conecta la actividad de tu equipo con la información que necesitas para dirigir tu negocio.</p><button className="executive-action" onClick={()=>window.dispatchEvent(new CustomEvent("salesia:navigate",{detail:target}))}>{role==="warehouse"?"Gestionar inventario":role==="seller"?"Ir a ventas":"Explorar Analytics"}<ArrowUpRight size={17}/></button><div className="executive-caption"><ShieldCheck size={14}/> Operaciones y análisis en un mismo espacio</div></div>
    <DataSculpture/>
  </section>;
}
