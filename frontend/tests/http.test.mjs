import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchWithReadRetry} from '../src/services/http.ts';

test('retries a transient GET 503 once',async()=>{
 let calls=0;
 const response=await fetchWithReadRetry('/test',{},async()=>new Response('',{status:++calls===1?503:200}));
 assert.equal(response.status,200);assert.equal(calls,2);
});
test('never repeats a write after a server error',async()=>{
 let calls=0;
 const response=await fetchWithReadRetry('/test',{method:'POST'},async()=>{calls++;return new Response('',{status:503})});
 assert.equal(response.status,503);assert.equal(calls,1);
});
test('never repeats a write after a network error',async()=>{
 let calls=0;
 await assert.rejects(fetchWithReadRetry('/test',{method:'POST'},async()=>{calls++;throw new TypeError('offline')}));
 assert.equal(calls,1);
});
test('stops after two failed reads',async()=>{
 let calls=0;
 await assert.rejects(fetchWithReadRetry('/test',{},async()=>{calls++;throw new TypeError('offline')}));
 assert.equal(calls,2);
});
test('does not repeat unauthorized requests',async()=>{
 let calls=0;
 const response=await fetchWithReadRetry('/test',{},async()=>{calls++;return new Response('',{status:401})});
 assert.equal(response.status,401);assert.equal(calls,1);
});
