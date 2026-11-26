"""Public-source Knowledge Base tools for VISUAL."""
import json
from knowledge_engine import add_source, ingest_source, search_knowledge, knowledge_stats
from catalog import queue_catalog

@tool("Public HTTPS source ko VISUAL Knowledge Base mein queue karo. Sirf wahi source add karo jiska public access aur reuse license/terms acceptable ho.",
      {"url": S("public HTTPS documentation/article URL"), "license": S("license/terms label; unknown if not known"), "topic": S("coding, python, android, ai, security, etc.")})
def knowledge_add_source(url, license="unknown", topic="general"):
    return json.dumps(add_source(url, license, topic, globals().get("HOME")), ensure_ascii=False)

@tool("Queued public source ko robots.txt aur size limits respect karte hue fetch aur local index karo.",
      {"source_id": S("knowledge_add_source se mila source ID")}, risky=True)
def knowledge_ingest(source_id):
    return json.dumps(ingest_source(source_id, globals().get("HOME")), ensure_ascii=False)

@tool("VISUAL ke local public Knowledge Base mein coding, programming, AI, Android aur security se related indexed material khojo.",
      {"query": S("search question or keywords"), "limit": S("maximum results 1-20")})
def knowledge_search(query, limit=8):
    return json.dumps(search_knowledge(query, limit, globals().get("HOME")), ensure_ascii=False, indent=2)[:12000]

@tool("VISUAL Public Knowledge Base ka storage aur indexing status dikhao.")
def knowledge_status():
    return json.dumps(knowledge_stats(globals().get("HOME")), ensure_ascii=False, indent=2)

@tool("Curated public knowledge catalog se programming, AI, science, security, standards, Android, data aur education sources queue karo. Ye fetch nahi karta; terms check karne ke baad ingest karein.",
      {"topics": S("optional comma-separated topic prefixes; blank means all catalog categories")})
def knowledge_queue_catalog(topics=""):
    selected = [x.strip() for x in str(topics).split(",") if x.strip()]
    return json.dumps(queue_catalog(globals().get("HOME"), selected), ensure_ascii=False)[:12000]
