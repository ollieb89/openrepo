#!/usr/bin/env python3
"""
Phase 4 Verification Script

Validates DSH-01, DSH-02, DSH-03, DSH-04, SEC-02 through live testing.
Starts dashboard dev server, probes endpoints, documents gaps.

Exit codes:
  0 - Verification complete (gaps documented, not failures)
  1 - Script crash or server timeout
"""

import json
import subprocess
import sys
import time
import socket
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
    print("-" * len(title))


def print_check(status: str, message: str) -> None:
    """Print a structured check line with status prefix."""
    color = {
        "PASS": Colors.GREEN,
        "FAIL": Colors.RED,
        "GAP": Colors.YELLOW,
        "WARN": Colors.YELLOW,
        "INFO": Colors.BLUE,
    }.get(status, Colors.RESET)
    print(f"{color}[{status}]{Colors.RESET} {message}")


def find_project_root() -> Path:
    """Find project root by walking up until openclaw.json is found."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "openclaw.json").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError("Could not find openclaw.json in parent directories.")


def http_get(url: str, timeout: float = 5.0) -> Tuple[int, Optional[str]]:
    """Make HTTP GET request, return (status_code, body)."""
    try:
        try:
            import requests
            resp = requests.get(url, timeout=timeout)
            return resp.status_code, resp.text
        except ImportError:
            pass
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace') if e.read() else None
    except Exception as e:
        return 0, str(e)


def http_get_sse(url: str, timeout: float = 5.0) -> Tuple[int, Optional[str], List[str]]:
    """Make SSE request, return (status_code, content_type, lines_read)."""
    try:
        try:
            import requests
            headers = {"Accept": "text/event-stream"}
            resp = requests.get(url, headers=headers, stream=True, timeout=timeout)
            lines = []
            for line in resp.iter_lines():
                if line:
                    lines.append(line.decode('utf-8', errors='replace'))
                if len(lines) >= 3:
                    break
            return resp.status_code, resp.headers.get('Content-Type', ''), lines
        except ImportError:
            pass
        req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            lines = []
            for _ in range(3):
                try:
                    line = resp.readline().decode('utf-8', errors='replace')
                    if line:
                        lines.append(line.strip())
                except:
                    break
            return resp.status, resp.headers.get('Content-Type', ''), lines
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', '') if hasattr(e, 'headers') else '', []
    except Exception as e:
        return 0, '', []


class DashboardServer:
    """Manages Next.js dashboard dev server lifecycle."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.process: Optional[subprocess.Popen] = None
        self.dashboard_dir = project_root / "workspace" / "occc"

    def start(self, max_wait: float = 30.0) -> bool:
        """Start dev server and wait for readiness."""
        if not self.dashboard_dir.exists():
            print_check("FAIL", f"Dashboard directory not found: {self.dashboard_dir}")
            return False

        # Check if already running
        if self._is_port_open(6987):
            print_check("WARN", "Port 6987 already in use, attempting to kill")
            self._kill_port_6987()
            time.sleep(1)

        # Start server
        print_check("INFO", "Starting dashboard dev server (npm run dev)...")
        try:
            self.process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=str(self.dashboard_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError:
            # Try bun
            self.process = subprocess.Popen(
                ["bun", "run", "dev"],
                cwd=str(self.dashboard_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        # Poll for readiness
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status, _ = http_get("http://localhost:6987/api/swarm", timeout=2.0)
            if status in (200, 404, 500):  # Any response means server is up
                print_check("PASS", f"Dashboard server ready on port 6987 (status: {status})")
                return True
            time.sleep(0.5)

        print_check("FAIL", f"Server failed to start within {max_wait}s")
        return False

    def stop(self) -> None:
        """Stop server and cleanup."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self._kill_port_6987()

    def _is_port_open(self, port: int) -> bool:
        """Check if a port is accepting connections."""
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except:
            return False

    def _kill_port_6987(self) -> None:
        """Force kill any process on port 6987."""
        try:
            subprocess.run(
                ["sh", "-c", "lsof -ti:6987 | xargs kill -9 2>/dev/null || true"],
                capture_output=True, timeout=5
            )
        except:
            pass


def verify_dsh01(project_root: Path, server_up: bool) -> Tuple[bool, Dict[str, Any]]:
    """DSH-01: Dashboard Deployment — Static + runtime checks."""
    print_section("DSH-01: Dashboard Deployment")

    results = {
        "passed": True,
        "next_version_ok": False,
        "tailwind_version_ok": False,
        "typescript_ok": False,
        "files_exist_ok": False,
        "http_root_ok": False,
        "http_api_ok": False,
        "api_status": None,
        "api_response": None,
    }

    dashboard_dir = project_root / "workspace" / "occc"

    # Static: Check package.json
    pkg_path = dashboard_dir / "package.json"
    if pkg_path.exists():
        pkg = json.loads(pkg_path.read_text())
        next_ver = pkg.get("dependencies", {}).get("next", "")
        tailwind_ver = pkg.get("devDependencies", {}).get("tailwindcss", "")

        if "16." in next_ver:
            results["next_version_ok"] = True
            print_check("PASS", f"Next.js version: {next_ver}")
        else:
            print_check("FAIL", f"Next.js version mismatch: {next_ver}")
            results["passed"] = False

        if tailwind_ver.startswith("4") or tailwind_ver.startswith("^4"):
            results["tailwind_version_ok"] = True
            print_check("PASS", f"Tailwind version: {tailwind_ver}")
        else:
            print_check("FAIL", f"Tailwind version mismatch: {tailwind_ver}")
            results["passed"] = False
    else:
        print_check("FAIL", "package.json not found")
        results["passed"] = False

    # Static: TypeScript compile
    try:
        tsc_result = subprocess.run(
            ["node_modules/.bin/tsc", "--noEmit"],
            cwd=str(dashboard_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if tsc_result.returncode == 0:
            results["typescript_ok"] = True
            print_check("PASS", "TypeScript compiles without errors")
        else:
            print_check("FAIL", "TypeScript compilation errors")
            print_check("INFO", tsc_result.stderr[:200])
            results["passed"] = False
    except Exception as e:
        print_check("FAIL", f"TypeScript check failed: {e}")
        results["passed"] = False

    # Static: Required files exist
    required_files = [
        "src/app/page.tsx",
        "src/components/AgentHierarchy.tsx",
        "src/components/AgentDetail.tsx",
        "src/components/LogStream.tsx",
        "src/components/GlobalMetrics.tsx",
    ]
    all_exist = True
    for f in required_files:
        if not (dashboard_dir / f).exists():
            print_check("FAIL", f"Missing required file: {f}")
            all_exist = False
    if all_exist:
        results["files_exist_ok"] = True
        print_check("PASS", "All required dashboard files exist")
    else:
        results["passed"] = False

    # Runtime: HTTP checks (only if server up)
    if server_up:
        status, body = http_get("http://localhost:6987/")
        if status == 200 and body and "html" in body.lower():
            results["http_root_ok"] = True
            print_check("PASS", "Dashboard root responds HTTP 200 with HTML")
        else:
            print_check("FAIL", f"Dashboard root failed: status={status}")
            results["passed"] = False

        status, body = http_get("http://localhost:6987/api/swarm")
        results["api_status"] = status
        results["api_response"] = body[:500] if body else None
        if status == 200:
            results["http_api_ok"] = True
            print_check("PASS", "/api/swarm responds HTTP 200")
        elif status == 500:
            print_check("GAP", f"/api/swarm returns 500 (Zod schema mismatch) — documented as Critical gap")
        else:
            print_check("FAIL", f"/api/swarm unexpected status: {status}")
            results["passed"] = False
    else:
        print_check("WARN", "Server not running — skipping runtime checks")

    return results["passed"], results


def verify_dsh02(project_root: Path, server_up: bool, dsh01_results: Dict) -> Tuple[bool, Dict[str, Any]]:
    """DSH-02: Real-Time Monitoring — /api/swarm and SSE checks."""
    print_section("DSH-02: Real-Time Monitoring")

    results = {
        "passed": True,
        "swarm_data_ok": False,
        "agents_key_exists": False,
        "state_key_exists": False,
        "sse_ok": False,
        "refresh_interval_found": False,
        "gap_zod_mismatch": False,
    }

    dashboard_dir = project_root / "workspace" / "occc"

    # Check /api/swarm response from DSH-01
    api_status = dsh01_results.get("api_status")
    api_response = dsh01_results.get("api_response")

    if api_status == 200 and api_response:
        try:
            data = json.loads(api_response)
            results["swarm_data_ok"] = True
            if "agents" in data:
                results["agents_key_exists"] = True
                print_check("PASS", "/api/swarm contains 'agents' key")
            else:
                print_check("FAIL", "/api/swarm missing 'agents' key")
                results["passed"] = False
            if "state" in data:
                results["state_key_exists"] = True
                print_check("PASS", "/api/swarm contains 'state' key")
            else:
                print_check("FAIL", "/api/swarm missing 'state' key")
                results["passed"] = False
        except json.JSONDecodeError:
            print_check("FAIL", "/api/swarm returned non-JSON response")
            results["passed"] = False
    elif api_status == 500:
        results["gap_zod_mismatch"] = True
        print_check("GAP", "CRITICAL: Zod schema mismatch prevents state.json parsing")
        print_check("GAP", "  version field is integer (actual) vs string (expected)")
        print_check("GAP", "  protocol field missing, metadata.created_at missing")
        results["passed"] = False
    else:
        print_check("FAIL", f"Cannot check /api/swarm: status={api_status}")
        results["passed"] = False

    # Check SSE endpoint
    if server_up:
        status, content_type, lines = http_get_sse("http://localhost:6987/api/swarm/stream", timeout=5.0)
        if content_type and "text/event-stream" in content_type:
            results["sse_ok"] = True
            print_check("PASS", "/api/swarm/stream returns SSE content-type")
        else:
            print_check("FAIL", f"/api/swarm/stream SSE check failed (content-type: {content_type})")
            results["passed"] = False
    else:
        print_check("WARN", "Server not running — skipping SSE check")

    # Code inspection: grep for refreshInterval in useSwarmState.ts
    hooks_path = dashboard_dir / "src" / "hooks" / "useSwarmState.ts"
    if hooks_path.exists():
        content = hooks_path.read_text()
        if "refreshInterval" in content:
            results["refresh_interval_found"] = True
            print_check("INFO", "refreshInterval found in useSwarmState.ts")
        else:
            print_check("WARN", "refreshInterval not found in useSwarmState.ts")
    else:
        print_check("WARN", "useSwarmState.ts not found")

    return results["passed"], results


def verify_dsh03(project_root: Path, server_up: bool) -> Tuple[bool, Dict[str, Any]]:
    """DSH-03: Live Log Feeds — /api/logs/[agent] endpoint."""
    print_section("DSH-03: Live Log Feeds")

    results = {
        "passed": True,
        "logs_endpoint_ok": False,
        "redaction_wired": False,
    }

    dashboard_dir = project_root / "workspace" / "occc"

    # Test /api/logs endpoint
    if server_up:
        status, body = http_get("http://localhost:6987/api/logs/pumplai_pm", timeout=5.0)
        if status == 200:
            results["logs_endpoint_ok"] = True
            print_check("PASS", "/api/logs/pumplai_pm returns 200 (container running)")
        elif status == 404:
            results["logs_endpoint_ok"] = True
            print_check("PASS", "/api/logs/pumplai_pm returns 404 (graceful — container not found)")
        elif status == 500:
            print_check("GAP", "/api/logs returns 500 (docker socket or implementation error)")
            results["passed"] = False
        else:
            print_check("INFO", f"/api/logs returned status {status}")
    else:
        print_check("WARN", "Server not running — skipping logs endpoint check")

    # Code inspection: check redaction wired in docker.ts
    docker_path = dashboard_dir / "src" / "lib" / "docker.ts"
    if docker_path.exists():
        content = docker_path.read_text()
        if "redactSensitiveData" in content:
            results["redaction_wired"] = True
            print_check("PASS", "redactSensitiveData wired in docker.ts")
        else:
            print_check("FAIL", "redactSensitiveData NOT found in docker.ts")
            results["passed"] = False
    else:
        print_check("FAIL", "docker.ts not found")
        results["passed"] = False

    return results["passed"], results


def verify_dsh04(project_root: Path, server_up: bool, dsh01_results: Dict) -> Tuple[bool, Dict[str, Any]]:
    """DSH-04: Global Metrics Visualization — metrics object check."""
    print_section("DSH-04: Global Metrics Visualization")

    results = {
        "passed": True,
        "metrics_ok": False,
        "all_fields_present": False,
        "component_exists": False,
        "missing_fields": [],
        "gap_zod_mismatch": False,
    }

    dashboard_dir = project_root / "workspace" / "occc"
    required_fields = [
        "totalByTier", "active", "idle", "errored",
        "totalTasks", "completedTasks", "failedTasks"
    ]

    # Check metrics from /api/swarm
    api_status = dsh01_results.get("api_status")
    api_response = dsh01_results.get("api_response")

    if api_status == 200 and api_response:
        try:
            data = json.loads(api_response)
            metrics = data.get("metrics", {})
            results["metrics_ok"] = True

            missing = [f for f in required_fields if f not in metrics]
            results["missing_fields"] = missing

            if not missing:
                results["all_fields_present"] = True
                print_check("PASS", f"All 7 required metrics fields present")
            else:
                print_check("FAIL", f"Missing metrics fields: {missing}")
                results["passed"] = False
        except json.JSONDecodeError:
            print_check("FAIL", "Could not parse /api/swarm response for metrics")
            results["passed"] = False
    elif api_status == 500:
        results["gap_zod_mismatch"] = True
        print_check("GAP", "CRITICAL: Zod schema mismatch — metrics unavailable from /api/swarm")
        results["passed"] = False
    else:
        print_check("FAIL", f"Cannot check metrics: /api/swarm status={api_status}")
        results["passed"] = False

    # Check GlobalMetrics.tsx exists
    component_path = dashboard_dir / "src" / "components" / "GlobalMetrics.tsx"
    if component_path.exists():
        results["component_exists"] = True
        print_check("PASS", "GlobalMetrics.tsx exists")
        content = component_path.read_text()
        if "metrics" in content.lower():
            print_check("PASS", "GlobalMetrics.tsx contains metric rendering logic")
        else:
            print_check("WARN", "GlobalMetrics.tsx may lack metric rendering logic")
    else:
        print_check("FAIL", "GlobalMetrics.tsx not found")
        results["passed"] = False

    return results["passed"], results


def verify_sec02(project_root: Path) -> Tuple[bool, Dict[str, Any]]:
    """SEC-02: Redaction Logic — run test_redaction.cjs."""
    print_section("SEC-02: Redaction Logic")

    results = {
        "passed": True,
        "test_script_ran": False,
        "implemented_patterns_ok": False,
        "missing_categories_documented": False,
        "docker_redaction_wired": False,
        "implemented_passed": 0,
        "implemented_total": 0,
        "missing_total": 0,
    }

    dashboard_dir = project_root / "workspace" / "occc"
    script_path = project_root / "scripts" / "test_redaction.cjs"

    # Run test_redaction.cjs
    try:
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        results["test_script_ran"] = True
        results["implemented_passed"] = data.get("summary", {}).get("passed", 0)
        results["implemented_total"] = data.get("summary", {}).get("total", 0)

        # Check implemented patterns
        implemented = data.get("implemented", [])
        all_implemented_pass = all(item.get("redacted") for item in implemented)
        if all_implemented_pass:
            results["implemented_patterns_ok"] = True
            print_check("PASS", f"All {len(implemented)} implemented redaction patterns work")
        else:
            failed = [i.get("name") for i in implemented if not i.get("redacted")]
            print_check("FAIL", f"Redaction patterns failed: {failed}")
            results["passed"] = False

        # Document missing categories as gaps
        missing = data.get("missing", [])
        results["missing_total"] = len(missing)
        if missing:
            missing_names = [m.get("name") for m in missing]
            print_check("GAP", f"MAJOR: Missing redaction categories: {missing_names}")
            print_check("GAP", "  CONTEXT.md requires redaction of host filesystem paths, IP addresses, container IDs")
            results["missing_categories_documented"] = True

    except subprocess.TimeoutExpired:
        print_check("FAIL", "test_redaction.cjs timed out")
        results["passed"] = False
    except json.JSONDecodeError as e:
        print_check("FAIL", f"Failed to parse test_redaction.cjs output: {e}")
        results["passed"] = False
    except Exception as e:
        print_check("FAIL", f"test_redaction.cjs error: {e}")
        results["passed"] = False

    # Code inspection: check docker.ts uses redactSensitiveData
    docker_path = dashboard_dir / "src" / "lib" / "docker.ts"
    if docker_path.exists():
        content = docker_path.read_text()
        if "redactSensitiveData" in content:
            results["docker_redaction_wired"] = True
            print_check("PASS", "redactSensitiveData called server-side in docker.ts")
        else:
            print_check("FAIL", "redactSensitiveData NOT called in docker.ts")
            results["passed"] = False
    else:
        print_check("FAIL", "docker.ts not found for SEC-02 inspection")
        results["passed"] = False

    return results["passed"], results


def print_summary(
    dsh01_pass: bool, dsh02_pass: bool, dsh03_pass: bool,
    dsh04_pass: bool, sec02_pass: bool
) -> None:
    """Print final verification summary."""
    print_section("Phase 4 Verification Summary")

    print(f"\n{Colors.BOLD}Requirements Coverage:{Colors.RESET}")
    print("")

    print_check("PASS" if dsh01_pass else "FAIL", "DSH-01: Dashboard Deployment (Next.js 16 + Tailwind 4)")
    print_check("PASS" if dsh02_pass else "FAIL", "DSH-02: Real-Time Monitoring (/api/swarm + SSE)")
    print_check("PASS" if dsh03_pass else "FAIL", "DSH-03: Live Log Feeds (/api/logs)")
    print_check("PASS" if dsh04_pass else "FAIL", "DSH-04: Global Metrics Visualization")
    print_check("PASS" if sec02_pass else "FAIL", "SEC-02: Redaction Logic")

    print("")
    print("=" * 60)

    all_passed = dsh01_pass and dsh02_pass and dsh03_pass and dsh04_pass and sec02_pass

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}PHASE 4 VERIFICATION COMPLETE{Colors.RESET}")
        print("=" * 60)
        print("")
        print("All five Phase 4 requirements verified successfully.")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}PHASE 4 VERIFICATION COMPLETE (WITH GAPS){Colors.RESET}")
        print("=" * 60)
        print("")
        print("Verification completed with documented gaps (see GAP entries above).")
        print("Gaps are expected per CONTEXT.md — this phase documents, does not fix.")

    print("")
    print("Exit code: 0")


def main() -> int:
    """Run end-to-end Phase 4 verification."""
    print(f"\n{Colors.BOLD}Phase 4 Verification{Colors.RESET}")
    print("Validates DSH-01, DSH-02, DSH-03, DSH-04, SEC-02")

    try:
        project_root = find_project_root()
    except FileNotFoundError as exc:
        print_check("FAIL", str(exc))
        return 1

    print_check("INFO", f"Project root: {project_root}")

    # Start dashboard server
    server = DashboardServer(project_root)
    server_up = server.start(max_wait=30.0)

    evidence = []
    exit_code = 0

    try:
        # Run all verification sections
        dsh01_pass, dsh01_results = verify_dsh01(project_root, server_up)
        dsh02_pass, dsh02_results = verify_dsh02(project_root, server_up, dsh01_results)
        dsh03_pass, dsh03_results = verify_dsh03(project_root, server_up)
        dsh04_pass, dsh04_results = verify_dsh04(project_root, server_up, dsh01_results)
        sec02_pass, sec02_results = verify_sec02(project_root)

        # Collect evidence
        evidence.append({"section": "DSH-01", "passed": dsh01_pass, "results": dsh01_results})
        evidence.append({"section": "DSH-02", "passed": dsh02_pass, "results": dsh02_results})
        evidence.append({"section": "DSH-03", "passed": dsh03_pass, "results": dsh03_results})
        evidence.append({"section": "DSH-04", "passed": dsh04_pass, "results": dsh04_results})
        evidence.append({"section": "SEC-02", "passed": sec02_pass, "results": sec02_results})

        # Write evidence JSON
        evidence_path = Path("/tmp/phase4_verification_evidence.json")
        evidence_path.write_text(json.dumps(evidence, indent=2, default=str))
        print_check("INFO", f"Evidence written to: {evidence_path}")

        # Print summary
        print_summary(dsh01_pass, dsh02_pass, dsh03_pass, dsh04_pass, sec02_pass)

    except Exception as e:
        print_check("FAIL", f"Verification crashed: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    finally:
        server.stop()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
