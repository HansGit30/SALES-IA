import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { FeatureCollection, Geometry, Position } from "geojson";
import "leaflet/dist/leaflet.css";
import type { Branch } from "./services/api";

function inRing(point:Position,ring:Position[]){
  let inside=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
    const a=ring[i],b=ring[j];
    if(((a[1]>point[1])!==(b[1]>point[1]))&&point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;
  }
  return inside;
}
function contains(geometry:Geometry,branch:Branch){
  if(branch.latitude===null||branch.longitude===null)return false;
  const polygons=geometry.type==="Polygon"?[geometry.coordinates]:geometry.type==="MultiPolygon"?geometry.coordinates:[];
  const p=[Number(branch.longitude),Number(branch.latitude)];
  return polygons.some(rings=>inRing(p,rings[0])&&!rings.slice(1).some(ring=>inRing(p,ring)));
}
export default function BranchMap({branches,selected,onSelect}:{branches:Branch[];selected:Branch|null;onSelect:(id:number)=>void}){
  const container=useRef<HTMLDivElement>(null);
  const map=useRef<L.Map|null>(null);
  const selectRef=useRef(onSelect);selectRef.current=onSelect;
  const [geometry,setGeometry]=useState<FeatureCollection|null>(null);
  const [error,setError]=useState("");
  const [revision,setRevision]=useState(0);
  useEffect(()=>{const controller=new AbortController();setError("");
    fetch("/maps/peru-departments.geojson",{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(setGeometry).catch(()=>{if(!controller.signal.aborted)setError("No se pudo cargar el mapa. La lista de sucursales sigue disponible.");});
    return()=>controller.abort();
  },[revision]);
  useEffect(()=>{
    if(!container.current)return;
    const instance=L.map(container.current,{scrollWheelZoom:false,zoomControl:false,attributionControl:true,minZoom:3,maxZoom:16}).setView([-9.2,-75],5);
    L.control.zoom({position:"topright"}).addTo(instance);
    instance.attributionControl.addAttribution('<a href="https://www.geoboundaries.org/" target="_blank" rel="noopener noreferrer">geoBoundaries · Perú ADM1</a>');
    map.current=instance;
    const observer=new ResizeObserver(()=>instance.invalidateSize());observer.observe(container.current);
    return()=>{observer.disconnect();instance.remove();map.current=null;};
  },[]);
  useEffect(()=>{
    if(!map.current||!geometry)return;
    const instance=map.current;
    const layer=L.geoJSON(geometry,{style:feature=>{
      const members=feature?branches.filter(b=>contains(feature.geometry,b)):[];
      const active=members.some(b=>b.id===selected?.id);
      return {className:active?"department-selected":"department-region",color:active?"#087f94":"#8baeba",weight:active?2:1,fillOpacity:1,fillColor:active?"#19b5c5":members.some(b=>b.is_active)?"#3b7ff5":"#cce2f8"};
    },onEachFeature:(feature,polygon)=>{
      // Department selection is expressed by its fill, without a floating tooltip box.
      polygon.on("click",()=>{const branch=branches.find(b=>contains(feature.geometry,b));if(branch)selectRef.current(branch.id);});
    }}).addTo(instance);
    layer.eachLayer(region=>{if(region instanceof L.Path && region.options.className==="department-selected")region.bringToFront();});
    const markers=L.layerGroup().addTo(instance);
    branches.filter(b=>b.latitude!==null&&b.longitude!==null).forEach(branch=>{
      const marker=L.marker([Number(branch.latitude),Number(branch.longitude)],{icon:L.divIcon({className:"branch-map-marker"+(selected?.id===branch.id?" selected":"")+(!branch.is_active?" inactive":""),html:"<span></span>",iconSize:[20,20],iconAnchor:[10,10]}),title:branch.name,keyboard:true}).addTo(markers);
      const label=document.createElement("span");label.textContent=branch.city;marker.bindTooltip(label,{direction:"top",permanent:true,className:"branch-city-label",offset:[0,-9]});
      marker.on("click",()=>selectRef.current(branch.id));
    });
    return()=>{layer.remove();markers.remove();};
  },[geometry,branches,selected]);
  useEffect(()=>{
    if(!map.current||!geometry)return;
    const bounds=L.geoJSON(geometry).getBounds();
    branches.forEach(b=>{if(b.latitude!==null&&b.longitude!==null)bounds.extend([Number(b.latitude),Number(b.longitude)]);});
    map.current.fitBounds(bounds,{padding:[25,25],animate:false});
  },[geometry,branches]);
  function reset(){if(map.current&&geometry)map.current.fitBounds(L.geoJSON(geometry).getBounds(),{padding:[25,25]});}
  return <div className="branch-map-shell"><div ref={container} className="branch-map-canvas" aria-label="Mapa de departamentos del Perú y sucursales"/><div className="branch-map-caption"><small>SALESIA / PERÚ</small><strong>Cobertura de la red</strong><span>{branches.length} sedes · {new Set(branches.map(b=>b.city.trim().toLowerCase())).size} ciudades</span></div><button className="branch-map-reset" onClick={reset}>Centrar Perú</button>{error?<div className="branch-map-message" role="alert">{error}<button onClick={()=>setRevision(v=>v+1)}>Reintentar</button></div>:!geometry&&<div className="branch-map-message" role="status">Cargando departamentos…</div>}<div className="branch-map-legend"><span><i/>Con sede activa</span><span><i/>Seleccionada</span><span><i/>Sin sede activa</span></div></div>;
}
