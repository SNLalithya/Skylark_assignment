"""
patch_agent_groq.py
-------------------
Replaces ChatOpenAI → ChatGroq in agent.py
Also ensures GROQ_API_KEY is read from .env

Usage (from inside the project folder):
    py -3.12 patch_agent_groq.py
"""

import os, re, sys

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent.py")
ENV    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

# ── Safety check ──────────────────────────────────────────────────────────
if not os.path.exists(TARGET):
    print(f"ERROR: Cannot find {TARGET}")
    sys.exit(1)

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

original = src   # keep for diff reporting

# ── 1. Replace import ─────────────────────────────────────────────────────
# Handle: from langchain_openai import ChatOpenAI
#     or: from langchain_openai import ChatOpenAI, ...
src = re.sub(
    r"from langchain_openai import (.*?)ChatOpenAI(.*?)\n",
    lambda m: (
        # If there were other things imported alongside ChatOpenAI, keep them
        # but add a separate groq import
        (f"from langchain_openai import {m.group(1).rstrip(', ')}{m.group(2).lstrip(', ')}\n"
         if (m.group(1).strip() or m.group(2).strip())
         else "")
        + "from langchain_groq import ChatGroq\n"
    ),
    src,
    flags=re.IGNORECASE,
)

# If ChatGroq import is already there, de-dupe
lines = src.splitlines()
seen, out = set(), []
for line in lines:
    if line.strip() == "from langchain_groq import ChatGroq":
        if line in seen:
            continue
        seen.add(line)
    out.append(line)
src = "\n".join(out)

# ── 2. Replace instantiation ──────────────────────────────────────────────
# Handles:  ChatOpenAI(model="gpt-4o-mini", ...)
#       or: ChatOpenAI(model='gpt-4o-mini', ...)
#       or: ChatOpenAI(model="gpt-4o", ...)
src = re.sub(
    r"ChatOpenAI\s*\(",
    "ChatGroq(",
    src,
)

# Replace OpenAI model names with a capable Groq model
for old_model in ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo"]:
    src = src.replace(f'model="{old_model}"', 'model="llama-3.3-70b-versatile"')
    src = src.replace(f"model='{old_model}'", "model='llama-3.3-70b-versatile'")

# ── 3. Ensure dotenv is loaded early ─────────────────────────────────────
if "load_dotenv" not in src:
    # Insert after the last regular import block
    dotenv_block = "from dotenv import load_dotenv\nload_dotenv()\n\n"
    # Put it right before the first non-import line that isn't a comment
    src = re.sub(
        r"((?:^(?:import |from |\s*#)[^\n]*\n)+)",
        r"\1" + dotenv_block,
        src,
        count=1,
        flags=re.MULTILINE,
    )

# ── Write back ────────────────────────────────────────────────────────────
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

print("✅  agent.py patched:")
print("    • ChatOpenAI  →  ChatGroq")
print("    • model       →  llama-3.3-70b-versatile")
print("    • load_dotenv() added if missing")
print()

# ── 4. Check .env has GROQ_API_KEY ────────────────────────────────────────
if os.path.exists(ENV):
    with open(ENV) as f:
        env_content = f.read()
    if "GROQ_API_KEY" in env_content:
        # Check it's not empty
        match = re.search(r"GROQ_API_KEY\s*=\s*(.+)", env_content)
        if match and match.group(1).strip() not in ("", '""', "''"):
            print("✅  .env: GROQ_API_KEY is set")
        else:
            print("⚠️  .env: GROQ_API_KEY is EMPTY — please add your key")
            print('    Edit .env and set:  GROQ_API_KEY=gsk_xxxxxxxxxxxx')
    else:
        print("⚠️  .env: GROQ_API_KEY not found — adding placeholder...")
        with open(ENV, "a") as f:
            f.write("\nGROQ_API_KEY=your_groq_api_key_here\n")
        print('    Edit .env and replace:  your_groq_api_key_here  →  your real key')
        print('    Get a free key at: https://console.groq.com/keys')
else:
    print("⚠️  No .env file found — creating one...")
    with open(ENV, "w") as f:
        f.write("MONDAY_API_KEY=your_monday_api_key_here\n")
        f.write("GROQ_API_KEY=your_groq_api_key_here\n")
    print("    Edit .env and fill in both keys.")
    print("    Groq free key: https://console.groq.com/keys")

print()
print("─" * 50)
print("Next steps:")
print("  1. Make sure .env has a valid GROQ_API_KEY")
print("  2. Run: py -3.12 -m chainlit run app.py")
