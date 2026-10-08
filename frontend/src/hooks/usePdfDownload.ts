import {useState} from "react";
import {downloadPdf} from "../services/api";

export function usePdfDownload(kind:"reports"|"sales",id:number){
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function download(){
    if(busy)return;
    setBusy(true);setError("");
    try{await downloadPdf(kind,id)}
    catch(e){setError(e instanceof Error?e.message:"No se pudo descargar el PDF")}
    finally{setBusy(false)}
  }
  return {download,busy,error};
}
