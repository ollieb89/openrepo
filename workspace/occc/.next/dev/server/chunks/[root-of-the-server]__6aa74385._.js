module.exports = [
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[externals]/path [external] (path, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("path", () => require("path"));

module.exports = mod;
}),
"[externals]/fs [external] (fs, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("fs", () => require("fs"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/after-task-async-storage.external.js [external] (next/dist/server/app-render/after-task-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/after-task-async-storage.external.js", () => require("next/dist/server/app-render/after-task-async-storage.external.js"));

module.exports = mod;
}),
"[project]/src/lib/jarvis.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ActivityEntrySchema",
    ()=>ActivityEntrySchema,
    "JarvisStateSchema",
    ()=>JarvisStateSchema,
    "TaskSchema",
    ()=>TaskSchema,
    "parseJarvisState",
    ()=>parseJarvisState,
    "safeParseJarvisState",
    ()=>safeParseJarvisState
]);
/**
 * Jarvis Protocol TypeScript Types
 *
 * Type definitions matching the Jarvis Protocol schema from orchestration/state_engine.py
 * Includes Zod schemas for runtime validation.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__ = __turbopack_context__.i("[project]/node_modules/zod/v4/classic/external.js [app-route] (ecmascript) <export * as z>");
;
const ActivityEntrySchema = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].object({
    timestamp: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].number(),
    status: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string(),
    entry: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string()
});
const TaskSchema = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].object({
    status: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].enum([
        'pending',
        'in_progress',
        'completed',
        'failed'
    ]),
    skill_hint: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string().optional(),
    activity_log: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].array(ActivityEntrySchema),
    created_at: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].number(),
    updated_at: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].number(),
    metadata: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].record(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string(), __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].any()).optional()
});
const JarvisStateSchema = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].object({
    version: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].union([
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string(),
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].number()
    ]),
    protocol: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].literal('jarvis').optional(),
    tasks: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].record(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].string(), TaskSchema),
    metadata: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].object({
        created_at: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].number().optional(),
        last_updated: __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$zod$2f$v4$2f$classic$2f$external$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__$3c$export__$2a$__as__z$3e$__["z"].number()
    })
});
function parseJarvisState(data) {
    return JarvisStateSchema.parse(data);
}
function safeParseJarvisState(data) {
    const result = JarvisStateSchema.safeParse(data);
    if (result.success) {
        return {
            success: true,
            data: result.data
        };
    }
    return {
        success: false,
        error: result.error
    };
}
}),
"[project]/src/lib/metrics.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * Agent Hierarchy and Metrics Derivation
 *
 * Builds agent hierarchy from openclaw.json and derives metrics from workspace-state.json
 */ __turbopack_context__.s([
    "buildAgentHierarchy",
    ()=>buildAgentHierarchy,
    "deriveSwarmMetrics",
    ()=>deriveSwarmMetrics
]);
// ============================================================================
// Helper Functions
// ============================================================================
/**
 * Determine agent status based on task states
 * - 'working': has in_progress tasks
 * - 'error': has failed tasks
 * - 'idle': no tasks or all completed
 * - 'offline': container not found (detected via metadata)
 */ function deriveAgentStatus(agentId, state) {
    const taskEntries = Object.entries(state.tasks);
    const tasks = taskEntries.filter(([, task])=>task.metadata?.agent_id === agentId || String(task.metadata?.container_name || '').includes(agentId));
    if (tasks.length === 0) {
        return 'idle';
    }
    const hasInProgress = tasks.some(([, task])=>task.status === 'in_progress');
    const hasFailed = tasks.some(([, task])=>task.status === 'failed');
    const allCompleted = tasks.every(([, task])=>task.status === 'completed');
    if (hasInProgress) return 'working';
    if (hasFailed) return 'error';
    if (allCompleted) return 'idle';
    return 'idle';
}
/**
 * Find the current active task for an agent
 */ function findCurrentTask(agentId, state) {
    const taskEntries = Object.entries(state.tasks);
    const inProgressTask = taskEntries.find(([, task])=>task.status === 'in_progress' && (task.metadata?.agent_id === agentId || String(task.metadata?.container_name || '').includes(agentId)));
    if (inProgressTask) {
        const [taskId, task] = inProgressTask;
        const latestActivity = task.activity_log[task.activity_log.length - 1];
        return latestActivity?.entry || `Task ${taskId}`;
    }
    return undefined;
}
function buildAgentHierarchy(agents, state) {
    // Build ID set for referent validation
    const agentIds = new Set(agents.map((a)=>a.id));
    // Validate reports_to references (warn on missing referent)
    agents.forEach((agent)=>{
        if (agent.reports_to && !agentIds.has(agent.reports_to)) {
            console.warn(`[hierarchy] Agent '${agent.id}' reports_to '${agent.reports_to}' which is not in the agents list`);
        }
    });
    // Detect circular chains via path-length guard
    agents.forEach((agent)=>{
        let current = agent.reports_to;
        let steps = 0;
        while(current && steps <= agents.length){
            const parent = agents.find((a)=>a.id === current);
            current = parent?.reports_to ?? null;
            steps++;
        }
        if (steps > agents.length) {
            console.warn(`[hierarchy] Circular reports_to chain detected starting from '${agent.id}'`);
        }
    });
    return agents.map((agent)=>{
        const level = agent.level || 1;
        const status = deriveAgentStatus(agent.id, state);
        const currentTask = findCurrentTask(agent.id, state);
        // Determine container name from metadata or construct it
        const taskValues = Object.values(state.tasks);
        const foundTask = taskValues.find((task)=>task.metadata?.agent_id === agent.id);
        const containerName = String(foundTask?.metadata?.container_name || `openclaw-${level === 3 ? 'l3-' : ''}${agent.id}`);
        return {
            id: agent.id,
            name: agent.name,
            level,
            status,
            currentTask,
            reports_to: agent.reports_to,
            container_name: containerName
        };
    });
}
function deriveSwarmMetrics(agents, state) {
    const totalByTier = {
        L1: agents.filter((a)=>a.level === 1).length,
        L2: agents.filter((a)=>a.level === 2).length,
        L3: agents.filter((a)=>a.level === 3).length
    };
    const active = agents.filter((a)=>a.status === 'working').length;
    const idle = agents.filter((a)=>a.status === 'idle').length;
    const errored = agents.filter((a)=>a.status === 'error').length;
    const allTasks = Object.values(state.tasks);
    const totalTasks = allTasks.length;
    const completedTasks = allTasks.filter((t)=>t.status === 'completed').length;
    const failedTasks = allTasks.filter((t)=>t.status === 'failed').length;
    return {
        totalByTier,
        active,
        idle,
        errored,
        totalTasks,
        completedTasks,
        failedTasks
    };
}
}),
"[project]/src/lib/projects.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "OPENCLAW_ROOT",
    ()=>OPENCLAW_ROOT,
    "getDefaultProject",
    ()=>getDefaultProject,
    "resolveProjectsDir",
    ()=>resolveProjectsDir,
    "resolveStateFilePath",
    ()=>resolveStateFilePath
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/path [external] (path, cjs)");
var __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/fs [external] (fs, cjs)");
;
;
const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
function resolveStateFilePath(projectId) {
    return __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__["default"].join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'workspace-state.json');
}
function resolveProjectsDir() {
    return __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__["default"].join(OPENCLAW_ROOT, 'projects');
}
async function getDefaultProject() {
    try {
        const projectsDir = resolveProjectsDir();
        const entries = await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].readdir(projectsDir, {
            withFileTypes: true
        });
        const candidates = [];
        for (const entry of entries){
            if (!entry.isDirectory() || entry.name.startsWith('_')) continue;
            const projectJsonPath = __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__["default"].join(projectsDir, entry.name, 'project.json');
            try {
                await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].access(projectJsonPath);
                candidates.push(entry.name);
            } catch  {
            // No project.json — skip
            }
        }
        candidates.sort();
        return candidates.length > 0 ? candidates[0] : null;
    } catch  {
        return null;
    }
}
}),
"[project]/src/app/api/swarm/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "GET",
    ()=>GET,
    "emptySwarmState",
    ()=>emptySwarmState,
    "getSwarmState",
    ()=>getSwarmState
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/path [external] (path, cjs)");
var __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/fs [external] (fs, cjs)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$jarvis$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/jarvis.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$metrics$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/metrics.ts [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/projects.ts [app-route] (ecmascript)");
;
;
;
;
;
;
const stateCache = new Map();
const CACHE_TTL_MS = 500; // 500ms TTL as per plan requirements
// Global config path — openclaw.json is not per-project
const DEFAULT_OPENCLAW_CONFIG = '/home/ollie/.openclaw/openclaw.json';
async function readStateFile(projectId) {
    const stateFilePath = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["resolveStateFilePath"])(projectId);
    const [data, stats] = await Promise.all([
        __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].readFile(stateFilePath, 'utf8'),
        __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].stat(stateFilePath)
    ]);
    return {
        data,
        mtime: stats.mtimeMs
    };
}
async function readOpenClawConfig() {
    const configPath = process.env.OPENCLAW_CONFIG || DEFAULT_OPENCLAW_CONFIG;
    const data = await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].readFile(configPath, 'utf8');
    const config = JSON.parse(data);
    return {
        agents: config.agents?.list || []
    };
}
async function getSwarmState(projectId) {
    const now = Date.now();
    // Check cache validity
    const cached = stateCache.get(projectId);
    if (cached && now - cached.timestamp < CACHE_TTL_MS) {
        return {
            agents: cached.agentNodes,
            metrics: cached.metrics,
            state: cached.state,
            lastUpdated: new Date(cached.mtime).toISOString()
        };
    }
    // Read state file and check mtime
    const { data: stateData, mtime } = await readStateFile(projectId);
    // If we have a cache with the same mtime, use it
    if (cached && cached.mtime === mtime) {
        stateCache.set(projectId, {
            ...cached,
            timestamp: now
        });
        return {
            agents: cached.agentNodes,
            metrics: cached.metrics,
            state: cached.state,
            lastUpdated: new Date(mtime).toISOString()
        };
    }
    // Parse and validate state
    const rawState = JSON.parse(stateData);
    const state = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$jarvis$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["parseJarvisState"])(rawState);
    // Read agent config
    const { agents: agentConfigs } = await readOpenClawConfig();
    // Build hierarchy and metrics
    const agentNodes = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$metrics$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["buildAgentHierarchy"])(agentConfigs, state);
    const metrics = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$metrics$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["deriveSwarmMetrics"])(agentNodes, state);
    // Update per-project cache
    stateCache.set(projectId, {
        state,
        agents: agentConfigs,
        agentNodes,
        metrics,
        mtime,
        timestamp: now
    });
    return {
        agents: agentNodes,
        metrics,
        state,
        lastUpdated: new Date(mtime).toISOString()
    };
}
function emptySwarmState() {
    const state = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$jarvis$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["parseJarvisState"])({
        version: '1.0',
        tasks: {},
        metadata: {
            last_updated: Date.now()
        }
    });
    const metrics = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$metrics$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["deriveSwarmMetrics"])([], state);
    return {
        agents: [],
        metrics,
        state,
        lastUpdated: new Date().toISOString()
    };
}
async function GET(request) {
    try {
        const searchParams = new URL(request.url).searchParams;
        let projectId = searchParams.get('project');
        // Fallback to first available project if no param provided
        if (!projectId) {
            projectId = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["getDefaultProject"])();
        }
        if (!projectId) {
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: 'No projects found'
            }, {
                status: 404
            });
        }
        // Validate project existence: check project.json in projects/<id>/
        const projectJsonPath = __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__["default"].join((0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["resolveProjectsDir"])(), projectId, 'project.json');
        try {
            await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].access(projectJsonPath);
        } catch  {
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
                error: 'Project not found',
                project: projectId
            }, {
                status: 404
            });
        }
        // Attempt to read state — return empty state if state file doesn't exist yet
        try {
            const swarmState = await getSwarmState(projectId);
            return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(swarmState);
        } catch (stateError) {
            const msg = stateError instanceof Error ? stateError.message : String(stateError);
            // If state file simply doesn't exist, return empty state (not an error)
            if (msg.includes('ENOENT') || msg.includes('no such file')) {
                return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json(emptySwarmState());
            }
            throw stateError;
        }
    } catch (error) {
        console.error('Error reading swarm state:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: 'Failed to read swarm state',
            detail: errorMessage
        }, {
            status: 500
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__6aa74385._.js.map