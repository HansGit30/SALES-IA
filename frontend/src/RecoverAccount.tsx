import { useState, type FormEvent } from "react";
import { api, type ManagedUser } from "./services/api";

export default function RecoverAccount({user,onClose,onRecovered}:{user:ManagedUser;onClose:()=>void;onRecovered:()=>void}){
  const [adminPassword,setAdminPassword]=useState("");
  const [temporary,setTemporary]=useState("");
  const [confirmation,setConfirmation]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  async function submit(event:FormEvent){
    event.preventDefault();setError("");
    if(temporary!==confirmation){setError("Las contraseñas temporales no coinciden.");return;}
    setBusy(true);
    try{await api.resetUserPassword(user.id,adminPassword,temporary);onRecovered();}
    catch(e){setError(e instanceof Error?e.message:"No se pudo restablecer el acceso.");}
    finally{setBusy(false);}
  }
  return <section className="panel settings-form"><div className="panel-heading"><div><h2>Restablecer acceso</h2><p>{user.full_name} · {user.email}</p></div></div>
    <p className="form-note">Confirma la identidad del usuario y comunícale la contraseña temporal por un canal seguro. Se cerrarán sus sesiones y deberá elegir una contraseña personal al entrar.</p>
    <form onSubmit={submit}>
      <label>Tu contraseña de administrador<input autoFocus type="password" autoComplete="current-password" required maxLength={200} disabled={busy} value={adminPassword} onChange={e=>setAdminPassword(e.target.value)}/></label>
      <label>Contraseña temporal del usuario<input type="password" autoComplete="new-password" required minLength={12} maxLength={200} disabled={busy} value={temporary} onChange={e=>setTemporary(e.target.value)}/></label>
      <label>Repite la contraseña temporal<input type="password" autoComplete="new-password" required minLength={12} maxLength={200} disabled={busy} value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></label>
      {error&&<p className="inline-error" role="alert">{error}</p>}
      <div className="modal-actions"><button type="button" className="btn btn-light" disabled={busy} onClick={onClose}>Cancelar</button><button className="btn btn-primary" disabled={busy}>{busy?"Restableciendo…":"Confirmar restablecimiento"}</button></div>
    </form>
  </section>;
}
