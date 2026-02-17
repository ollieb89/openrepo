# Research Summary: OpenClaw Ecosystem

**Domain:** AI Swarm Orchestration / Monitoring
**Researched:** 2026-02-17
**Overall confidence:** HIGH

## Executive Summary

The OpenClaw ecosystem is transitioning from a flat multi-agent model to the **Grand Architect Protocol**, a three-tiered hierarchical swarm designed to minimize cognitive load ("brain fog") and maximize execution parallelism. The architecture isolates strategy, management, and execution across three distinct levels, physically enforced via Docker containerization on an Ubuntu 24.04 host.

The **PumplAI Pilot** serves as the reference implementation, demonstrating how a Level 2 Project Manager orchestrates Level 3 Frontend and Backend specialists. Central to this system is the **Jarvis Protocol**, a shared `state.json` file that synchronizes status across isolated containers, which is then visualized in the **occc Dashboard**—a real-time monitoring tool built with Next.js 16 and Tailwind 4.

## Key Findings

**Stack:** OpenClaw core with Next.js 16 dashboard, powered by Gemini 2.5/3.0 on Ubuntu 24.04.
**Architecture:** 3-tier hierarchy (Strategic L1, Tactical L2, Execution L3) with hub-and-spoke communication.
**Critical pitfall:** Cognitive Overload ("Brain Fog") caused by context bleeding in non-isolated agent environments.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Environment Substrate** - Establish the Ubuntu 24.04 host, Nvidia drivers, and Docker network.
   - Addresses: Resource isolation and GPU access.
   - Avoids: VRAM contention and toolchain conflicts.

2. **Core Orchestration (L1/L2)** - Configure ClawdiaPrime (L1) and Domain PMs (L2).
   - Addresses: Task routing and planning logic.
   - Avoids: Implementation hallucinations in strategy layers.

3. **Specialist Workers (L3)** - Deploy project-scoped specialists (Frontend/Backend/ML).
   - Addresses: Parallel execution and semantic snapshotting.
   - Avoids: Spaghetti code through volume scoping.

4. **Monitoring Uplink (occc)** - Deploy the Next.js dashboard for real-time human oversight.
   - Addresses: Global metrics and live log feeds.
   - Avoids: System blindness during complex swarm operations.

**Phase ordering rationale:**
- Infrastructure must precede agents to ensure physical isolation is present from day one. Routing (L1/L2) must be established before implementation (L3) to maintain architectural integrity. The dashboard is the final layer to provide visibility into the running system.

**Research flags for phases:**
- Phase 1: Likely needs deeper research into Nvidia Container Toolkit compatibility with Ubuntu 24.04 (specifically driver version 550+).
- Phase 3: Semantic Snapshot implementation details for Playwright integration need validation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Explicitly defined in `package.json` and `SWARM_PLAN.md`. |
| Features | HIGH | Table stakes and differentiators mapped from design docs. |
| Architecture | HIGH | 3-tier model is the core of the Grand Architect Protocol. |
| Pitfalls | MEDIUM | Derived from design doc warnings and common multi-agent failure modes. |

## Gaps to Address

- **Real-time Communication:** The design mentions "Lane Queues" and "state.json". Need to verify if actual WebSockets are planned for L3 -> Dashboard for lower latency than 2s polling.
- **Security Redaction:** The automated redaction logic in `PM-ShDebug` needs a concrete regex list.
