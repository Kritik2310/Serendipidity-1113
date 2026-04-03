from __future__ import annotations

import re
from pathlib import Path

import pdfplumber


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PDF_PATH = BASE_DIR / "data" / "icu_clinical_guidelines.pdf"

SECTION_CATEGORY_MAP = {
    1: "sepsis",
    2: "sofa",
    3: "qsofa",
    4: "sepsis",
    5: "septic_shock",
    6: "aki",
    7: "ards",
    8: "sepsis",
    9: "early_warning",
    10: "lab_thresholds",
    15: "outlier_detection",
}


def extract_pdf_pages(pdf_path: str | Path = DEFAULT_PDF_PATH) -> list[dict]:
    pages = []
    path = Path(pdf_path)

    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text() or ""
            text = clean_pdf_text(raw_text)
            if not text:
                continue

            pages.append(
                {
                    "page_number": index,
                    "source": path.name,
                    "text": text,
                }
            )

    return pages


def clean_pdf_text(text: str) -> str:
    text = text.replace("(cid:127)", "-")
    text = text.replace("‡", ">=")
    text = text.replace("≤", "<=")
    text = text.replace("≥", ">=")
    text = text.replace("£", "<=")
    text = text.replace("Ã—", "x")
    text = text.replace("â‰¥", ">=")
    text = text.replace("â‰¤", "<=")
    text = text.replace("â€”", "-")
    text = text.replace("—", "-")

    lines = [line.strip() for line in text.splitlines()]
    cleaned_lines = []
    for line in lines:
        if not line:
            cleaned_lines.append("")
            continue

        lowered = line.lower()
        if lowered.startswith("icu clinical guidelines reference"):
            continue
        if lowered.startswith("for rag pipeline use"):
            continue
        if lowered.startswith("important: this document is for ai-assisted clinical decision support only."):
            continue
        if re.fullmatch(r"page\s+\d+", lowered):
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def build_pdf_guideline_chunks(pdf_path: str | Path = DEFAULT_PDF_PATH) -> list[dict]:
    pages = extract_pdf_pages(pdf_path)
    chunks = []
    pending_section = None

    for page in pages:
        page_text = page["text"]
        section_match = re.search(r"SECTION\s+(\d+)", page_text, flags=re.IGNORECASE)
        if section_match:
            pending_section = int(section_match.group(1))

        paragraphs = split_page_into_paragraphs(page_text)
        for paragraph_index, paragraph in enumerate(paragraphs):
            section_number = detect_section_number(paragraph) or pending_section
            category = SECTION_CATEGORY_MAP.get(section_number, "general")
            source = build_source_label(section_number)

            chunks.append(
                {
                    "id": f"pdf-p{page['page_number']}-c{paragraph_index}",
                    "text": paragraph,
                    "metadata": {
                        "source": source,
                        "category": category,
                        "page": page["page_number"],
                        "section": section_number or 0,
                    },
                }
            )

    chunks.extend(build_supplementary_chunks())
    return dedupe_chunks(chunks)


def split_page_into_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    paragraphs = []
    for part in parts:
        normalized = " ".join(line.strip() for line in part.splitlines() if line.strip())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if len(normalized) >= 120:
            paragraphs.append(normalized)
    return paragraphs


def detect_section_number(text: str) -> int | None:
    match = re.search(r"SECTION\s+(\d+)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def build_source_label(section_number: int | None) -> str:
    if section_number == 1:
        return "Sepsis-3 Consensus Definitions"
    if section_number == 2:
        return "SOFA Score Reference"
    if section_number == 3:
        return "qSOFA Bedside Tool"
    if section_number == 4:
        return "Surviving Sepsis Campaign 2021"
    if section_number == 5:
        return "Septic Shock Identification and Management"
    if section_number == 6:
        return "KDIGO AKI Guidelines 2012"
    if section_number == 7:
        return "ARDS Berlin Definition"
    if section_number == 8:
        return "NICE NG51 Sepsis Recognition"
    if section_number == 9:
        return "NEWS2 Early Warning Score"
    if section_number == 10:
        return "Laboratory Reference Ranges and Clinical Thresholds"
    if section_number == 15:
        return "Outlier Detection Reference Values"
    return "ICU Clinical Guidelines PDF"


def build_supplementary_chunks() -> list[dict]:
    return [
        {
            "id": "supp-sofa-renal",
            "text": (
                "SOFA renal scoring: creatinine <1.2 mg/dL = score 0, 1.2-1.9 = score 1, "
                "2.0-3.4 = score 2, 3.5-4.9 or urine output <500 mL/day = score 3, "
                ">=5.0 or urine output <200 mL/day = score 4."
            ),
            "metadata": {"source": "SOFA Score Reference", "category": "sofa", "page": 6, "section": 2},
        },
        {
            "id": "supp-sofa-cardiovascular",
            "text": (
                "SOFA cardiovascular scoring includes MAP <70 mmHg for score 1 and escalating "
                "vasopressor requirements for higher scores. Septic patients with vasopressors "
                "and rising lactate require urgent assessment."
            ),
            "metadata": {"source": "SOFA Score Reference", "category": "sofa", "page": 6, "section": 2},
        },
        {
            "id": "supp-qsofa-thresholds",
            "text": (
                "qSOFA is positive when at least two of the following are present: altered mentation, "
                "respiratory rate >=22 per minute, and systolic blood pressure <=100 mmHg."
            ),
            "metadata": {"source": "qSOFA Bedside Tool", "category": "qsofa", "page": 8, "section": 3},
        },
        {
            "id": "supp-septic-shock-definition",
            "text": (
                "Septic shock requires sepsis plus persistent hypotension needing vasopressors to maintain "
                "MAP >=65 mmHg and lactate >2 mmol/L despite adequate fluid resuscitation."
            ),
            "metadata": {"source": "Septic Shock Identification and Management", "category": "septic_shock", "page": 12, "section": 5},
        },
        {
            "id": "supp-aki-definition",
            "text": (
                "KDIGO AKI definition: creatinine rise >=0.3 mg/dL in 48 hours, or >=1.5x baseline in 7 days, "
                "or urine output <0.5 mL/kg/hour for >=6 hours."
            ),
            "metadata": {"source": "KDIGO AKI Guidelines 2012", "category": "aki", "page": 13, "section": 6},
        },
        {
            "id": "supp-ards-definition",
            "text": (
                "ARDS requires onset within 1 week, bilateral opacities on imaging, respiratory failure not "
                "explained by cardiac overload, and PaO2/FiO2 <=300 mmHg with PEEP or CPAP >=5 cmH2O."
            ),
            "metadata": {"source": "ARDS Berlin Definition", "category": "ards", "page": 15, "section": 7},
        },
        {
            "id": "supp-news2-thresholds",
            "text": (
                "NEWS2 score >=7 indicates high risk requiring immediate clinician review with critical care "
                "competencies and consideration of ICU transfer."
            ),
            "metadata": {"source": "NEWS2 Early Warning Score", "category": "early_warning", "page": 18, "section": 9},
        },
        {
            "id": "supp-lab-lactate",
            "text": (
                "Laboratory threshold summary: lactate >2.0 mmol/L indicates hypoperfusion and lactate >4.0 mmol/L "
                "is a high-mortality threshold strongly associated with septic shock."
            ),
            "metadata": {"source": "Laboratory Reference Ranges and Clinical Thresholds", "category": "lab_thresholds", "page": 19, "section": 10},
        },
        {
            "id": "supp-lab-creatinine",
            "text": (
                "Creatinine thresholds: rise >=0.3 mg/dL in 48 hours suggests AKI, >4.0 mg/dL is critical, "
                "and SOFA renal points increase from >1.2 to >5.0 mg/dL."
            ),
            "metadata": {"source": "Laboratory Reference Ranges and Clinical Thresholds", "category": "lab_thresholds", "page": 19, "section": 10},
        },
        {
            "id": "supp-lab-platelets",
            "text": (
                "Platelet thresholds: <150 begins SOFA coagulation scoring, <50 indicates severe coagulopathy, "
                "and <20 is a score 4 threshold with spontaneous bleeding risk."
            ),
            "metadata": {"source": "Laboratory Reference Ranges and Clinical Thresholds", "category": "lab_thresholds", "page": 20, "section": 10},
        },
        {
            "id": "supp-outlier-rule",
            "text": (
                "Outlier handling rule: when a lab result is flagged as a probable outlier, the AI system must "
                "exclude it from SOFA scoring and avoid changing risk assessment until redraw confirmation."
            ),
            "metadata": {"source": "Outlier Detection Reference Values", "category": "outlier_detection", "page": 22, "section": 15},
        },
        {
            "id": "supp-outlier-thresholds",
            "text": (
                "Outlier thresholds include potassium >9.0 or <1.5 mEq/L, sodium >175 or <110 mEq/L, "
                "lactate >30 mmol/L, and WBC >500 x10^3/uL or <0.1 x10^3/uL as physiologically implausible."
            ),
            "metadata": {"source": "Outlier Detection Reference Values", "category": "outlier_detection", "page": 21, "section": 15},
        },
    ]


def dedupe_chunks(chunks: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for chunk in chunks:
        key = re.sub(r"\s+", " ", chunk["text"]).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(chunk)
    return output
