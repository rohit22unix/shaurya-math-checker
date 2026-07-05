from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


@dataclass
class ParsedQuestion:
    qid: str
    prompt: str
    options: list[str]


_question_re = re.compile(r"^\s*(?:Q\s*)?(\d{1,3})\s*[\).:-]\s*(.+)$", re.IGNORECASE)
_option_re = re.compile(r"^\s*([A-Da-d])\s*[\).:-]\s*(.+)$")
_inline_option_re = re.compile(r"([A-Da-d])\s*[\).:-]\s*([^-A-D]+?)(?=(?:\s+[A-Da-d]\s*[\).:-])|$)")


class OCRWorksheetParser:
    def __init__(self) -> None:
        self._engine = RapidOCR()

    def extract_text_lines(self, image_bytes: bytes) -> list[str]:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)
        result, _ = self._engine(img_array)
        if not result:
            return []

        lines: list[str] = []
        for row in result:
            text = str(row[1]).strip()
            if text:
                lines.append(text)

        return lines

    def parse_mcq_questions(self, lines: list[str]) -> list[ParsedQuestion]:
        questions: list[ParsedQuestion] = []
        current_qid: str | None = None
        current_prompt_parts: list[str] = []
        current_options: list[str] = []

        def flush() -> None:
            nonlocal current_qid, current_prompt_parts, current_options
            if not current_qid:
                return
            prompt = " ".join(part.strip() for part in current_prompt_parts if part.strip())
            clean_options = [opt.strip() for opt in current_options if opt.strip()]
            if prompt and len(clean_options) >= 2:
                questions.append(
                    ParsedQuestion(
                        qid=f"Q{current_qid}",
                        prompt=prompt,
                        options=clean_options,
                    )
                )
            current_qid = None
            current_prompt_parts = []
            current_options = []

        for raw_line in lines:
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue

            question_match = _question_re.match(line)
            if question_match:
                flush()
                current_qid = question_match.group(1)
                remainder = question_match.group(2).strip()
                inline_options = self._extract_inline_options(remainder)
                if inline_options:
                    current_prompt_parts.append(self._strip_inline_options_from_text(remainder))
                    current_options.extend(inline_options)
                else:
                    current_prompt_parts.append(remainder)
                continue

            option_match = _option_re.match(line)
            if option_match and current_qid:
                current_options.append(option_match.group(2).strip())
                continue

            inline_options = self._extract_inline_options(line)
            if inline_options and current_qid:
                if not current_options:
                    current_prompt_parts.append(self._strip_inline_options_from_text(line))
                current_options.extend(inline_options)
                continue

            if current_qid and len(current_options) < 2:
                current_prompt_parts.append(line)

        flush()
        return questions

    @staticmethod
    def _extract_inline_options(text: str) -> list[str]:
        matches = _inline_option_re.findall(text)
        if not matches:
            return []
        return [m[1].strip() for m in matches]

    @staticmethod
    def _strip_inline_options_from_text(text: str) -> str:
        first_option = re.search(r"\s+[A-Da-d]\s*[\).:-]\s*", text)
        if not first_option:
            return text.strip()
        return text[: first_option.start()].strip()


def parsed_questions_to_dict(items: list[ParsedQuestion]) -> list[dict[str, Any]]:
    return [
        {
            "qid": item.qid,
            "prompt": item.prompt,
            "options": item.options,
        }
        for item in items
    ]
