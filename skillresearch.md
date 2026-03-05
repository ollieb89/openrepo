# OpenClaw & ClawHub Skills Research

This document contains skill research results from searching the open agent skills ecosystem for OpenClaw, ClawHub, agent services, jobs, and personas.

## OpenClaw-specific Skills

| Skill | Description | Install |
|-------|-------------|---------|
| `adisinghstudent/easyclaw@openclaw-config` | OpenClaw configuration (most popular - 981 installs) | `npx skills add adisinghstudent/easyclaw@openclaw-config` |
| `sundial-org/awesome-openclaw-skills@proactive-agent` | Proactive agent patterns | `npx skills add sundial-org/awesome-openclaw-skills@proactive-agent` |
| `0xindiebruh/openclaw-mission-control-skill@openclaw-mission-control` | Mission control for OpenClaw | `npx skills add 0xindiebruh/openclaw-mission-control-skill@openclaw-mission-control` |
| `paulrberg/agent-skills@openclaw` | OpenClaw agent skills | `npx skills add paulrberg/agent-skills@openclaw` |
| `fanthus/agent-skills@openclaw-expert` | OpenClaw expert patterns | `npx skills add fanthus/agent-skills@openclaw-expert` |
| `agentlyhq/aixyz@aixyz-on-openclaw` | AIxyz integration on OpenClaw | `npx skills add agentlyhq/aixyz@aixyz-on-openclaw` |
| `mirangareddy/openclaw-essentials@openclaw-cli` | OpenClaw CLI essentials | `npx skills add mirangareddy/openclaw-essentials@openclaw-cli` |
| `anthemflynn/ccmp@openclaw-maintain` | OpenClaw maintenance | `npx skills add anthemflynn/ccmp@openclaw-maintain` |

## ClawHub Skills

| Skill | Description | Install |
|-------|-------------|---------|
| `steipete/clawdis@clawhub` | ClawHub integration (295 installs) | `npx skills add steipete/clawdis@clawhub` |
| `hugomrtz/skill-vetting-clawhub@clawhub-skill-vetting` | Skill vetting for ClawHub (209 installs) | `npx skills add hugomrtz/skill-vetting-clawhub@clawhub-skill-vetting` |
| `prompt-security/clawsec@clawsec-clawhub-checker` | Security checking for ClawHub | `npx skills add prompt-security/clawsec@clawsec-clawhub-checker` |
| `sundial-org/awesome-openclaw-skills@clawhub` | Awesome OpenClaw skills for ClawHub | `npx skills add sundial-org/awesome-openclaw-skills@clawhub` |

## Notes

- **Agent Services/Jobs/Personas**: No specific skills found for these concepts in the OpenClaw ecosystem. These may be handled internally in OpenClaw/ClawHub rather than as separate skills.
- **Skill Discovery**: Use `npx skills find <query>` to search for more skills
- **Browse all skills**: https://skills.sh/

## Installation

To install a skill globally:

```bash
npx skills add <owner/repo@skill> -g -y
```

Example:

```bash
npx skills add steipete/clawdis@clawhub -g -y
```
