"""Rotating, resumable multi-domain public metadata collection for VISUAL."""
import json
import os
import time
from pathlib import Path
from api_harvest import harvest_public_metadata

DOMAIN_QUERIES = {
  "medicine": ["clinical medicine systematic review", "public health epidemiology", "medical imaging open dataset"],
  "biology": ["molecular biology genomics", "proteomics biodiversity"],
  "veterinary": ["veterinary medicine animal disease livestock health", "animal welfare veterinary epidemiology open research"],
  "animals_wildlife": ["wildlife species animal behaviour ecology open dataset", "mammals birds reptiles amphibians biodiversity occurrence"],
  "history": ["ancient history archaeology historical archive", "manuscripts epigraphy cultural heritage"],
  "education": ["teacher education pedagogy open educational resources", "mathematics education curriculum"],
  "coding": ["software engineering programming languages", "open source software code dataset"],
  "ai": ["machine learning deep learning foundation models", "natural language processing computer vision"],
  "agents": ["AI agents tool use benchmark", "multi agent systems planning reasoning"],
  "tools": ["developer tools compilers databases operating systems", "robotics automation engineering"],
  "physics": ["physics astronomy materials science", "particle physics open data"],
  "chemistry": ["chemistry chemical materials research", "drug discovery molecular datasets"],
  "mathematics": ["pure mathematics applied mathematics statistics", "theorem proving mathematical datasets"],
  "agriculture": ["agriculture crop science soil food security", "livestock plant pathology"],
  "climate": ["climate change meteorology weather", "oceanography hydrology earth observation"],
  "space": ["astronomy astrophysics planetary science NASA", "satellite earth observation"],
  "engineering": ["civil mechanical electrical engineering", "electronics semiconductor manufacturing"],
  "energy": ["renewable energy power grids batteries", "nuclear energy energy systems"],
  "economics": ["economics finance development statistics", "labor markets trade public policy"],
  "law": ["law legal scholarship human rights legislation", "comparative law public legal information"],
  "languages": ["linguistics language documentation multilingual corpora", "Hindi language NLP speech"],
  "culture": ["music art anthropology folklore cultural heritage", "literature archives oral history"],
  "geography": ["geography geospatial maps population", "urban planning transportation infrastructure"],
  "environment": ["ecology conservation pollution environmental science", "biodiversity species occurrence"],
  "oceans": ["marine biology fisheries ocean data", "coral reefs ocean circulation"],
  "disasters": ["earthquake flood wildfire disaster risk", "emergency management resilience"],
  "security": ["cybersecurity cryptography vulnerability research", "software security threat intelligence"],
  "business": ["management entrepreneurship industry supply chains", "operations research logistics"],
  "sports": ["sports science biomechanics exercise physiology", "sports analytics open data"],
  "human_behavior": ["human behavior everyday activities social interaction behavioral science open dataset", "human action recognition walking running sitting standing hand movements gestures"],
  "speech_voice": ["multilingual speech corpus spontaneous conversation speech recognition open dataset", "prosody laughter crying emotion speech voice activity dataset"],
  "facial_expression": ["facial expression action units gaze head pose emotion recognition dataset", "face gesture non-identifying landmark movement research dataset"],
  "memory_cognition": ["human memory cognition attention learning decision making psychology dataset", "episodic memory autobiographical memory cognitive task open research data"],
  "social_science": ["sociology social networks demographics migration public survey dataset", "anthropology ethnography oral history community behavior open data"],
  "social_platforms": ["public social media trends platform governance content moderation research dataset", "public online communities discussion network misinformation research dataset"],
  "robotics_motion": ["robotics human robot interaction motion capture manipulation dataset", "human pose estimation gait locomotion biomechanics open dataset"],
  "manufacturing": ["manufacturing industrial engineering predictive maintenance machine sensor dataset", "factory process quality control CNC robotics semiconductor production research data"],
  "mechanical": ["mechanical engineering fluid dynamics thermodynamics vibration materials dataset", "machine components CAD finite element simulation engineering open data"],
  "electrical_electronics": ["electrical engineering power electronics circuits semiconductor devices dataset", "microelectronics chip fabrication testing reliability open research data"],
  "transport": ["transportation traffic pedestrian mobility public transit open data", "vehicle dynamics autonomous driving road safety dataset"],
  "construction": ["construction engineering building materials structural health monitoring dataset", "architecture infrastructure bridge civil engineering open data"],
  "geology": ["geology tectonics minerals volcanology geophysics open research", "earth history rocks soil groundwater geoscience datasets"],
  "paleontology": ["paleontology fossils prehistoric life evolution open research", "dinosaur fossil vertebrate invertebrate paleobiology collections"],
  "archaeology_technology": ["archaeological technology ancient engineering tools metallurgy", "history of inventions ancient machines materials construction"],
  "neuroscience": ["neuroscience brain behavior neural systems open datasets", "cognitive neuroscience motor control perception attention"],
  "psychology": ["psychology emotion behavior personality development open research", "clinical psychology social psychology experimental datasets"],
  "biomechanics": ["human biomechanics gait posture locomotion motion capture open data", "muscle skeletal movement ergonomics sports biomechanics"],
  "sign_language": ["sign language gestures handshape facial grammar open corpus", "gesture recognition sign language linguistics datasets"],
  "performing_arts": ["dance theatre acting facial expression body language movement", "music performance voice prosody rhythm gesture research"],
  "food_nutrition": ["food science nutrition public health food composition open data", "agri food processing fermentation food safety research"],
  "water_resources": ["hydrology water quality groundwater river basin open datasets", "water treatment desalination sanitation engineering research"],
  "quantum_technology": ["quantum computing quantum information devices open research", "quantum sensors materials communication technology"],
  "patents_inventions": ["patent inventions technology trends public patent metadata", "historical patents engineering inventions innovation research"],
  "standards": ["engineering technical standards interoperability public standards", "medical safety manufacturing quality measurement standards"],
  "open_hardware": ["open source hardware electronics robotics designs", "microcontroller embedded systems circuit schematics open projects"],
  "public_policy": ["public policy governance institutions development open data", "government services public administration regulatory research"],
  "discovery_frontier": ["recent scientific discoveries emerging technologies research frontiers", "interdisciplinary unexplored research questions open science"],
  "deep_learning": ["deep learning neural network architectures optimization training benchmarks", "self supervised learning representation learning foundation models research"],
  "computer_vision": ["computer vision image video understanding object detection segmentation open datasets", "human pose estimation action recognition facial action units gaze tracking"],
  "multimodal_ai": ["multimodal AI vision language audio video models benchmarks", "cross modal representation learning grounding perception research"],
  "medical_imaging": ["medical imaging radiology MRI CT ultrasound pathology open research datasets", "medical image segmentation detection clinical validation explainable AI"],
  "clinical_trials": ["clinical trials interventions outcomes trial registries open research", "randomized controlled trials systematic reviews treatment evidence"],
  "genomics_proteomics": ["genomics transcriptomics proteomics single cell biology open datasets", "protein structure function molecular biology bioinformatics research"],
  "human_motion": ["human activity recognition gait pose estimation body movement datasets", "hand gestures sign language facial expression body posture motion capture"],
  "audio_speech": ["speech emotion recognition speaker diarization acoustic phonetics open corpora", "environmental sound classification animal vocalization audio datasets"],
  "semiconductor_research": ["semiconductor device physics chip fabrication lithography packaging reliability", "integrated circuits transistor process nodes materials yield testing research"],
  "materials_science": ["materials science alloys polymers ceramics nanomaterials characterization datasets", "battery materials catalysts superconductors crystal structures research"],
  "robotics_agents": ["robot learning manipulation navigation embodied AI agent benchmarks", "autonomous agents planning tool use reinforcement learning robotics"],
  "ancient_civilizations": ["ancient civilizations archaeology epigraphy artifacts trade technology", "historical engineering architecture metallurgy inventions manuscripts"],

  "india": ["India public health agriculture census education", "India history languages geography"],
  "animal_taxonomy": ["global animal taxonomy species subspecies taxonomy phylogeny open datasets", "invertebrates vertebrates mammals birds reptiles amphibians fish taxonomy"],
  "animal_morphology": ["animal morphology anatomy body size shape coloration pattern pigmentation", "animal development sexual dimorphism seasonal plumage coat morphology variation"],
  "animal_behavior": ["animal behaviour ethology social behaviour feeding mating migration territoriality", "animal cognition problem solving tool use play cooperation learning"],
  "animal_communication": ["animal communication signals calls courtship alarm contact vocal repertoire", "interspecies communication acoustic signaling chemical visual tactile signals"],
  "animal_bioacoustics": ["animal bioacoustics birdsong mammal calls amphibian insects sound datasets", "whale dolphin bat echolocation wolf howling frog calls annotated audio"],
  "animal_vision_color": ["animal coloration camouflage mimicry iridescence structural color visual ecology", "animal vision ultraviolet polarization color perception comparative datasets"],
  "animal_life_history": ["animal life history development reproduction lifespan growth survival datasets", "seasonal behavior hibernation torpor migration breeding phenology animals"],
  "plants_traits_ecology": ["plant morphology leaf flower root seed traits phenology open datasets", "plant behavior tropism signaling pollination dispersal ecological interactions"],
  "ecosystems_foodwebs": ["ecosystem ecology food webs trophic interactions predator prey datasets", "population dynamics habitat connectivity biodiversity conservation monitoring"],
  "neuroscience_cognition": ["neuroscience cognition perception attention memory decision making open datasets", "brain development plasticity learning executive function cognitive neuroscience"],
  "brain_imaging": ["human brain MRI fMRI EEG MEG connectomics open neuroimaging datasets", "neural circuits brain atlases cell types electrophysiology neuroscience data"],
  "learning_intelligence": ["learning science intelligence cognitive abilities reasoning problem solving research", "skill acquisition expertise metacognition education cognitive development datasets"],
  "psychometrics_behavior": ["psychometrics measurement scales reliability validity cognitive assessment datasets", "human behavior social cognition personality decision making experimental research"],
  "medicine_clinical": ["clinical medicine diagnosis treatment outcomes guidelines evidence datasets", "medical specialties cardiology neurology oncology infectious disease clinical research"],
  "medicine_public_health": ["epidemiology disease surveillance public health health systems open datasets", "nutrition maternal child health environmental health occupational health research"],
  "medical_methods": ["medical research methodology clinical study design randomized trials cohort studies", "systematic reviews meta analysis biostatistics reproducibility clinical evidence"],
  "engineering_methods": ["engineering design methodology systems engineering reliability safety analysis", "engineering simulation finite element computational fluid dynamics optimization methods"],
  "manufacturing_processes": ["manufacturing process planning quality control metrology lean production datasets", "industrial process monitoring failure analysis yield optimization maintenance research"],
  "electronics_circuits": ["electronics analog digital circuits PCB embedded systems open hardware research", "semiconductor testing chip design verification signal integrity power electronics"],
  "robotics_perception_control": ["robotics perception localization mapping motion planning control datasets", "robot manipulation locomotion grasping tactile sensing human robot interaction"],
  "computer_science_methods": ["algorithms data structures distributed systems databases operating systems research", "programming languages formal methods software testing verification benchmarks"],
  "materials_properties": ["materials properties mechanical thermal electrical optical chemical datasets", "materials characterization microscopy spectroscopy crystallography open data"],
  "energy_systems": ["energy systems power generation transmission storage grid reliability datasets", "solar wind hydrogen batteries nuclear energy lifecycle research"],
  "earth_observation": ["remote sensing satellite imagery land cover climate atmosphere ocean datasets", "geospatial GIS hydrology hazards geology earth observation research"],
  "history_knowledge": ["world history primary sources archives manuscripts archaeology material culture", "history of science technology medicine engineering inventions methods"],
  "philosophy_ethics": ["philosophy epistemology logic ethics reasoning knowledge theory research", "research ethics scientific integrity responsible innovation technology governance"],
  "economics_work": ["labor economics productivity occupations workplace skills industry datasets", "development economics inequality institutions markets behavioral economics research"],
  "agriculture_animal_husbandry": ["livestock animal husbandry breeding welfare behavior nutrition datasets", "crop science soil plant disease irrigation farm management open research"],
  "language_culture": ["world languages linguistics phonetics dialects endangered language corpora", "cultural anthropology folklore oral history social practices public datasets"],
  "audio_environment": ["environmental soundscape acoustic ecology urban rural sound datasets", "sound event detection machinery weather transport household acoustic research"]
}

# Each provider returns bounded public search metadata, not unrestricted file mirrors.
PROVIDERS = ("openalex", "crossref", "zenodo", "gbif", "nasa_cmr",
             "huggingface", "pubmed", "stackoverflow", "arxiv", "europe_pmc", "wikidata",
             "openverse_images", "openverse_audio", "wikimedia_commons", "internet_archive")

def collect_global_research(topics=None, per_request=25, max_requests=300, home=None, offset=None):
    """Rotate through all domain/provider tasks so scheduled runs don't repeat only the first page."""
    selected = sorted({x.strip().lower() for x in (topics or []) if x.strip()})
    unknown = sorted(set(selected) - set(DOMAIN_QUERIES))
    if unknown:
        raise ValueError("Unknown topics: " + ", ".join(unknown) + ". Available: " + ", ".join(DOMAIN_QUERIES))
    chosen = selected or list(DOMAIN_QUERIES)
    per_request = max(1, min(int(per_request), 25))
    max_requests = max(1, min(int(max_requests), 300))
    tasks = [(topic, query, provider) for topic in chosen
             for query in DOMAIN_QUERIES[topic] for provider in PROVIDERS]
    if not tasks:
        raise ValueError("No provider-query tasks are configured.")
    state_path = Path(home or Path.home() / ".visual") / "global_research_state.json"
    state_key = "all" if not selected else ",".join(sorted(set(selected)))
    saved_offset = 0
    saved_state = {}
    if offset is None and state_path.is_file():
        try:
            saved_state = json.loads(state_path.read_text(encoding="utf-8"))
            saved_offset = int(saved_state.get("next_offsets", {}).get(
                state_key, saved_state.get("next_offset", 0) if state_key == "all" else 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError, AttributeError):
            saved_offset = 0
            saved_state = {}
    start = int(saved_offset if offset is None else offset) % len(tasks)
    rotated_tasks = tasks[start:] + tasks[:start]
    results, errors = [], []
    attempted = 0
    for topic, query, provider in rotated_tasks[:max_requests]:
        attempted += 1
        try:
            item = harvest_public_metadata(provider, query, per_request, home, topic=topic)
            results.append({"topic": topic, **item})
        except Exception as exc:
            errors.append({"topic": topic, "provider": provider,
                           "query": query, "error": str(exc)[:240]})
        time.sleep(0.4)
    next_offset = (start + attempted) % len(tasks)
    state_error = ""
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = state_path.with_suffix(".tmp")
        offsets = saved_state.get("next_offsets", {}) if isinstance(saved_state, dict) else {}
        if not isinstance(offsets, dict):
            offsets = {}
        offsets[state_key] = next_offset
        new_state = {"next_offsets": offsets, "last_task_key": state_key,
                     "next_offset": offsets.get("all", 0), "total_tasks": len(tasks),
                     "updated_at": time.time()}
        temp_path.write_text(json.dumps(new_state, indent=2), encoding="utf-8")
        os.replace(temp_path, state_path)
    except OSError as exc:
        state_error = str(exc)[:240]
    summary = _summary(results, errors, attempted, chosen)
    summary["task_offset"] = start
    summary["next_task_offset"] = next_offset
    summary["total_provider_query_tasks"] = len(tasks)
    summary["rotation_state_error"] = state_error
    summary["stopped_reason"] = "per-run request cap reached" if len(tasks) > max_requests else "all selected tasks processed"
    return summary

def _summary(results, errors, attempted, topics):
    provider_status_counts = {}
    for item in results:
        provider = item.get("provider", "unknown")
        status = item.get("status", "unknown")
        counts = provider_status_counts.setdefault(provider, {})
        counts[status] = counts.get(status, 0) + 1
    for item in errors:
        provider = item.get("provider", "unknown")
        counts = provider_status_counts.setdefault(provider, {})
        counts["error"] = counts.get("error", 0) + 1
    return {
        "topics": topics,
        "requests_attempted": attempted,
        "successful_requests": sum(1 for x in results if x.get("status") in ("indexed", "already_indexed")),
        "empty_results": sum(1 for x in results if x.get("status") == "empty"),
        "failed_requests": len(errors) + sum(1 for x in results if x.get("status") not in ("indexed", "already_indexed", "empty")),
        "indexed_characters": sum(int(x.get("indexed_characters", 0)) for x in results),
        "fetched_characters": sum(int(x.get("fetched_characters", x.get("indexed_characters", 0))) for x in results),
        "provider_status_counts": provider_status_counts,
        "results": results,
        "errors": errors,
        "scope": "Public API search metadata only; full-text and bulk dataset files require separate item-level rights and download workflows.",
    }
