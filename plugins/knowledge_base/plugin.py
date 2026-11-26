"""Public-source Knowledge Base tools for VISUAL."""
import json
from knowledge_engine import add_source, ingest_source, search_knowledge, knowledge_stats
from catalog import queue_catalog, collect_catalog
from local_import import import_local_file
from bulk_download import download_dataset
from api_harvest import harvest_public_metadata
from global_research import collect_global_research

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

@tool("Curated public catalog ke queued sources ko abhi batch mein download aur local index karo. Max 30 pages per run; robots.txt, licensing notes aur bandwidth limits respect honge.",
      {"limit": S("1 se 30 sources; default 10"), "topics": S("optional topic prefixes separated by commas")}, risky=True)
def knowledge_collect_now(limit=10, topics=""):
    selected = [x.strip() for x in str(topics).split(",") if x.strip()]
    return json.dumps(collect_catalog(globals().get("HOME"), selected, limit), ensure_ascii=False)[:14000]


@tool("Phone ya Termux ke local Download/Documents folder se TXT, Markdown, HTML, CSV, JSON, JSONL aur gzip datasets ko internet ke bina VISUAL ke local Knowledge Base mein index karo. Bade datasets ke liye JSONL.GZ behtar hai; data user ke phone par hi rahega.",
      {"path": S("exact local file path, e.g. /storage/emulated/0/Download/data.jsonl.gz"),
       "topic": S("subject/category label"),
       "max_records": S("0 = all records; otherwise a bounded number")}, risky=True)
def knowledge_import_local(path, topic="local-dataset", max_records=0):
    return json.dumps(import_local_file(path, topic, globals().get("HOME"), max_records), ensure_ascii=False)[:12000]


@tool("User-selected official public dataset file ko bounded size ke saath download karo. HTTPS only, resume support, SHA-256 verification, private IP/redirect blocking. Download automatic nahi hota; exact URL aur destination user ko dena hoga.",
      {"url": S("exact official HTTPS file URL"),
       "destination": S("absolute path inside ~/.visual, Android Download or Documents"),
       "max_bytes": S("maximum bytes; default 536870912 (512 MiB)"),
       "expected_sha256": S("optional publisher checksum")}, risky=True)
def knowledge_download_dataset(url, destination, max_bytes=536870912, expected_sha256=""):
    return json.dumps(download_dataset(url, destination, max_bytes, expected_sha256, globals().get("HOME")), ensure_ascii=False)[:12000]


@tool("OpenAlex, Crossref, Zenodo, Hugging Face, PubMed, Europe PMC, Wikidata, Stack Exchange, arXiv, GBIF, NASA, Openverse Images/Audio, Wikimedia Commons ya Internet Archive ke official public API se bounded research/dataset metadata khojo aur VISUAL local Knowledge Base mein index karo. Har run mein adhiktam 25 metadata records; yeh full-text ya poora repository download nahi karta.", 
      {"provider": S("openalex, crossref, zenodo, huggingface, pubmed, europe_pmc, wikidata, stackoverflow, arxiv, gbif, nasa_cmr, openverse_images, openverse_audio, wikimedia_commons, internet_archive"), "query": S("topic, title, author, DOI, or dataset keywords"), "limit": S("1-25 records; default 10")}, risky=True)
def knowledge_harvest_public_metadata(provider, query, limit=10):
    return json.dumps(harvest_public_metadata(provider, query, limit, globals().get("HOME")), ensure_ascii=False)[:12000]


@tool("VISUAL ke liye ek hi run mein deep learning, computer vision, multimodal AI, medical imaging, clinical trials, genomics, human motion, audio/speech, semiconductor research, materials science, robotics agents, medicine, biology, veterinary, wildlife, archaeology, engineering, agriculture, climate, space, law, economy, languages, cybersecurity aur anya domains ke official public APIs se metadata collect aur local index karo. 15 allowlisted APIs; default sabhi domains ka controlled batch; max 300 API requests per run. Retry-after, per-provider pacing aur duplicate checks enabled hain. Yeh metadata harvesting hai, full archive mirror ya model training nahi.", 
      {"topics": S("optional comma-separated topic keys; blank = all available domains"), "per_request": S("1-25 metadata records per API request; default 25"), "max_requests": S("1-300 API requests per run; default 300")}, risky=True)
def knowledge_collect_global_research(topics="", per_request=25, max_requests=300):
    selected = [x.strip() for x in str(topics).split(",") if x.strip()]
    return json.dumps(collect_global_research(selected, per_request, max_requests, globals().get("HOME")), ensure_ascii=False)[:24000]
