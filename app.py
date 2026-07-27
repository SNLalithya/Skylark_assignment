import os
import chainlit as cl
from dotenv import load_dotenv
load_dotenv()

try:
    from agent import create_agent, run_agent, generate_leadership_brief_fn
    _AGENT_OK = True
except ImportError as e:
    _AGENT_OK = False
    _IMPORT_ERROR = str(e)

_agent = None

def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent

@cl.on_chat_start
async def on_chat_start():
    if not _AGENT_OK:
        await cl.Message(content=f"Import error: {_IMPORT_ERROR}").send()
        return
    try:
        _get_agent()
    except Exception as e:
        await cl.Message(content=f"Init error: {e}").send()
        return
    await cl.Message(content="👋 **Skylark Drones BI Agent ready!**\n\nAsk me about your **Work Orders** or **Deals**.\n\n- *What is the total deal value?*\n- *Show open work orders by sector*\n- *Which deals are at Proposal stage?*\n- *Are there overdue work orders?*\n- Type `brief` for executive summary").send()

@cl.on_message
async def on_message(message: cl.Message):
    if not _AGENT_OK:
        await cl.Message(content=f"Agent not available: {_IMPORT_ERROR}").send()
        return
    user_text = message.content.strip()
    msg = cl.Message(content="⏳ Thinking...")
    await msg.send()
    try:
        agent = _get_agent()
        if user_text.lower() in ("brief", "leadership brief", "executive brief"):
            response = await cl.make_async(generate_leadership_brief_fn)()
        else:
            response = await cl.make_async(run_agent)(agent, user_text)
        msg.content = response
        await msg.update()
    except Exception as e:
        msg.content = f"❌ Error: {str(e)}"
        await msg.update()

if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
