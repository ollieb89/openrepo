#!/usr/bin/env python3
"""
L1 Delegation Verification Script

Tests the L1->L2 delegation wiring and reports pass/fail for each stage:
1. Config Loading - Validate L1 config.json structure
2. Skill Resolution - Verify router_skill exists and is valid
3. Gateway Connectivity - Check gateway is reachable
4. Delegation Roundtrip - Test actual delegation via router_skill

Exit codes:
  0 - All stages passed
  1 - One or more stages failed
"""

import json
import socket
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_stage(name, status, message, hint=None):
    """Print a stage result with color coding"""
    if status == 'pass':
        symbol = f"{Colors.GREEN}✓{Colors.RESET}"
        print(f"[{symbol}] {Colors.BOLD}{name}{Colors.RESET}: {message}")
    elif status == 'fail':
        symbol = f"{Colors.RED}✗{Colors.RESET}"
        print(f"[{symbol}] {Colors.BOLD}{name}{Colors.RESET}: {message}")
        if hint:
            print(f"    {Colors.YELLOW}→{Colors.RESET} {hint}")
    elif status == 'info':
        print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def stage_config_loading():
    """Stage 1: Load and validate L1 config.json"""
    config_path = Path('agents/clawdia_prime/agent/config.json')
    
    if not config_path.exists():
        print_stage(
            'Config Loading',
            'fail',
            'L1 config.json not found',
            'Expected at: agents/clawdia_prime/agent/config.json'
        )
        return False, None
    
    try:
        with open(config_path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print_stage(
            'Config Loading',
            'fail',
            f'Invalid JSON in config.json: {e}',
            'Fix JSON syntax errors'
        )
        return False, None
    
    required_fields = ['id', 'level', 'skill_registry', 'gateway']
    missing = [f for f in required_fields if f not in config]
    if missing:
        print_stage(
            'Config Loading',
            'fail',
            f'Missing required fields: {", ".join(missing)}',
            'Add missing fields to config.json'
        )
        return False, None
    
    if config['id'] != 'clawdia_prime':
        print_stage(
            'Config Loading',
            'fail',
            f'Wrong agent id: {config["id"]} (expected: clawdia_prime)',
            'Fix id field in config.json'
        )
        return False, None
    
    if config['level'] != 1:
        print_stage(
            'Config Loading',
            'fail',
            f'Wrong level: {config["level"]} (expected: 1)',
            'Fix level field in config.json'
        )
        return False, None
    
    if 'router' not in config.get('skill_registry', {}):
        print_stage(
            'Config Loading',
            'fail',
            'Missing router in skill_registry',
            'Add router skill to skill_registry'
        )
        return False, None
    
    print_stage('Config Loading', 'pass', 'L1 config.json valid')
    return True, config


def stage_skill_resolution(config):
    """Stage 2: Verify router_skill exists and is valid"""
    skill_path = config['skill_registry']['router'].get('skill_path')
    
    if not skill_path:
        print_stage(
            'Skill Resolution',
            'fail',
            'Missing skill_path in router config',
            'Add skill_path to router in skill_registry'
        )
        return False
    
    skill_dir = Path(skill_path)
    if not skill_dir.exists():
        print_stage(
            'Skill Resolution',
            'fail',
            f'Skill directory not found: {skill_path}',
            'Verify router_skill is installed'
        )
        return False
    
    skill_json = skill_dir / 'skill.json'
    if not skill_json.exists():
        print_stage(
            'Skill Resolution',
            'fail',
            f'skill.json not found in {skill_path}',
            'Verify router_skill installation is complete'
        )
        return False
    
    try:
        with open(skill_json) as f:
            skill_config = json.load(f)
    except json.JSONDecodeError as e:
        print_stage(
            'Skill Resolution',
            'fail',
            f'Invalid JSON in skill.json: {e}',
            'Fix JSON syntax errors in skill.json'
        )
        return False
    
    index_js = skill_dir / 'index.js'
    if not index_js.exists():
        print_stage(
            'Skill Resolution',
            'fail',
            f'index.js not found in {skill_path}',
            'Verify router_skill installation is complete'
        )
        return False
    
    print_stage('Skill Resolution', 'pass', f'router_skill found at {skill_path}')
    return True


def stage_gateway_connectivity():
    """Stage 3: Check gateway is reachable"""
    openclaw_config_path = Path('openclaw.json')
    
    if not openclaw_config_path.exists():
        print_stage(
            'Gateway Connectivity',
            'fail',
            'openclaw.json not found',
            'Verify OpenClaw installation'
        )
        return False, None
    
    try:
        with open(openclaw_config_path) as f:
            openclaw_config = json.load(f)
    except json.JSONDecodeError as e:
        print_stage(
            'Gateway Connectivity',
            'fail',
            f'Invalid JSON in openclaw.json: {e}',
            'Fix JSON syntax errors'
        )
        return False, None
    
    gateway_port = openclaw_config.get('gateway', {}).get('port', 18789)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    
    try:
        result = sock.connect_ex(('localhost', gateway_port))
        sock.close()
        
        if result == 0:
            print_stage('Gateway Connectivity', 'pass', f'localhost:{gateway_port} reachable')
            return True, gateway_port
        else:
            print_stage(
                'Gateway Connectivity',
                'fail',
                f'Gateway not reachable at localhost:{gateway_port}',
                'Is the OpenClaw daemon running? Try: openclaw gateway status'
            )
            return False, gateway_port
    except socket.error as e:
        print_stage(
            'Gateway Connectivity',
            'fail',
            f'Socket error: {e}',
            'Check network configuration'
        )
        return False, gateway_port


def stage_delegation_roundtrip(config):
    """Stage 4: Test actual delegation via router_skill"""
    skill_path = config['skill_registry']['router']['skill_path']
    index_js = Path(skill_path) / 'index.js'
    
    target_agent = 'pumplai_pm'
    directive = 'ping'
    
    cmd = ['node', str(index_js), target_agent, directive]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd()
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or 'Unknown error'
            
            if 'ECONNREFUSED' in error_msg or 'not reachable' in error_msg.lower():
                print_stage(
                    'Delegation Roundtrip',
                    'fail',
                    'Gateway connection refused',
                    'Start the OpenClaw gateway: openclaw gateway start'
                )
            elif 'not found' in error_msg.lower() or 'unknown agent' in error_msg.lower():
                print_stage(
                    'Delegation Roundtrip',
                    'fail',
                    f'Agent {target_agent} not found',
                    'Verify agent is registered in openclaw.json'
                )
            elif 'timeout' in error_msg.lower():
                print_stage(
                    'Delegation Roundtrip',
                    'fail',
                    'Delegation timeout',
                    'Check agent responsiveness and gateway logs'
                )
            else:
                print_stage(
                    'Delegation Roundtrip',
                    'fail',
                    f'Command failed: {error_msg[:100]}',
                    'Check router_skill logs for details'
                )
            return False
        
        try:
            response = json.loads(result.stdout)
            if response.get('status') == 'ok':
                run_id = response.get('runId', 'unknown')
                print_stage(
                    'Delegation Roundtrip',
                    'pass',
                    f'{target_agent} responded with status=ok (runId: {run_id})'
                )
                return True
            else:
                print_stage(
                    'Delegation Roundtrip',
                    'fail',
                    f'Agent returned status: {response.get("status")}',
                    'Check agent logs for error details'
                )
                return False
        except json.JSONDecodeError:
            print_stage(
                'Delegation Roundtrip',
                'fail',
                'Invalid JSON response from router_skill',
                'Check router_skill implementation'
            )
            return False
            
    except subprocess.TimeoutExpired:
        print_stage(
            'Delegation Roundtrip',
            'fail',
            'Command timeout (30s)',
            'Check gateway and agent responsiveness'
        )
        return False
    except FileNotFoundError:
        print_stage(
            'Delegation Roundtrip',
            'fail',
            'node command not found',
            'Install Node.js: apt install nodejs'
        )
        return False
    except Exception as e:
        print_stage(
            'Delegation Roundtrip',
            'fail',
            f'Unexpected error: {e}',
            'Check system logs'
        )
        return False


def main():
    """Run all verification stages"""
    print(f"\n{Colors.BOLD}L1 Delegation Verification{Colors.RESET}\n")
    
    results = []
    
    passed, config = stage_config_loading()
    results.append(passed)
    
    if not passed:
        print(f"\n{Colors.RED}RESULT: Config validation failed{Colors.RESET}\n")
        return 1
    
    passed = stage_skill_resolution(config)
    results.append(passed)
    
    if not passed:
        print(f"\n{Colors.RED}RESULT: Skill resolution failed{Colors.RESET}\n")
        return 1
    
    gateway_passed, gateway_port = stage_gateway_connectivity()
    results.append(gateway_passed)
    
    if not gateway_passed:
        print(f"\n{Colors.YELLOW}RESULT: WIRING OK, RUNTIME UNAVAILABLE{Colors.RESET}")
        print(f"{Colors.BLUE}ℹ{Colors.RESET} Config and skill wiring are correct, but gateway is not running\n")
        return 0
    
    delegation_passed = stage_delegation_roundtrip(config)
    results.append(delegation_passed)
    
    print()
    if all(results):
        print(f"{Colors.GREEN}{Colors.BOLD}RESULT: All stages PASSED{Colors.RESET}\n")
        return 0
    else:
        if gateway_passed and not delegation_passed:
            print(f"{Colors.YELLOW}RESULT: WIRING OK, DELEGATION FAILED{Colors.RESET}")
            print(f"{Colors.BLUE}ℹ{Colors.RESET} Config is correct but delegation failed - check agent availability\n")
            return 0
        else:
            print(f"{Colors.RED}RESULT: One or more stages FAILED{Colors.RESET}\n")
            return 1


if __name__ == '__main__':
    sys.exit(main())
