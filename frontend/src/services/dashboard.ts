import { decimalAmount, lineCents } from "./amounts.ts";

export type SalesDay = { day:string; transactions:number; revenue:string };
export type SalesBucket = { start:string; end:string; transactions:number; revenue:string };
export function shiftDay(day:string, offset:number):string {
  const date=new Date(day+"T12:00:00Z");
  date.setUTCDate(date.getUTCDate()+offset);
  return date.toISOString().slice(0,10);
}
export function dashboardWindow(days:number, now=new Date()) {
  const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/Lima",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(now);
  const part=(name:string)=>parts.find(p=>p.type===name)!.value;
  const end=`${part("year")}-${part("month")}-${part("day")}`;
  const start=shiftDay(end,1-days);
  return {start,end,previousStart:shiftDay(start,-days),previousEnd:shiftDay(start,-1)};
}
export function bucketSales(rows:SalesDay[],start:string,end:string,grain:"day"|"week"|"month"):SalesBucket[] {
  const byDay=new Map(rows.map(row=>[row.day,row]));
  const buckets:{start:string;end:string;transactions:number;cents:bigint;key:string}[]=[];
  let index=0;
  for(let day=start;day<=end;day=shiftDay(day,1),index++){
    const key=grain==="day"?day:grain==="week"?String(Math.floor(index/7)):day.slice(0,7);
    let bucket=buckets[buckets.length-1];
    if(!bucket||bucket.key!==key){bucket={start:day,end:day,transactions:0,cents:0n,key};buckets.push(bucket);}
    const row=byDay.get(day);
    bucket.end=day;
    if(row){bucket.transactions+=row.transactions;bucket.cents+=lineCents(row.revenue,"1");}
  }
  return buckets.map(bucket=>({start:bucket.start,end:bucket.end,transactions:bucket.transactions,revenue:decimalAmount(bucket.cents)}));
}
export function relativeChange(current:number,previous:number):number|null {
  return previous===0?(current===0?0:null):(current-previous)/Math.abs(previous)*100;
}
