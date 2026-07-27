"""
patch_monday_client.py
----------------------
Run this ONCE to add DealFilter and WorkOrderFilter to monday_client.py

Usage:
    py -3.12 patch_monday_client.py
"""

import os
import sys

TARGET = os.path.join(os.path.dirname(__file__), "monday_client.py")

PATCH = '''

# ─────────────────────────────────────────────────────────────────────────────
# Filter dataclasses  (added by patch_monday_client.py)
# ─────────────────────────────────────────────────────────────────────────────
from dataclasses import dataclass as _dc
from typing import Optional as _Opt

@_dc
class DealFilter:
    """All fields optional — omit to match everything."""
    sector:         _Opt[str]   = None
    stage:          _Opt[str]   = None
    status:         _Opt[str]   = None
    owner:          _Opt[str]   = None
    probability:    _Opt[str]   = None   # "High" / "Medium" / "Low"
    min_value:      _Opt[float] = None
    max_value:      _Opt[float] = None
    active_only:    bool        = False
    stuck_only:     bool        = False
    closing_before: _Opt[str]   = None   # ISO yyyy-mm-dd
    search_text:    _Opt[str]   = None


@_dc
class WorkOrderFilter:
    """All fields optional — omit to match everything."""
    sector:          _Opt[str]   = None
    exec_status:     _Opt[str]   = None
    wo_status:       _Opt[str]   = None
    customer:        _Opt[str]   = None
    bd_owner:        _Opt[str]   = None
    type:            _Opt[str]   = None
    min_contract:    _Opt[float] = None
    max_contract:    _Opt[float] = None
    min_billed:      _Opt[float] = None
    has_receivable:  bool        = False
    on_hold_only:    bool        = False
    search_text:     _Opt[str]   = None
'''

# ── Read current file ──────────────────────────────────────────────────────
if not os.path.exists(TARGET):
    print(f"ERROR: Cannot find {TARGET}")
    print("Make sure you run this script from inside the skylark-bi-agent folder.")
    sys.exit(1)

with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

# ── Check if already patched ───────────────────────────────────────────────
if "class DealFilter" in content and "class WorkOrderFilter" in content:
    print("✅  monday_client.py already has DealFilter and WorkOrderFilter.")
    print("    No patch needed — try running the app again.")
    sys.exit(0)

# ── Apply patch ────────────────────────────────────────────────────────────
with open(TARGET, "a", encoding="utf-8") as f:
    f.write(PATCH)

print("✅  Patch applied to monday_client.py")
print()

# ── Verify ─────────────────────────────────────────────────────────────────
try:
    import importlib.util, sys as _sys
    spec = importlib.util.spec_from_file_location("monday_client", TARGET)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "DealFilter"),       "DealFilter missing after patch!"
    assert hasattr(mod, "WorkOrderFilter"),  "WorkOrderFilter missing after patch!"
    assert hasattr(mod, "MondayClient"),     "MondayClient missing!"
    print("✅  Verification passed — all classes found:")
    print("    • MondayClient")
    print("    • DealFilter")
    print("    • WorkOrderFilter")
    print()
    print("Now run:  py -3.12 -m chainlit run app.py")
except Exception as e:
    print(f"❌  Verification failed: {e}")
    print("    The patch was written but something else may be wrong.")
    sys.exit(1)
