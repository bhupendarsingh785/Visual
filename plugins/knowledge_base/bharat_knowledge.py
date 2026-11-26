"""Hindi, Indic-script and Indian textual-heritage research expansion.

This adds targeted public-catalog search queries to VISUAL's existing bounded
metadata collector. It does not copy copyrighted books or claim to mirror
complete scriptures. Every full-text item still needs its own rights check.
"""
from global_research import DOMAIN_QUERIES

BHARAT_DOMAIN_QUERIES = {
    "hindi_language": [
        "Hindi language grammar phonology morphology syntax semantics pragmatics",
        "Hindi alphabet Devanagari varnamala vowels consonants matras anusvara visarga chandrabindu",
        "Devanagari Unicode normalization grapheme clusters conjunct consonants nukta typography",
        "Hindi orthography spelling punctuation numerals transliteration Romanization ISO 15919 IAST",
        "Hindi lexicography dictionaries thesaurus etymology word formation compounds",
        "Hindi dialects Braj Awadhi Bhojpuri Bundeli Bagheli Haryanvi Khari Boli linguistic corpora",
        "Hindi literature prose poetry drama short stories novels literary history criticism",
        "Hindi conversational corpus colloquial registers code switching Hinglish sociolinguistics",
        "Hindi NLP tokenization stemming lemmatization POS tagging dependency parsing named entities",
        "Hindi parallel corpus translation instruction question answering reading comprehension dataset",
        "Hindi speech corpus phonetics pronunciation accent prosody ASR TTS speaker diarization",
        "Hindi handwriting OCR printed text document layout recognition Devanagari benchmark",
        "Hindi child language literacy pedagogy reading writing graded vocabulary educational resources",
        "Hindi idioms proverbs lokokti muhavare phraseology discourse markers",
        "Hindi Braille accessibility language technology low resource evaluation benchmarks",
    ],
    "indic_scripts": [
        "Brahmic Indic scripts history paleography Brahmi Gupta Nagari Devanagari",
        "Devanagari script complete character inventory vowels consonants vowel signs virama",
        "Bengali Assamese Gurmukhi Gujarati Odia Tamil Telugu Kannada Malayalam scripts Unicode",
        "Sanskrit writing systems Devanagari Grantha Sharada Modi script manuscript catalogues",
        "Indic script OCR handwritten manuscript recognition datasets benchmark",
        "Indic language transliteration cross script mapping normalization Unicode standards",
        "Indic phonetics varnamala place of articulation aspiration voicing retroflex nasals",
        "Indic language corpora multilingual parallel datasets speech text open license",
    ],
    "sanskrit_language": [
        "Sanskrit grammar Panini Ashtadhyayi dhatu gana pratyaya sandhi samasa",
        "Sanskrit phonology shiksha svara vyanjana accent Vedic pitch accent",
        "Sanskrit lexicons dictionaries dhatupatha amarakosha etymology",
        "Sanskrit syntax semantics morphology dependency treebanks corpora",
        "Sanskrit manuscript digitization OCR paleography critical editions",
        "Sanskrit computational linguistics sandhi splitting compound analysis parsing",
        "Vedic Sanskrit classical Sanskrit Prakrit Apabhramsha historical linguistics",
        "Sanskrit prosody chandas metres meters poetry analysis",
        "Sanskrit translation parallel corpus aligned text evaluation",
    ],
    "hindu_texts": [
        "Rigveda Samaveda Yajurveda Atharvaveda public domain manuscript catalogue critical edition",
        "Vedic Samhita Brahmana Aranyaka Upanishad textual history recensions shakha",
        "Vedanga Shiksha Kalpa Vyakarana Nirukta Chandas Jyotisha scholarly catalogue",
        "Ramayana Valmiki Ramayana regional Ramayana manuscripts critical scholarship",
        "Mahabharata Bhagavad Gita textual transmission manuscripts critical edition",
        "Puranas Mahapurana Upapurana textual history catalogue Sanskrit",
        "Agama Tantra Shaiva Vaishnava Shakta textual traditions manuscript studies",
        "Dharma literature Dharmasutra Dharmashastra Manusmriti Yajnavalkya Smriti scholarship",
        "Itihasa Purana oral transmission commentary translation textual criticism",
        "Bhakti literature Alvar Nayanar Sant Kabir Tulsidas Surdas Mirabai regional traditions",
        "Hindu scriptures translations commentaries provenance edition translator publication date",
        "Indian manuscript libraries Sanskrit Grantha Sharada Devanagari palm leaf manuscripts",
        "Hindu textual traditions comparative studies history of interpretation philosophy",
        "Vedic recitation oral tradition shakha patha svara audio archive scholarly documentation",
    ],
    "hindu_philosophy": [
        "Hindu darshana Samkhya Yoga Nyaya Vaisheshika Mimamsa Vedanta primary texts",
        "Advaita Vishishtadvaita Dvaita Vedanta commentaries bhashya comparative philosophy",
        "Upanishadic philosophy Brahman Atman moksha knowledge scholarly interpretations",
        "Nyaya logic epistemology pramana inference debate Sanskrit primary sources",
        "Yoga Sutra Patanjali commentary philosophy practice textual history",
        "Mimamsa hermeneutics Vedic exegesis ritual interpretation",
        "Shaiva Shakta Vaishnava philosophical schools primary texts commentaries",
        "Indian philosophy ethics metaphysics epistemology ontology comparative scholarship",
        "Bhagavad Gita commentarial traditions translations interpretation history",
    ],
    "indian_knowledge_systems": [
        "Indian mathematics Sulba Sutra place value zero algebra geometry historical sources",
        "Indian astronomy Jyotisha siddhanta observatories historical manuscripts",
        "Ayurveda Charaka Samhita Sushruta Samhita Ashtanga Hridaya textual history",
        "Indian architecture Vastu Shastra Shilpa Shastra temple architecture manuscripts",
        "Indian music Natya Shastra Sangeet texts raga tala historical sources",
        "Indian linguistics Panini Bhartrihari Patanjali language philosophy",
        "Indian metallurgy water management agriculture historical technology primary sources",
        "Yoga history philosophy textual traditions primary sources scholarly research",
        "Indian knowledge systems critical editions provenance historical context evidence",
    ],
    "indian_literature": [
        "Hindi Sanskrit Tamil Telugu Kannada Bengali Marathi Gujarati Odia literature archives",
        "Indian epics poetry drama classical literature manuscript catalogues",
        "Braj Bhasha Awadhi Maithili Bhojpuri Rajasthani literary corpora",
        "Indian folk tales oral epics folklore regional language archives",
        "Panchatantra Hitopadesha Jataka story traditions editions translation history",
        "Indian children's literature short stories fables moral tales public domain",
        "Indian literary criticism bibliography authorship publication chronology",
    ],
    "indian_oral_traditions": [
        "India oral traditions folk songs storytelling epics public audio archives",
        "Vedic oral recitation preservation phonetics audio recordings scholarly collections",
        "Indian regional folklore legends proverbs riddles oral history archives",
        "Braj Awadhi Bhojpuri Rajasthani Haryanvi oral storytelling audio corpus",
        "Indian performing arts theatre puppetry katha vachana narrative traditions",
    ],
}

def install_bharat_domains():
    """Idempotently register targeted domains in the shared research catalogue."""
    for topic, queries in BHARAT_DOMAIN_QUERIES.items():
        DOMAIN_QUERIES[topic] = list(queries)
    return sorted(BHARAT_DOMAIN_QUERIES)
