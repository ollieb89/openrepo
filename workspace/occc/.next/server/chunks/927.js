"use strict";exports.id=927,exports.ids=[927],exports.modules={491:(e,t,n)=>{n.d(t,{QI:()=>_,Vo:()=>g,_P:()=>O,bu:()=>T,ej:()=>f,ic:()=>h,rP:()=>S,uZ:()=>y,wI:()=>E});var r=n(3292),a=n.n(r),i=n(1017),o=n.n(i);let s=process.env.OPENCLAW_ROOT||"/home/ollie/.openclaw",c=o().join(s,"workspace",".openclaw","connectors","runtime-store.json"),d=Promise.resolve();function l(){return process.env.CONNECTOR_RUNTIME_STORE_PATH||c}async function u(){try{let e=await a().readFile(l(),"utf-8"),t=JSON.parse(e);return{connectors:t.connectors||{},checkpoints:t.checkpoints||{},progress:t.progress||{}}}catch{return{connectors:{},checkpoints:{},progress:{}}}}async function m(e){let t=l();await a().mkdir(o().dirname(t),{recursive:!0}),await a().writeFile(t,JSON.stringify(e,null,2),"utf-8")}function p(e){let t=d.then(e);return d=t.then(()=>void 0,()=>void 0),t}async function f(){return Object.values((await u()).connectors)}async function y(e){return(await u()).connectors[e]||null}async function g(e){return p(async()=>{let t=new Date().toISOString(),n=await u(),r=n.connectors[e.id],a={...e,createdAt:r?.createdAt||e.createdAt||t,updatedAt:e.updatedAt||t};return n.connectors[e.id]=a,await m(n),a})}async function h(e,t){return p(async()=>{let n=new Date().toISOString(),r=await u(),a=r.connectors[e];if(!a)return null;let i={...a,status:t.status,lastError:t.lastError,lastSyncedAt:t.lastSyncedAt||a.lastSyncedAt,updatedAt:n};return r.connectors[e]=i,await m(r),i})}async function S(e){return(await u()).checkpoints[e]||null}async function E(e,t){return p(async()=>{let n=await u();return n.checkpoints[e]=t,await m(n),t})}async function _(){return Object.values((await u()).checkpoints)}async function T(e,t){return p(async()=>{let n=await u();return n.progress[e]=t,await m(n),t})}async function O(e){let t=Object.values((await u()).progress);return e?t.filter(t=>t.connectorId===e):t}},6555:(e,t,n)=>{n.d(t,{C6:()=>l,MF:()=>c,streamCompletion:()=>d});var r=n(5553);let a=process.env.OLLAMA_HOST||"http://localhost:11434",i="phi3:mini",o=new r._({host:a});async function s(){try{return await o.list(),!0}catch(e){return console.warn("[Ollama] Local Ollama service not available:",e),!1}}async function c(e,t={}){if(!await s())throw Error("Ollama service is not available");try{return(await o.generate({model:i,prompt:e,options:{temperature:t.temperature??0},stream:!1})).response}catch(e){throw console.error("[Ollama] Error generating completion:",e),e}}async function*d(e,t={}){if(!await s())throw Error("Ollama service is not available");try{for await(let n of(await o.generate({model:t.model??i,prompt:e,options:{temperature:t.temperature??0},stream:!0})))yield n.response}catch(e){throw console.error("[Ollama] Error in streaming completion:",e),e}}async function l(e){if(!await s())throw Error("Ollama service is not available");try{return(await o.embeddings({model:"mxbai-embed-large",prompt:e})).embedding}catch(e){throw console.error("[Ollama] Error generating embedding:",e),e}}},7174:(e,t,n)=>{n.d(t,{i:()=>a});let r=[/(['"`]?)(api[_-]?key|apikey|token|secret|password|pass)['"`]?\s*[:=]\s*['"`]?([a-zA-Z0-9_-]{20,})['"`]?/gi,/bearer\s+([a-zA-Z0-9._-]+)/gi,/eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*/g,/(['"`]?)([a-zA-Z_][a-zA-Z0-9_]*['"`]?\s*[:=]\s*['"`]?)([a-zA-Z0-9+/]{40,})['"`]?/gi,/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g];function a(e){let t=e;for(let e of r)t=t.replace(e,(e,...t)=>t.length>=3?`${t[0]}${t[1]}[REDACTED]`:(t.length,"[REDACTED]"));return t}},8960:(e,t,n)=>{n.d(t,{t:()=>i});var r=n(6555),a=n(1364);async function i(e,t,n,i){try{let o=await (0,r.C6)(n);(0,a.YE)({id:e,entity_type:t,content:n,metadata:i,embedding:o})}catch(n){throw console.error(`[Indexer] Failed to index entity ${t}:${e}:`,n),n}}},2109:(e,t,n)=>{function r(e,t){let n=0,r=new Set;if(RegExp(`\\b${t.id}\\b`,"i").test(e.content)&&(n=.95,r.add("explicit_mention")),e.embedding&&t.embedding){let a=Math.max(0,function(e,t){if(e.length!==t.length||0===e.length)return 0;let n=0,r=0,a=0;for(let i=0;i<e.length;i++)n+=e[i]*t[i],r+=e[i]*e[i],a+=t[i]*t[i];return n/(Math.sqrt(r)*Math.sqrt(a))}(e.embedding,t.embedding));a>n&&(n=a),a>.6&&r.add("semantic_similarity")}let o=a(e.content),s=a(t.content),c=o.filter(e=>s.includes(e));if(c.length>0){let e=Math.min(.5,.1*c.length);e>n&&(n=e),r.add("keyword_overlap")}let d=i(e),l=i(t);return d>0&&l>0&&1728e5>Math.abs(d-l)&&(n+=.1,r.add("temporal_proximity")),{score:Math.min(1,n),reasons:Array.from(r)}}function a(e){let t=["api","database","frontend","backend","auth","security","privacy","sync","vector","embedding","docker","container","ui","ux","performance","scalability","react","nextjs","typescript","sqlite","vss","search","index","summary","decision","issue","link","suggestion","review","loop","autonomous","agent","executor"];return Array.from(new Set(e.toLowerCase().split(/\W+/).filter(e=>t.includes(e))))}function i(e){return e.metadata?.created_at?new Date(e.metadata.created_at).getTime():e.metadata?.timestamp?new Date(e.metadata.timestamp).getTime():0}n.d(t,{m:()=>r})},7347:(e,t,n)=>{n.d(t,{AQ:()=>u,fH:()=>d,fX:()=>l,sF:()=>m});var r=n(7147),a=n.n(r),i=n(1017),o=n.n(i),s=n(7174);let c=()=>{let e=process.env.OPENCLAW_ROOT||process.cwd();return o().join(e,"workspace",".openclaw","records")};async function d(e,t,n){if(0===n.length)return;let r=o().join(c(),e);a().existsSync(r)||a().mkdirSync(r,{recursive:!0});let i=o().join(r,`${t}.json`),d=[];if(a().existsSync(i))try{let e=a().readFileSync(i,"utf8");d=JSON.parse(e)}catch(e){console.error(`Failed to load existing records from ${i}:`,e)}let l=n.map(e=>{let t={...e.payload};return"string"==typeof t.text&&(t.text=(0,s.i)(t.text)),t.raw&&"string"==typeof t.raw.text&&(t.raw.text=(0,s.i)(t.raw.text)),{...e,payload:t}}),u=new Map;d.forEach(e=>u.set(e.id,e)),l.forEach(e=>u.set(e.id,e));let m=Array.from(u.values());a().writeFileSync(i,JSON.stringify(m,null,2))}async function l(e,t){let n=o().join(c(),e,`${t}.json`);if(!a().existsSync(n))return[];try{let e=a().readFileSync(n,"utf8");return JSON.parse(e)}catch(e){return console.error(`Failed to load records from ${n}:`,e),[]}}async function u(e,t){if(0===t.length)return;let n=o().join(c(),"decisions");a().existsSync(n)||a().mkdirSync(n,{recursive:!0});let r=o().join(n,`${e}.json`),i=[];if(a().existsSync(r))try{let e=a().readFileSync(r,"utf8");i=JSON.parse(e)}catch(e){console.error(`Failed to load decisions from ${r}:`,e)}let s=new Map;i.forEach(e=>s.set(e.id,e)),t.forEach(e=>s.set(e.id,e)),a().writeFileSync(r,JSON.stringify(Array.from(s.values()),null,2))}async function m(e){let t=o().join(c(),"decisions",`${e}.json`);if(!a().existsSync(t))return[];try{let e=a().readFileSync(t,"utf8");return JSON.parse(e)}catch(e){return console.error(`Failed to load decisions from ${t}:`,e),[]}}},8858:(e,t,n)=>{n.d(t,{M:()=>d,v:()=>l});var r=n(6555),a=n(7347),i=n(8960),o=n(1364),s=n(2109);async function c(e){try{let t=(0,o.SK)(e);if(!t||"decision"!==t.entity_type){console.warn(`[Suggestions] Decision ${e} not found in vector cache.`);return}let n=(0,o.G_)("issue");if(0===n.length){console.log("[Suggestions] No issues found in cache to link against.");return}let r=0;for(let a of n){let{score:n,reasons:i}=(0,s.m)(t,a);n>=.6&&((0,o.Bj)({id:crypto.randomUUID(),decision_id:e,issue_id:a.id,score:n,status:"pending",reasons:i}),r++)}r>0&&console.log(`[Suggestions] Generated ${r} suggestions for decision ${e}`)}catch(t){console.error(`[Suggestions] Failed to generate suggestions for decision ${e}:`,t)}}async function d(e,t,n,a){let i=a?`

USER HINT: ${a}
(Please incorporate this hint into your analysis.)`:"",o=`
Analyze the following Slack thread to extract key decisions. 
A decision is a consensus reached, a resolution to a debate, or a clear path forward.

Thread Content:
"""
${e.payload.text}
"""${i}

Think step-by-step:
1. Analyze the thread for proposals and debate.
2. Identify consensus (Convergent Evolution).
3. Extract the final Outcome.
4. Identify Participants (@mentions).
5. Extract Next Steps.
6. Find the "Smoking Gun" citation: the EXACT quote from the thread that confirms the decision.

Return your findings in the following format:
DECISION_START
Outcome: [Summary of the decision]
Participants: [List of @mentions, e.g. <@U12345>]
Next Steps: [Action items or "None"]
Citation: [Exact quote from the thread]
DECISION_END

If multiple decisions were made, provide multiple blocks. If no decision was made, return "NO_DECISION".
`.trim(),s=await (0,r.MF)(o,{temperature:0});if(s.includes("NO_DECISION"))return[];let c=[];for(let r of s.split("DECISION_START").filter(e=>e.includes("DECISION_END"))){let a=r.match(/Outcome:\s*(.*)/)?.[1]?.trim(),i=r.match(/Participants:\s*(.*)/)?.[1]?.trim()||"",o=r.match(/Next Steps:\s*(.*)/)?.[1]?.trim(),s=r.match(/Citation:\s*(.*)/)?.[1]?.trim();if(!a||!s)continue;let d=/<@U[A-Z0-9]+>/g,l=Array.from(new Set(i.match(d)||[])),u=/\b[A-Z0-9]{2,}-\d+\b/g,m=Array.from(new Set(r.match(u)||[])),p=s.replace(/^["']|["']$/g,"");if(!e.payload.text.includes(p)){console.warn(`[Summarizer] Citation validation failed for thread ${e.id}. Skipping decision block.`);continue}let f=new Date().toISOString();c.push({id:crypto.randomUUID(),threadId:e.id,connectorId:t,sourceId:n,outcome:a,participants:l,nextStep:o&&"None"!==o?o:null,citation:p,linearIds:m,isHidden:!1,createdAt:f,updatedAt:f})}return c}async function l(e,t){let n=await (0,a.fX)(e,t);if(0===n.length)return;let r=new Set((await (0,a.sF)(e)).map(e=>e.threadId)),o=n.filter(e=>!r.has(e.id));if(0===o.length){console.log(`[Summarizer] No new threads to process for ${e}::${t}`);return}console.log(`[Summarizer] Processing ${o.length} new threads for ${e}::${t}`);let s=[];for(let n of o)try{let r=await d(n,e,t);s.push(...r)}catch(e){console.error(`[Summarizer] Failed to process thread ${n.id}:`,e)}if(s.length>0)for(let t of(await (0,a.AQ)(e,s),console.log(`[Summarizer] Saved ${s.length} new decisions for ${e}`),s)){let e=`${t.outcome}

Citation: ${t.citation}`;(0,i.t)(t.id,"decision",e,{connectorId:t.connectorId,sourceId:t.sourceId,threadId:t.threadId}).then(()=>c(t.id)).catch(e=>{console.error(`[Summarizer] Failed to index or suggest for decision ${t.id}:`,e)})}else console.log(`[Summarizer] No decisions extracted from ${o.length} threads.`)}},1364:(e,t,n)=>{n.d(t,{Bj:()=>y,G_:()=>p,K2:()=>S,SK:()=>f,T5:()=>g,YE:()=>m,i$:()=>h});var r=n(5890),a=n.n(r),i=n(1017),o=n.n(i),s=n(7147),c=n.n(s),d=n(2109);let l=()=>{let e=process.env.OPENCLAW_ROOT||process.cwd();return o().join(e,"workspace",".openclaw","nexus-sync.db")};function u(){let e=l(),t=o().dirname(e);c().existsSync(t)||c().mkdirSync(t,{recursive:!0});let n=new(a())(e);return n.exec(`
    CREATE TABLE IF NOT EXISTS vector_cache (
      id TEXT PRIMARY KEY,
      entity_type TEXT NOT NULL, -- 'decision' or 'issue'
      content TEXT NOT NULL,
      metadata JSON,
      embedding JSON,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -- VSS table for 1024-dim vectors (mxbai-embed-large dimension)
    -- This requires the vss extension to be loaded
    -- CREATE VIRTUAL TABLE IF NOT EXISTS vss_cache USING vss0(
    --   embedding(1024)
    -- );

    CREATE TABLE IF NOT EXISTS link_suggestions (
      id TEXT PRIMARY KEY,
      decision_id TEXT NOT NULL,
      issue_id TEXT NOT NULL,
      score REAL NOT NULL,
      status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
      reasons JSON, -- e.g. ["explicit_mention", "semantic_similarity"]
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(decision_id, issue_id)
    );
  `),n}function m(e){let t=u();try{t.prepare(`
      INSERT INTO vector_cache (id, entity_type, content, metadata, embedding)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        entity_type = excluded.entity_type,
        content = excluded.content,
        metadata = excluded.metadata,
        embedding = excluded.embedding,
        created_at = CURRENT_TIMESTAMP
    `).run(e.id,e.entity_type,e.content,JSON.stringify(e.metadata),JSON.stringify(e.embedding))}finally{t.close()}}function p(e){let t=u();try{return t.prepare("SELECT * FROM vector_cache WHERE entity_type = ?").all(e).map(e=>({...e,metadata:JSON.parse(e.metadata),embedding:JSON.parse(e.embedding)}))}finally{t.close()}}function f(e){let t=u();try{let n=t.prepare("SELECT * FROM vector_cache WHERE id = ?").get(e);if(!n)return null;return{...n,metadata:JSON.parse(n.metadata),embedding:JSON.parse(n.embedding)}}finally{t.close()}}function y(e){let t=u();try{t.prepare(`
      INSERT INTO link_suggestions (id, decision_id, issue_id, score, status, reasons)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(decision_id, issue_id) DO UPDATE SET
        score = excluded.score,
        reasons = excluded.reasons,
        created_at = CURRENT_TIMESTAMP
    `).run(e.id,e.decision_id,e.issue_id,e.score,e.status,JSON.stringify(e.reasons))}finally{t.close()}}function g(){let e=u();try{return e.prepare(`
      SELECT 
        ls.*,
        d.content as decision_content,
        d.metadata as decision_metadata,
        i.content as issue_content,
        i.metadata as issue_metadata
      FROM link_suggestions ls
      JOIN vector_cache d ON ls.decision_id = d.id
      JOIN vector_cache i ON ls.issue_id = i.id
      WHERE ls.status = 'pending'
      ORDER BY ls.score DESC
    `).all().map(e=>({...e,reasons:JSON.parse(e.reasons),decision_metadata:JSON.parse(e.decision_metadata),issue_metadata:JSON.parse(e.issue_metadata)}))}finally{e.close()}}function h(e,t){let n=u();try{return n.prepare("UPDATE link_suggestions SET status = ? WHERE id = ?").run(t,e).changes>0}finally{n.close()}}async function S(e,t){let n=u();try{let r="SELECT * FROM vector_cache WHERE 1=1",a=[];return e.timeRange.start&&(r+=" AND created_at >= ?",a.push(e.timeRange.start)),e.timeRange.end&&(r+=" AND created_at <= ?",a.push(e.timeRange.end)),n.prepare(r).all(...a).map(e=>({...e,metadata:JSON.parse(e.metadata),embedding:JSON.parse(e.embedding)})).map(n=>{let r=0;if(t){let a={id:"query",entity_type:"decision",content:e.query,metadata:{},embedding:t},{score:i}=(0,d.m)(a,n);r=i}else r=.5;return e.boostedProjectId&&n.metadata?.projectId===e.boostedProjectId&&(r+=.3),{...n,_score:Math.min(1,r)}}).sort((e,t)=>t._score-e._score).slice(0,e.limit)}finally{n.close()}}}};