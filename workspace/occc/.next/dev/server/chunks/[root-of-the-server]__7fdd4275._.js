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
"[project]/src/app/api/projects/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "GET",
    ()=>GET
]);
var __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/path [external] (path, cjs)");
var __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__ = __turbopack_context__.i("[externals]/fs [external] (fs, cjs)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/server.js [app-route] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/projects.ts [app-route] (ecmascript)");
;
;
;
;
/**
 * Derives project status from the workspace state file.
 * - 'active'  → state file exists and has in_progress tasks
 * - 'error'   → state file exists, has failed tasks, no in_progress tasks
 * - 'idle'    → state file missing or no in_progress/failed tasks
 */ async function deriveProjectStatus(projectId) {
    const stateFilePath = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["resolveStateFilePath"])(projectId);
    try {
        const data = await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].readFile(stateFilePath, 'utf8');
        const state = JSON.parse(data);
        const tasks = state.tasks || {};
        const taskList = Object.values(tasks);
        const hasInProgress = taskList.some((t)=>t.status === 'in_progress');
        const hasFailed = taskList.some((t)=>t.status === 'failed');
        if (hasInProgress) return 'active';
        if (hasFailed) return 'error';
        return 'idle';
    } catch  {
        // State file missing or unreadable → idle
        return 'idle';
    }
}
async function GET() {
    try {
        const projectsDir = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$projects$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["resolveProjectsDir"])();
        const entries = await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].readdir(projectsDir, {
            withFileTypes: true
        });
        const projects = [];
        for (const entry of entries){
            if (!entry.isDirectory() || entry.name.startsWith('_')) continue;
            const projectJsonPath = __TURBOPACK__imported__module__$5b$externals$5d2f$path__$5b$external$5d$__$28$path$2c$__cjs$29$__["default"].join(projectsDir, entry.name, 'project.json');
            try {
                const raw = await __TURBOPACK__imported__module__$5b$externals$5d2f$fs__$5b$external$5d$__$28$fs$2c$__cjs$29$__["promises"].readFile(projectJsonPath, 'utf8');
                const parsed = JSON.parse(raw);
                const id = parsed.id || entry.name;
                const name = parsed.name || id;
                const status = await deriveProjectStatus(id);
                projects.push({
                    id,
                    name,
                    status
                });
            } catch  {
            // Skip directories without a valid project.json
            }
        }
        // Sort alphabetically by name
        projects.sort((a, b)=>a.name.localeCompare(b.name));
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            projects
        });
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error('[projects] Error scanning projects directory:', errorMessage);
        return __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$server$2e$js__$5b$app$2d$route$5d$__$28$ecmascript$29$__["NextResponse"].json({
            error: `Failed to scan projects: ${errorMessage}`,
            projects: []
        }, {
            status: 500
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__7fdd4275._.js.map