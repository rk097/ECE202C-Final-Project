from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import json
import sys

from scanner import scan_firmware

load_dotenv()
client = OpenAI()


def list_files(path: str):
    root = Path(path)
    if not root.exists():
        return {"error": f"Path does not exist: {path}"}

    files = []
    for p in root.rglob("*"):
        if p.is_file():
            files.append(str(p))

    return {"files": files}


def read_file(path: str):
    p = Path(path)

    if not p.exists():
        return {"error": f"File does not exist: {path}"}

    if not p.is_file():
        return {"error": f"Path is not a file: {path}"}

    try:
        text = p.read_text(errors="ignore")
    except Exception as e:
        return {"error": str(e)}

    # Avoid dumping huge files into the model.
    return {
        "path": str(p),
        "content": text[:4000],
        "truncated": len(text) > 4000
    }


def run_scanner(path: str):
    findings = scan_firmware(path)
    return {"findings": findings}


TOOLS = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List files recursively inside a simulated IoT firmware directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the firmware directory."
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a specific file from the simulated firmware directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read."
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "run_scanner",
        "description": "Run the static IoT firmware security scanner on a firmware directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the firmware directory."
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    }
]


TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "run_scanner": run_scanner
}


SYSTEM_PROMPT = """
You are an IoT firmware security analysis agent.

You analyze only simulated firmware folders for a class project.
Do not provide instructions for attacking real devices, public IPs, or live systems.

Your goal is not only to summarize scanner output. You must independently inspect relevant files and compare your own observations against the scanner results.

Required workflow:

1. Call list_files on the target directory.
2. Identify firmware sample directories.
3. Call run_scanner on each firmware sample.
4. Read security-relevant files, including:
   - config files
   - init/startup scripts
   - update scripts
   - key/certificate files
   - files mentioned in scanner findings
5. For each sample, determine:
   - scanner findings
   - additional issues you noticed from file contents
   - scanner false negatives
   - scanner false positives, if any
6. Produce a final markdown security report.
7. Include a section called "Scanner Limitations and Missed Findings".

Do not rely only on scanner output. As one leading example, if a config file contains fields such as password, admin_password, secret, token, key, or credential, evaluate whether it is a hardcoded secret even if the scanner did not flag it.

Do not claim exploitability unless the evidence supports it.
"""


def run_agent(target: str, max_steps: int = 8):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"Analyze this simulated IoT firmware directory: {target}"
        }
    ]

    transcript = []
    transcript.append("# LLM Agent Transcript\n")
    transcript.append(f"Target: `{target}`\n\n")

    final_text = None

    for step in range(max_steps):
        transcript.append(f"## Step {step + 1}\n")

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=messages,
            tools=TOOLS
        )

        # Save raw-ish response text for logs when available.
        tool_calls = []

        for item in response.output:
            if item.type == "function_call":
                tool_calls.append(item)

        if not tool_calls:
            final_text = response.output_text
            transcript.append("### Final Agent Response\n")
            transcript.append(final_text)
            transcript.append("\n")
            break

        for call in tool_calls:
            tool_name = call.name
            args = json.loads(call.arguments)

            transcript.append(f"### Tool Call: `{tool_name}`\n")
            transcript.append("Arguments:\n")
            transcript.append("```json\n")
            transcript.append(json.dumps(args, indent=2))
            transcript.append("\n```\n")

            if tool_name not in TOOL_MAP:
                result = {"error": f"Unknown tool: {tool_name}"}
            else:
                result = TOOL_MAP[tool_name](**args)

            transcript.append("Result:\n")
            transcript.append("```json\n")
            transcript.append(json.dumps(result, indent=2))
            transcript.append("\n```\n")

            messages.append(call)
            messages.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result)
            })

    if final_text is None:
        final_text = "Agent stopped before producing a final report."

    return final_text, "".join(transcript)


def main():
    if len(sys.argv) != 2:
        print("Usage: python run_agent.py <firmware_folder>")
        sys.exit(1)

    target = sys.argv[1]
    sample_name = Path(target).name

    Path("logs").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)

    final_report, transcript = run_agent(target)

    report_path = Path("reports") / f"{sample_name}_llm_report.md"
    log_path = Path("logs") / f"{sample_name}_llm_transcript.md"

    report_path.write_text(final_report)
    log_path.write_text(transcript)

    print("=== LLM IoT Firmware Agent ===")
    print(f"Target: {target}")
    print(f"Wrote report: {report_path}")
    print(f"Wrote transcript: {log_path}")


if __name__ == "__main__":
    main()