"""
agent_orchestrator.py
---------------------
Agentic workflow coordinator for Power BI Report Server dashboards.

Takes natural language prompts and orchestrates:
1. Data model work (pbi-cli): tables, measures, DAX, RLS
2. Report building (vizbuilder): pages, visuals, layouts

Usage:
    python agent_orchestrator.py "your_file.pbix"

Then type prompts at the >> prompt:
    >> Connect and inspect the model
    >> Add a revenue measure with DAX
    >> Build a dashboard with KPIs and charts
    >> Add row-level security by region
"""

import os
import sys
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

# Try to import Claude API (optional - falls back to template mode)
try:
    from anthropic import Anthropic
    HAS_CLAUDE_API = True
except ImportError:
    HAS_CLAUDE_API = False
    print("Note: Claude API not available. Running in template-guided mode.")


class PBIAgent:
    def __init__(self, pbix_file):
        self.pbix_file = os.path.abspath(pbix_file)
        self.pbix_name = Path(pbix_file).stem
        self.work_dir = os.getcwd()
        self.config_file = os.path.join(self.work_dir, f"{self.pbix_name}_config.py")
        self.client = Anthropic() if HAS_CLAUDE_API else None
        self.conversation_history = []

        if not os.path.isfile(self.pbix_file):
            raise FileNotFoundError(f"PBIX file not found: {self.pbix_file}")

        print(f"\n✓ Connected to: {self.pbix_file}")
        print(f"✓ pbi-cli available: {self._check_pbi_cli()}")
        print(f"✓ API mode: {'Claude API' if HAS_CLAUDE_API else 'Template-guided'}")
        print("\nPrompt examples:")
        print('  "Inspect tables and columns in this model"')
        print('  "Add a Revenue measure as Sum(Orders[Sales])"')
        print('  "Build a dashboard with Total Sales KPI and sales by region chart"')
        print('  "Add row-level security: filter by Region field"\n')

    def _check_pbi_cli(self):
        try:
            result = subprocess.run(["pbi-cli", "--version"],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    def run_pbi_cli(self, command):
        """Execute a pbi-cli command."""
        try:
            # pbi-cli expects a running Power BI Desktop session
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def run_build(self):
        """Execute vizbuilder build."""
        if not os.path.isfile(self.config_file):
            return "", "No config file found. Use a prompt like 'build dashboard...'", 1

        output_file = os.path.join(self.work_dir, f"{self.pbix_name}_out.pbix")
        cmd = f"build.bat \"{self.pbix_file}\" \"{output_file}\" --config \"{self.config_file}\""

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return f"✓ Built: {output_file}\n", result.stderr, 0
            else:
                return "", result.stderr, 1
        except Exception as e:
            return "", str(e), 1

    def interpret_prompt(self, prompt):
        """Use Claude to interpret the prompt and route to appropriate tool."""
        if not HAS_CLAUDE_API:
            return self._template_interpret(prompt)

        system_prompt = """You are an expert Power BI and vizbuilder agent.
Analyze user prompts and decide what to do:

1. MODEL WORK (pbi-cli):
   - "inspect", "show tables", "add measure", "add dax", "row level security", "rls"
   - Response: {'action': 'model', 'pbi_cli_command': '...', 'description': '...'}

2. REPORT WORK (vizbuilder):
   - "build dashboard", "add chart", "add kpi", "layout", "pages", "visuals"
   - Response: {'action': 'report', 'python_code': '...', 'description': '...'}

3. ANALYSIS:
   - "analyze", "show lineage", "find unused", "validate"
   - Response: {'action': 'analyze', 'command': '...', 'description': '...'}

Always respond with valid JSON only, no extra text."""

        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })

        response = self.client.messages.create(
            model="claude-opus-5-5",
            max_tokens=1000,
            system=system_prompt,
            messages=self.conversation_history
        )

        assistant_message = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        try:
            return json.loads(assistant_message)
        except:
            return {"action": "unknown", "error": assistant_message}

    def _template_interpret(self, prompt):
        """Fallback template-based interpretation when API unavailable."""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["inspect", "tables", "columns", "model", "schema"]):
            return {
                "action": "model",
                "pbi_cli_command": "pbi-cli dataset show-table",
                "description": "Inspecting model tables and columns..."
            }
        elif any(word in prompt_lower for word in ["measure", "dax", "add"]):
            return {
                "action": "model",
                "pbi_cli_command": "pbi-cli dataset show-measure",
                "description": "Creating/updating measure..."
            }
        elif any(word in prompt_lower for word in ["rls", "security", "row level"]):
            return {
                "action": "model",
                "pbi_cli_command": "pbi-cli dataset show-rls",
                "description": "Setting up row-level security..."
            }
        elif any(word in prompt_lower for word in ["dashboard", "chart", "build", "visual", "kpi"]):
            return {
                "action": "report",
                "description": "Building dashboard with vizbuilder...",
                "needs_config": True
            }
        else:
            return {"action": "unknown", "description": "Could not understand prompt."}

    def execute_action(self, action_result):
        """Execute the interpreted action."""
        action = action_result.get("action")

        if action == "model":
            print(f"\n📊 {action_result.get('description', 'Model work...')}")
            cmd = action_result.get("pbi_cli_command", "")
            if cmd:
                print(f"   Running: {cmd}")
                stdout, stderr, code = self.run_pbi_cli(cmd)
                if code == 0:
                    print(f"   ✓ Success:\n{stdout}")
                else:
                    print(f"   ✗ Note: Power BI Desktop may need to be running for pbi-cli")
                    print(f"      Error: {stderr[:200]}")

        elif action == "report":
            print(f"\n📈 {action_result.get('description', 'Building report...')}")

            # Generate a basic config if needed
            if action_result.get("needs_config") or not os.path.isfile(self.config_file):
                self._generate_default_config()

            stdout, stderr, code = self.run_build()
            if code == 0:
                print(f"   ✓ {stdout}")
            else:
                print(f"   ✗ Build failed: {stderr[:300]}")

        elif action == "analyze":
            print(f"\n🔍 {action_result.get('description', 'Analyzing...')}")
            cmd = action_result.get("command", "")
            if cmd:
                os.system(cmd)

        else:
            print(f"   {action_result.get('description', 'Unknown action')}")
            if "error" in action_result:
                print(f"   Error: {action_result['error'][:200]}")

    def _generate_default_config(self):
        """Generate a basic dashboard config."""
        config_code = '''"""Auto-generated dashboard config."""
from layout_builder import add_visual

def build_pages():
    page1 = [
        add_visual("card", {"value": "Sum(Orders[Sales])"},
                   x=20, y=60, w=200, h=100, vid=1, title="Total Sales"),
        add_visual("clustered_column", {"category": "Orders[Region]", "value": "Sum(Orders[Sales])"},
                   x=240, y=60, w=500, h=300, vid=2, title="Sales by Region"),
    ]
    return [{"name": "Dashboard", "title": "Dashboard", "visuals": page1}]
'''
        with open(self.config_file, "w") as f:
            f.write(config_code)
        print(f"   Generated: {self.config_file}")

    def interactive_loop(self):
        """Interactive conversation loop."""
        print("\n" + "="*60)
        print("Power BI Agentic Orchestrator - Type 'exit' to quit")
        print("="*60)

        while True:
            try:
                prompt = input("\n>> ").strip()
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                break

            if prompt.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            if not prompt:
                continue

            # Interpret prompt
            action_result = self.interpret_prompt(prompt)

            # Execute action
            self.execute_action(action_result)


def main(argv=None):
    if not argv:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: python agent_orchestrator.py <file.pbix>")
        return 1

    pbix_file = argv[0]

    try:
        agent = PBIAgent(pbix_file)
        agent.interactive_loop()
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
