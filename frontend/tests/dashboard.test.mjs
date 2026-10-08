import test from "node:test";
import assert from "node:assert/strict";
import { dashboardWindow, bucketSales, relativeChange } from "../src/services/dashboard.ts";

test("uses the Lima day and adjacent equal-length comparison windows",()=>{
  assert.deepEqual(dashboardWindow(7,new Date("2026-10-02T02:00:00Z")),{
    start:"2026-09-25",end:"2026-10-01",previousStart:"2026-09-18",previousEnd:"2026-09-24"
  });
});
test("includes missing days as zero without losing revenue",()=>{
  const rows=bucketSales([{day:"2026-10-01",transactions:2,revenue:"0.03"},{day:"2026-10-03",transactions:1,revenue:"0.07"}],"2026-10-01","2026-10-03","day");
  assert.equal(rows.length,3);assert.equal(rows[1].revenue,"0.00");
  assert.equal(rows[2].transactions,1);
});
test("weekly and monthly buckets preserve all amounts and partial periods",()=>{
  const data=[{day:"2026-09-30",transactions:1,revenue:"10.25"},{day:"2026-10-08",transactions:2,revenue:"20.35"}];
  const weekly=bucketSales(data,"2026-09-30","2026-10-08","week");
  assert.deepEqual(weekly.map(b=>b.revenue),["10.25","20.35"]);
  assert.equal(weekly[1].end,"2026-10-08");
  const monthly=bucketSales(data,"2026-09-30","2026-10-08","month");
  assert.equal(monthly.length,2);assert.equal(monthly[1].start,"2026-10-01");
});
test("zero comparison baseline does not invent a percentage",()=>{
  assert.equal(relativeChange(10,0),null);assert.equal(relativeChange(0,0),0);
  assert.equal(relativeChange(75,100),-25);
});
