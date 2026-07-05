import json
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st

from grader import (
    NO_ANSWER,
    OUT_OF_OPTIONS,
    OUT_OF_OPTIONS_MARK_INCORRECT,
    OUT_OF_OPTIONS_MARK_ISSUE,
    Question,
    StudentAnswer,
    grade_sheet,
)
from ocr_parser import OCRWorksheetParser, parsed_questions_to_dict
from report_export import sheet_result_to_csv_bytes, sheet_result_to_pdf_bytes


def render_camera_permission_notice() -> None:
    try:
        current_url = str(st.context.url)
        user_agent = str(st.context.headers.get("user-agent", "")).lower()
    except Exception:
        return

    is_mobile = any(token in user_agent for token in ["iphone", "android", "mobile", "ipad"])
    if not is_mobile:
        return

    parsed = urlparse(current_url)
    scheme = parsed.scheme.lower()

    if scheme != "https":
        st.warning(
            "Camera may not open on mobile over non-HTTPS links. Use the secure "
            "Cloudflare URL and allow camera permission in Safari."
        )


def render_mobile_worksheet_capture() -> bytes | None:
    st.subheader("Worksheet Photo Upload (Mobile Friendly)")
    st.caption(
        "Use this section on phone to quickly capture or upload worksheet photos."
    )

    mode = st.radio(
        "Choose capture method",
        ["Open camera", "Upload image"],
        horizontal=True,
        key="capture_mode",
    )

    image_file = None
    if mode == "Open camera":
        image_file = st.camera_input("Tap to open camera and capture worksheet")
    else:
        image_file = st.file_uploader(
            "Upload worksheet image",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            key="worksheet_image_upload",
        )

    if image_file is not None:
        img_bytes = image_file.getvalue()
        st.success("Worksheet image received.")
        st.image(img_bytes, caption="Captured worksheet", use_container_width=True)
        return img_bytes

    return None


def load_ocr_questions_from_image(image_bytes: bytes) -> list[dict[str, str | list[str]]]:
    parser = OCRWorksheetParser()
    lines = parser.extract_text_lines(image_bytes)
    parsed = parser.parse_mcq_questions(lines)
    return parsed_questions_to_dict(parsed)


def load_default_questions() -> list[Question]:
    return [
        Question(
            qid="Q1",
            prompt="What is 7 + 5?",
            options=["10", "11", "12", "13"],
            correct_answer="12",
            explanation="7 + 5 = 12.",
            points=1,
        ),
        Question(
            qid="Q2",
            prompt="What is 9 x 3?",
            options=["18", "27", "36", "21"],
            correct_answer="27",
            explanation="9 multiplied by 3 is 27.",
            points=1,
        ),
        Question(
            qid="Q3",
            prompt="What is 20 - 6?",
            options=["12", "13", "14", "15"],
            correct_answer="14",
            explanation="20 - 6 = 14.",
            points=1,
        ),
    ]


def parse_uploaded_questions(raw_text: str) -> list[Question]:
    data = json.loads(raw_text)
    questions: list[Question] = []

    for item in data:
        questions.append(
            Question(
                qid=str(item["qid"]),
                prompt=str(item["prompt"]),
                options=[str(opt) for opt in item["options"]],
                correct_answer=str(item["correct_answer"]),
                explanation=str(item.get("explanation", "")),
                points=int(item.get("points", 1)),
            )
        )

    return questions


def render_ocr_extraction_panel(image_bytes: bytes | None) -> None:
    st.subheader("Auto Detect Questions (OCR)")
    st.caption("Extract printed MCQ questions and options from worksheet image.")

    if "ocr_questions" not in st.session_state:
        st.session_state["ocr_questions"] = []

    if image_bytes is None:
        st.info("Capture or upload worksheet image first.")
        return

    if st.button("Extract Questions from Image", type="secondary"):
        with st.spinner("Running OCR and parsing questions..."):
            try:
                questions = load_ocr_questions_from_image(image_bytes)
            except Exception as exc:
                st.error(f"OCR failed: {exc}")
                st.session_state["ocr_questions"] = []
                return

        if not questions:
            st.warning("No MCQ questions detected. Try a clearer image.")
            st.session_state["ocr_questions"] = []
            return

        st.session_state["ocr_questions"] = questions
        st.success(f"Detected {len(questions)} questions.")

    if st.session_state["ocr_questions"]:
        with st.expander("Preview extracted questions"):
            st.json(st.session_state["ocr_questions"])


def get_questions_source() -> str:
    with st.sidebar:
        st.header("Worksheet Source")
        options = ["Use demo worksheet", "Upload JSON worksheet"]
        if st.session_state.get("ocr_questions"):
            options.append("Use OCR worksheet")

        return st.radio("Choose input mode", options)


def get_questions_from_json_upload() -> list[Question]:
    with st.sidebar:
        file = st.file_uploader("Upload a JSON file", type=["json"])
    if file is None:
        st.info("Upload a file or switch source mode.")
        return []

    text = file.read().decode("utf-8")
    try:
        questions = parse_uploaded_questions(text)
    except Exception as exc:
        st.error(f"Invalid JSON format: {exc}")
        return []

    if not questions:
        st.error("No questions found in file.")
        return []

    return questions


def get_questions_from_ocr() -> list[Question]:
    data = st.session_state.get("ocr_questions", [])
    if not data:
        st.info("No OCR worksheet available yet. Extract questions first.")
        return []

    st.subheader("Set Answer Key for OCR Questions")
    st.caption("Choose the correct option for each detected question before grading.")

    questions: list[Question] = []
    for item in data:
        qid = str(item["qid"])
        prompt = str(item["prompt"])
        options = [str(opt) for opt in item["options"]]
        if len(options) < 2:
            continue

        with st.container(border=True):
            st.markdown(f"### {qid}: {prompt}")
            correct_answer = st.selectbox(
                "Choose correct option",
                options,
                key=f"key_{qid}",
            )
            explanation = st.text_input(
                "Explanation for incorrect answers",
                key=f"exp_{qid}",
                placeholder="Example: 7 + 5 = 12",
            )
            points = st.number_input(
                "Points",
                min_value=1,
                max_value=10,
                value=1,
                step=1,
                key=f"pts_{qid}",
            )

        questions.append(
            Question(
                qid=qid,
                prompt=prompt,
                options=options,
                correct_answer=correct_answer,
                explanation=explanation,
                points=int(points),
            )
        )

    if not questions:
        st.warning("OCR detected data is incomplete.")

    return questions


def resolve_questions(source: str) -> list[Question]:
    if source == "Use demo worksheet":
        return load_default_questions()
    if source == "Upload JSON worksheet":
        return get_questions_from_json_upload()
    if source == "Use OCR worksheet":
        return get_questions_from_ocr()
    return []


def render_report_downloads(result) -> None:
    st.subheader("Export Report")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_bytes = sheet_result_to_csv_bytes(result)
    pdf_bytes = sheet_result_to_pdf_bytes(result)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"worksheet_report_{timestamp}.csv",
            mime="text/csv",
            key="download_csv_report",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"worksheet_report_{timestamp}.pdf",
            mime="application/pdf",
            key="download_pdf_report",
            use_container_width=True,
        )


def render_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700&family=Nunito:wght@500;700&display=swap');

        :root {
            --page-bg-1: #f6fbff;
            --page-bg-2: #eef7ea;
            --page-bg-3: #fff6e6;
            --surface: rgba(255, 255, 255, 0.96);
            --surface-strong: #ffffff;
            --text-main: #112b35;
            --text-muted: #35515a;
            --accent: #0d7a6f;
            --accent-strong: #0a5f57;
            --border: #c7d8de;
            --sidebar-bg: rgba(248, 252, 255, 0.98);
            --warning-bg: #fff8d8;
        }

        .stApp {
            background: linear-gradient(135deg, var(--page-bg-1) 0%, var(--page-bg-2) 45%, var(--page-bg-3) 100%);
            font-family: 'Nunito', sans-serif;
            color: var(--text-main);
        }

        .block-container {
            max-width: 980px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        .stApp, .stApp p, .stApp label, .stApp span, .stApp div {
            color: var(--text-main);
        }

        .stCaptionContainer, .stMarkdown p, .stMarkdown li, .stText, .stAlert {
            color: var(--text-main);
        }

        [data-testid="stSidebar"] {
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * {
            color: var(--text-main);
        }

        h1, h2, h3 {
            font-family: 'Baloo 2', cursive;
            color: var(--text-main);
            letter-spacing: 0.3px;
        }

        h1 {
            font-size: clamp(2rem, 5vw, 3.1rem);
        }

        h2, h3 {
            line-height: 1.2;
        }

        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stExpander"],
        [data-testid="stFileUploader"],
        [data-testid="stImage"],
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 18px;
            box-shadow: 0 10px 24px rgba(17, 43, 53, 0.06);
        }

        .result-card {
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.75rem;
            background: var(--surface-strong);
            border: 1px solid var(--border);
            box-shadow: 0 10px 24px rgba(17, 43, 53, 0.08);
            color: var(--text-main);
        }

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        textarea,
        input {
            background: var(--surface-strong) !important;
            color: var(--text-main) !important;
            border-color: var(--border) !important;
        }

        [data-baseweb="radio"] label,
        [data-baseweb="radio"] div,
        [role="radiogroup"] label,
        [role="radiogroup"] span {
            color: var(--text-main) !important;
        }

        [data-testid="stAlert"] {
            background: var(--warning-bg);
            color: var(--text-main);
            border: 1px solid #e6cf7a;
        }

        button[kind="primary"], button[kind="secondary"] {
            border-radius: 999px;
            min-height: 46px;
            font-weight: 700;
            border: none !important;
        }

        button[kind="primary"] {
            background: var(--accent) !important;
            color: #ffffff !important;
        }

        button[kind="secondary"] {
            background: #e8f4f2 !important;
            color: var(--accent-strong) !important;
            border: 1px solid #b8d8d2 !important;
        }

        button[kind="primary"]:hover,
        button[kind="secondary"]:hover {
            filter: brightness(0.97);
        }

        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"] {
            color: var(--text-main) !important;
        }

        .stDownloadButton button {
            width: 100%;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }

            [data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }

            .result-card {
                padding: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Math Worksheet Checker", page_icon="🧮", layout="wide")
    render_styles()

    st.title("Math Worksheet Checker")
    st.caption(
        "Upload worksheet questions, enter student responses, and get fair scoring with explanations."
    )
    render_camera_permission_notice()

    image_bytes = render_mobile_worksheet_capture()
    render_ocr_extraction_panel(image_bytes)

    source = get_questions_source()
    questions = resolve_questions(source)
    if not questions:
        st.stop()

    st.subheader("Student Answer Entry")

    answers: dict[str, StudentAnswer] = {}

    for q in questions:
        with st.container(border=True):
            st.markdown(f"### {q.qid}: {q.prompt}")

            all_options = q.options + [NO_ANSWER, OUT_OF_OPTIONS]
            selected = st.radio(
                "Select student answer",
                all_options,
                index=len(q.options),
                key=f"ans_{q.qid}",
                horizontal=True,
            )

            typed_answer = ""
            resolution = OUT_OF_OPTIONS_MARK_INCORRECT

            if selected == OUT_OF_OPTIONS:
                typed_answer = st.text_input(
                    "Student's actual answer (optional)",
                    key=f"typed_{q.qid}",
                    placeholder="Example: 22",
                )
                resolution = st.radio(
                    "How should this be graded?",
                    options=[OUT_OF_OPTIONS_MARK_INCORRECT, OUT_OF_OPTIONS_MARK_ISSUE],
                    key=f"resolve_{q.qid}",
                    format_func=lambda x: "Incorrect (strict MCQ)"
                    if x == OUT_OF_OPTIONS_MARK_INCORRECT
                    else "Question issue (exclude from score)",
                )

            answers[q.qid] = StudentAnswer(
                selected_option=selected,
                typed_answer=typed_answer,
                out_of_options_resolution=resolution,
            )

    if st.button("Grade Worksheet", type="primary"):
        result = grade_sheet(questions, answers)

        st.subheader("Score Summary")
        strict_pct = (
            (result.score_correct / result.score_possible_strict) * 100
            if result.score_possible_strict > 0
            else 0.0
        )
        adjusted_pct = (
            (result.score_correct / result.score_possible_excluding_issues) * 100
            if result.score_possible_excluding_issues > 0
            else 0.0
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Strict Score",
                f"{result.score_correct}/{result.score_possible_strict}",
                help="Includes all questions in denominator.",
            )
            st.metric("Strict Percentage", f"{strict_pct:.1f}%")

        with col2:
            st.metric(
                "Adjusted Score",
                f"{result.score_correct}/{result.score_possible_excluding_issues}",
                help="Excludes question issue items from denominator.",
            )
            st.metric("Adjusted Percentage", f"{adjusted_pct:.1f}%")

        st.write(
            {
                "Correct": result.correct_count,
                "Incorrect": result.incorrect_count,
                "Unattempted": result.unattempted_count,
                "Question issue": result.question_issue_count,
            }
        )

        st.subheader("Question-by-Question Report")
        for row in result.question_results:
            st.markdown(
                f"""
                <div class="result-card">
                <strong>{row.qid}</strong><br/>
                Status: <strong>{row.status}</strong><br/>
                Points: {row.points_earned}/{row.points_possible}<br/>
                Feedback: {row.feedback}
                </div>
                """,
                unsafe_allow_html=True,
            )

            render_report_downloads(result)

    with st.expander("JSON worksheet format"):
        st.code(
            json.dumps(
                [
                    {
                        "qid": "Q1",
                        "prompt": "What is 4 + 6?",
                        "options": ["8", "9", "10", "11"],
                        "correct_answer": "10",
                        "explanation": "4 + 6 = 10",
                        "points": 1,
                    }
                ],
                indent=2,
            ),
            language="json",
        )


if __name__ == "__main__":
    main()
