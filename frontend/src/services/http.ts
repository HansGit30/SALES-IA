/** Retry only reads. A failed write may already have committed and must not repeat. */
export async function fetchWithReadRetry(url:string,options:RequestInit={},fetcher:typeof fetch=fetch):Promise<Response>{
  const mayRetry=(options.method??"GET").toUpperCase()==="GET";
  for(let attempt=0;;attempt++){
    try{
      const response=await fetcher(url,options);
      if(!mayRetry||attempt>0||response.status!==503)return response;
    }catch(error){
      if(!mayRetry||attempt>0||options.signal?.aborted)throw error;
    }
    await new Promise(resolve=>setTimeout(resolve,250));
  }
}
