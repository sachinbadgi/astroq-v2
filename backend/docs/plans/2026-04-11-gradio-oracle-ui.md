# Local Gradio Oracle UI Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Create a local Gradio UI that allows the user to chat with an Ollama-hosted `gemma4` model, using a generated Gemini payload JSON as system context.

**Architecture:** A single Python script `tests/lk_prediction/gradio_oracle.py` serving a `gradio.Blocks` and `gradio.ChatInterface`. The chat function loads the user-specified JSON file, aggregates the session history, and streams the output from `litellm` directly to the Gradio chat window.

**Tech Stack:** Python, Gradio, LiteLLM, Ollama

---

### Task 1: Environment Setup

**Files:**
- Modify: `/Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/requirements.txt`

**Step 1: Write the failing test**

Run: `source venv/bin/activate && python -c "import gradio"`
Expected: FAIL with `ModuleNotFoundError: No module named 'gradio'`

**Step 2: Write minimal implementation**

Append `gradio` to `requirements.txt`.
```bash
echo "gradio" >> requirements.txt
source venv/bin/activate && pip install -r requirements.txt
```

**Step 3: Run test to verify it passes**

Run: `source venv/bin/activate && python -c "import gradio; print('Gradio installed')"`
Expected: PASS with "Gradio installed"

**Step 4: Commit**
```bash
git add requirements.txt
git commit -m "chore: add gradio to requirements"
```

---

### Task 2: Implement the Gradio Application

**Files:**
- Create: `/Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/lk_prediction/gradio_oracle.py`

**Step 1: Write the failing test**

Run: `ls /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/lk_prediction/gradio_oracle.py`
Expected: FAIL with "No such file or directory"

**Step 2: Write minimal implementation**

Create `/Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/lk_prediction/gradio_oracle.py`:

```python
import gradio as gr
import litellm
import json
import os

# Disable litellm telemetry and explicit outputs natively
litellm.telemetry = False

def load_payload(filepath):
    if not os.path.exists(filepath):
        return "Error: JSON payload file not found. Ensure the filename is correct."
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        return json.dumps(data)
    except Exception as e:
        return f"Error loading JSON: {str(e)}"

def chat_logic(message, history, payload_path):
    if not payload_path:
        yield "Please provide a valid path to the *_gemini_payload.json file."
        return

    system_context = load_payload(payload_path)
    if system_context.startswith("Error"):
        yield system_context
        return

    messages = [
        {"role": "system", "content": f"You are a Premium Lal Kitab Oracle. Analyze the astrological context deeply. Here is the chart details:\\n{system_context}"}
    ]
    
    for human, ai in history:
        messages.append({"role": "user", "content": human})
        if ai:
            messages.append({"role": "assistant", "content": ai})
            
    messages.append({"role": "user", "content": message})
    
    try:
        # LiteLLM routing natively to ollama running locally on 11434
        response = litellm.completion(
            model="ollama/gemma4",
            messages=messages,
            stream=True
        )
        
        partial_message = ""
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            partial_message += delta
            # Yielding enables "Typewriter/Streaming" effect natively in Gradio
            # making "<think>...</think>" blocks render gracefully in real time.
            yield partial_message

    except Exception as e:
        yield f"LLM Connection Error (Ensure Ollama is running and gemma4 is pulled): {str(e)}"

def build_app():
    with gr.Blocks(title="Local Oracle UI", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔮 Local Lal Kitab Oracle")
        gr.Markdown("Uses Ollama's `gemma4` local reasoning model to process GEMINI-Payload chart insights.")
        
        json_path = gr.Textbox(
            label="Path to JSON Payload", 
            value="sachin_predictions.json", # Default example
            placeholder="e.g., sachin_gemini_payload.json"
        )
        
        # We pass the dynamic filepath from the textbox straight to the logic wrapper
        chat = gr.ChatInterface(
            fn=lambda msg, hist: chat_logic(msg, hist, json_path.value),
            chatbot=gr.Chatbot(height=600, bubble_full_width=False)
        )
    return demo

if __name__ == "__main__":
    demo = build_app()
    demo.launch(server_name="127.0.0.1", server_port=7860, show_api=False)
```

**Step 3: Run test to verify it passes**

Run: `ls /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/lk_prediction/gradio_oracle.py`
Expected: PASS (shows file exists).
Run: `python -m py_compile /Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/lk_prediction/gradio_oracle.py`
Expected: PASS (syntactically valid).

**Step 4: Commit**

```bash
git add tests/lk_prediction/gradio_oracle.py
git commit -m "feat: add gradio testing UI for local ollama gemma4 instance"
```
