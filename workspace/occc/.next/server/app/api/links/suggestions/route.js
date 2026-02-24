"use strict";(()=>{var e={};e.id=2761,e.ids=[2761],e.modules={5890:e=>{e.exports=require("better-sqlite3")},399:e=>{e.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},7147:e=>{e.exports=require("fs")},1017:e=>{e.exports=require("path")},3585:(e,t,a)=>{a.r(t),a.d(t,{originalPathname:()=>T,patchFetch:()=>g,requestAsyncStorage:()=>u,routeModule:()=>l,serverHooks:()=>m,staticGenerationAsyncStorage:()=>p});var n={};a.r(n),a.d(n,{GET:()=>c});var i=a(9303),s=a(8716),r=a(670),d=a(7070),o=a(1364);async function c(){try{let e=(0,o.T5)();return d.NextResponse.json(e)}catch(e){return console.error("[API] Failed to fetch suggestions:",e),d.NextResponse.json({error:"Failed to fetch suggestions"},{status:500})}}let l=new i.AppRouteRouteModule({definition:{kind:s.x.APP_ROUTE,page:"/api/links/suggestions/route",pathname:"/api/links/suggestions",filename:"route",bundlePath:"app/api/links/suggestions/route"},resolvedPagePath:"/home/ollie/.openclaw/workspace/occc/src/app/api/links/suggestions/route.ts",nextConfigOutput:"",userland:n}),{requestAsyncStorage:u,staticGenerationAsyncStorage:p,serverHooks:m}=l,T="/api/links/suggestions/route";function g(){return(0,r.patchFetch)({serverHooks:m,staticGenerationAsyncStorage:p})}},9303:(e,t,a)=>{e.exports=a(517)},2109:(e,t,a)=>{function n(e,t){let a=0,n=new Set;if(RegExp(`\\b${t.id}\\b`,"i").test(e.content)&&(a=.95,n.add("explicit_mention")),e.embedding&&t.embedding){let i=Math.max(0,function(e,t){if(e.length!==t.length||0===e.length)return 0;let a=0,n=0,i=0;for(let s=0;s<e.length;s++)a+=e[s]*t[s],n+=e[s]*e[s],i+=t[s]*t[s];return a/(Math.sqrt(n)*Math.sqrt(i))}(e.embedding,t.embedding));i>a&&(a=i),i>.6&&n.add("semantic_similarity")}let r=i(e.content),d=i(t.content),o=r.filter(e=>d.includes(e));if(o.length>0){let e=Math.min(.5,.1*o.length);e>a&&(a=e),n.add("keyword_overlap")}let c=s(e),l=s(t);return c>0&&l>0&&1728e5>Math.abs(c-l)&&(a+=.1,n.add("temporal_proximity")),{score:Math.min(1,a),reasons:Array.from(n)}}function i(e){let t=["api","database","frontend","backend","auth","security","privacy","sync","vector","embedding","docker","container","ui","ux","performance","scalability","react","nextjs","typescript","sqlite","vss","search","index","summary","decision","issue","link","suggestion","review","loop","autonomous","agent","executor"];return Array.from(new Set(e.toLowerCase().split(/\W+/).filter(e=>t.includes(e))))}function s(e){return e.metadata?.created_at?new Date(e.metadata.created_at).getTime():e.metadata?.timestamp?new Date(e.metadata.timestamp).getTime():0}a.d(t,{m:()=>n})},1364:(e,t,a)=>{a.d(t,{Bj:()=>g,G_:()=>m,K2:()=>y,SK:()=>T,T5:()=>E,YE:()=>p,i$:()=>_});var n=a(5890),i=a.n(n),s=a(1017),r=a.n(s),d=a(7147),o=a.n(d),c=a(2109);let l=()=>{let e=process.env.OPENCLAW_ROOT||process.cwd();return r().join(e,"workspace",".openclaw","nexus-sync.db")};function u(){let e=l(),t=r().dirname(e);o().existsSync(t)||o().mkdirSync(t,{recursive:!0});let a=new(i())(e);return a.exec(`
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
  `),a}function p(e){let t=u();try{t.prepare(`
      INSERT INTO vector_cache (id, entity_type, content, metadata, embedding)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        entity_type = excluded.entity_type,
        content = excluded.content,
        metadata = excluded.metadata,
        embedding = excluded.embedding,
        created_at = CURRENT_TIMESTAMP
    `).run(e.id,e.entity_type,e.content,JSON.stringify(e.metadata),JSON.stringify(e.embedding))}finally{t.close()}}function m(e){let t=u();try{return t.prepare("SELECT * FROM vector_cache WHERE entity_type = ?").all(e).map(e=>({...e,metadata:JSON.parse(e.metadata),embedding:JSON.parse(e.embedding)}))}finally{t.close()}}function T(e){let t=u();try{let a=t.prepare("SELECT * FROM vector_cache WHERE id = ?").get(e);if(!a)return null;return{...a,metadata:JSON.parse(a.metadata),embedding:JSON.parse(a.embedding)}}finally{t.close()}}function g(e){let t=u();try{t.prepare(`
      INSERT INTO link_suggestions (id, decision_id, issue_id, score, status, reasons)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(decision_id, issue_id) DO UPDATE SET
        score = excluded.score,
        reasons = excluded.reasons,
        created_at = CURRENT_TIMESTAMP
    `).run(e.id,e.decision_id,e.issue_id,e.score,e.status,JSON.stringify(e.reasons))}finally{t.close()}}function E(){let e=u();try{return e.prepare(`
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
    `).all().map(e=>({...e,reasons:JSON.parse(e.reasons),decision_metadata:JSON.parse(e.decision_metadata),issue_metadata:JSON.parse(e.issue_metadata)}))}finally{e.close()}}function _(e,t){let a=u();try{return a.prepare("UPDATE link_suggestions SET status = ? WHERE id = ?").run(t,e).changes>0}finally{a.close()}}async function y(e,t){let a=u();try{let n="SELECT * FROM vector_cache WHERE 1=1",i=[];return e.timeRange.start&&(n+=" AND created_at >= ?",i.push(e.timeRange.start)),e.timeRange.end&&(n+=" AND created_at <= ?",i.push(e.timeRange.end)),a.prepare(n).all(...i).map(e=>({...e,metadata:JSON.parse(e.metadata),embedding:JSON.parse(e.embedding)})).map(a=>{let n=0;if(t){let i={id:"query",entity_type:"decision",content:e.query,metadata:{},embedding:t},{score:s}=(0,c.m)(i,a);n=s}else n=.5;return e.boostedProjectId&&a.metadata?.projectId===e.boostedProjectId&&(n+=.3),{...a,_score:Math.min(1,n)}}).sort((e,t)=>t._score-e._score).slice(0,e.limit)}finally{a.close()}}}};var t=require("../../../../webpack-runtime.js");t.C(e);var a=e=>t(t.s=e),n=t.X(0,[8948,7070],()=>a(3585));module.exports=n})();