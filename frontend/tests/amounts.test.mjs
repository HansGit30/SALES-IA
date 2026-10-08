import test from "node:test";
import assert from "node:assert/strict";
import { lineCents, decimalAmount, saleLineAmounts } from "../src/services/amounts.ts";

test("rounds fractional units half up as the API does", () => {
  assert.equal(lineCents("1.00", "1.005"), 101n);
  assert.equal(lineCents("1.00", "1.004"), 100n);
  assert.equal(lineCents(1.5, "2"), 300n);
});
test("rounds each line before adding the payment", () => {
  assert.equal(decimalAmount(lineCents("0.01", "0.5") + lineCents("0.01", "0.5")), "0.02");
});
test("retains precision for large catalog prices", () => {
  assert.equal(decimalAmount(lineCents("999999999999.99", "1")), "999999999999.99");
});
test("rejects invalid input and quantities beyond three decimals", () => {
  for (const value of ["", "-1", "NaN", "0.0001"]) assert.throws(() => lineCents("10.00", value));
});

test("applies discount before tax with decimal half-up rounding",()=>{
 assert.deepEqual(saleLineAmounts("10.00","2","10","18"),{subtotal:2000n,discount:200n,tax:324n,total:2124n});
 assert.deepEqual(saleLineAmounts("0.05","1","10","10"),{subtotal:5n,discount:1n,tax:0n,total:4n});
 assert.equal(saleLineAmounts("10.00","1","100","18").total,0n);
});
test("rejects malformed or excessive tax and discount percentages",()=>{
 for(const value of ["-1","100.01","0.001","","NaN"]) {
  assert.throws(()=>saleLineAmounts("10","1",value,"0"));
  assert.throws(()=>saleLineAmounts("10","1","0",value));
 }
});
