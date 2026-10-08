import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowUpRight, Search, X } from "lucide-react";

type Destination={id:string;label:string;description:string};
const normalize=(value:string)=>value.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
export default function ModuleSearch({items,onNavigate}:{items:Destination[];onNavigate:(id:string)=>void}){
  const [open,setOpen]=useState(false);
  const [query,setQuery]=useState("");
  const [selected,setSelected]=useState(0);
  const dialog=useRef<HTMLDivElement>(null);
  const trigger=useRef<HTMLButtonElement>(null);
  const filtered=items.filter(item=>normalize(item.label+" "+item.description).includes(normalize(query.trim())));
  useEffect(()=>{
    function shortcut(event:KeyboardEvent){
      if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
        // Do not intercept shortcuts from an active business form.
        if(document.querySelector('[aria-modal="true"]')&&!dialog.current)return;
        event.preventDefault();setQuery("");setSelected(0);setOpen(value=>!value);
      }
    }
    window.addEventListener("keydown",shortcut);
    return()=>window.removeEventListener("keydown",shortcut);
  },[]);
  useEffect(()=>{
    if(!open)return;
    const previous=document.activeElement as HTMLElement|null;
    const oldOverflow=document.body.style.overflow;
    document.body.style.overflow="hidden";
    dialog.current?.querySelector<HTMLInputElement>("input")?.focus();
    return()=>{document.body.style.overflow=oldOverflow;if(previous?.isConnected)previous.focus();else trigger.current?.focus();};
  },[open]);
  useEffect(()=>{if(open)document.getElementById("module-result-"+selected)?.scrollIntoView({block:"nearest"});},[selected,open]);
  function choose(item:Destination){setOpen(false);onNavigate(item.id);}
  return <>
    <button ref={trigger} className="module-search-trigger" onClick={()=>{setQuery("");setSelected(0);setOpen(true);}} aria-label="Buscar módulo" aria-haspopup="dialog"><Search size={16}/><span>Buscar módulo</span><kbd>Ctrl K</kbd></button>
    {open&&createPortal(<div className="module-search-overlay" onClick={()=>setOpen(false)}><div ref={dialog} className="module-search-dialog" role="dialog" aria-modal="true" aria-labelledby="module-search-title" onClick={e=>e.stopPropagation()} onKeyDown={e=>{
      if(e.key==="Escape"){e.preventDefault();setOpen(false);}
      if(e.key==="Tab"){const elements=dialog.current?.querySelectorAll<HTMLElement>('input,button');if(!elements?.length)return;const first=elements[0],last=elements[elements.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
    }}>
      <div className="module-search-heading"><div><span>NAVEGACIÓN RÁPIDA</span><h2 id="module-search-title">¿A dónde quieres ir?</h2></div><button className="icon-button" aria-label="Cerrar búsqueda" onClick={()=>setOpen(false)}><X size={19}/></button></div>
      <div className="module-search-input"><Search size={19}/><input placeholder="Ventas, inventario, reportes…" aria-label="Nombre del módulo" role="combobox" aria-autocomplete="list" aria-expanded="true" aria-controls="module-results" aria-activedescendant={filtered[selected]?"module-result-"+selected:undefined} value={query} onChange={e=>{setQuery(e.target.value);setSelected(0);}} onKeyDown={e=>{
        if(e.key==="ArrowDown"){e.preventDefault();setSelected(value=>Math.min(value+1,filtered.length-1));}
        if(e.key==="ArrowUp"){e.preventDefault();setSelected(value=>Math.max(value-1,0));}
        if(e.key==="Enter"&&filtered[selected]){e.preventDefault();choose(filtered[selected]);}
      }}/></div>
      <div className="module-search-results" id="module-results" role="listbox" aria-label="Módulos disponibles">{filtered.map((item,index)=><div id={"module-result-"+index} key={item.id} role="option" aria-selected={selected===index} className={"module-search-result"+(selected===index?" selected":"")} onMouseEnter={()=>setSelected(index)} onClick={()=>choose(item)}><span className="module-result-icon"><ArrowUpRight size={18}/></span><div><strong>{item.label}</strong><p>{item.description}</p></div><span className="module-enter">↵</span></div>)}</div>
      {!filtered.length&&<p className="module-search-empty" role="status">No hay módulos que coincidan. Prueba otro nombre.</p>}
      <footer className="module-search-footer"><span>↑ ↓ Seleccionar · Enter Abrir</span><span>Esc Cerrar</span></footer>
    </div></div>,document.body)}
  </>;
}
