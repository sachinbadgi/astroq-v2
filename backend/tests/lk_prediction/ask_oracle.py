"""
Ask the Oracle - Simple CLI
============================
Loads the JSON output from interactive_chart_builder.py and sends it
alongside a user question to gemma4 running locally on Ollama.

Usage:
    python ask_oracle.py
    python ask_oracle.py --file sachin_gemini_payload.json
"""

import os
import sys
import json
import glob
import argparse
import litellm

# Disable litellm telemetry/verbose logging
litellm.telemetry = False

OLLAMA_MODEL = "ollama/gemma4"
SYSTEM_PROMPT_TEMPLATE = """\
You are a Premium Lal Kitab Oracle with deep expertise in Vedic astrology.
You think step by step before answering. Be detailed, insightful, and precise.

Below is the astrological chart data for the client. Use this as the basis for all answers.

--- CHART DATA ---
{chart_json}
--- END CHART DATA ---
"""

def find_json_files():
    """Find *_predictions.json and *_gemini_payload.json in the current directory."""
    files = glob.glob("*_predictions.json") + glob.glob("*_gemini_payload.json")
    return sorted(files)

def pick_file(args_file):
    """Resolve the JSON file to load."""
    if args_file:
        if not os.path.exists(args_file):
            print(f"\n[ERROR] File not found: {args_file}")
            sys.exit(1)
        return args_file

    files = find_json_files()
    if not files:
        print("\n[ERROR] No *_predictions.json or *_gemini_payload.json files found.")
        print("Run interactive_chart_builder.py first to generate a chart.")
        sys.exit(1)

    if len(files) == 1:
        print(f"[INFO] Using: {files[0]}")
        return files[0]

    print("\nMultiple chart files found:")
    for i, f in enumerate(files):
        print(f"  [{i+1}] {f}")
    while True:
        choice = input("\nSelect file number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        print(f"Invalid choice. Enter a number between 1 and {len(files)}.")

def load_json(filepath):
    """Load and return JSON file content as a compact string."""
    with open(filepath, "r") as f:
        data = json.load(f)
    return json.dumps(data, separators=(",", ":"))

def stream_response(messages):
    """Stream the LLM response and print as it arrives."""
    try:
        response = litellm.completion(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=True,
        )
        print("\n" + "=" * 60)
        print("🔮 Oracle Response:")
        print("=" * 60 + "\n")

        full_response = ""
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            print(delta, end="", flush=True)
            full_response += delta

        print("\n\n" + "=" * 60)
        return full_response
    except Exception as e:
        print(f"\n[LLM ERROR] {e}")
        print("Ensure Ollama is running and gemma4 is pulled ('ollama run gemma4')")
        return None

def main():
    parser = argparse.ArgumentParser(description="Ask the Lal Kitab Oracle a question.")
    parser.add_argument("--file", type=str, help="Path to *_predictions.json or *_gemini_payload.json")
    args = parser.parse_args()

    print("=========================================================")
    print("       Lal Kitab Oracle  — Local Ollama gemma4          ")
    print("=========================================================\n")

    # 1. Pick JSON context file
    filepath = pick_file(args.file)
    print(f"[1/3] Loading chart context from: {filepath}")
    chart_json = load_json(filepath)

    # 2. Build system prompt
    system_content = SYSTEM_PROMPT_TEMPLATE.format(chart_json=chart_json)

    # 3. Interactive question loop
    print("[2/3] Connected to Ollama (model: gemma4)")
    print("[3/3] Ready! Type your astrological question below.")
    print("      (Type 'exit' or press Ctrl+C to quit)\n")

    messages = [{"role": "system", "content": system_content}]

    try:
        while True:
            question = input("❓ Your Question: ").strip()
            if not question:
                continue
            if question.lower() in ("exit", "quit", "q"):
                print("\nFarewell! May the stars guide you. 🌟")
                break

            messages.append({"role": "user", "content": question})
            assistant_reply = stream_response(messages)
            if assistant_reply:
                # Keep conversation history for follow-up questions
                messages.append({"role": "assistant", "content": assistant_reply})

    except KeyboardInterrupt:
        print("\n\nFarewell! May the stars guide you. 🌟")

if __name__ == "__main__":
    main()
