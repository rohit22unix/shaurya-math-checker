from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

STATUS_CORRECT = "Correct"
STATUS_INCORRECT = "Incorrect"
STATUS_UNATTEMPTED = "Unattempted"
STATUS_QUESTION_ISSUE = "Question issue"

OUT_OF_OPTIONS_MARK_INCORRECT = "incorrect"
OUT_OF_OPTIONS_MARK_ISSUE = "issue"


@dataclass
class Question:
    qid: str
    prompt: str
    options: list[str]
    correct_answer: str
    explanation: str
    points: int = 1


@dataclass
class StudentAnswer:
    selected_option: str
    typed_answer: str = ""
    out_of_options_resolution: str = OUT_OF_OPTIONS_MARK_INCORRECT


@dataclass
class QuestionResult:
    qid: str
    status: str
    points_earned: int
    points_possible: int
    feedback: str


@dataclass
class SheetResult:
    question_results: list[QuestionResult]
    total_questions: int
    correct_count: int
    incorrect_count: int
    unattempted_count: int
    question_issue_count: int
    score_correct: int
    score_possible_strict: int
    score_possible_excluding_issues: int


NO_ANSWER = "No answer selected"
OUT_OF_OPTIONS = "Answer not in options"


def evaluate_question(question: Question, answer: StudentAnswer) -> QuestionResult:
    if answer.selected_option == NO_ANSWER:
        return QuestionResult(
            qid=question.qid,
            status=STATUS_UNATTEMPTED,
            points_earned=0,
            points_possible=question.points,
            feedback="No answer selected by student.",
        )

    if answer.selected_option == OUT_OF_OPTIONS:
        if answer.out_of_options_resolution == OUT_OF_OPTIONS_MARK_ISSUE:
            return QuestionResult(
                qid=question.qid,
                status=STATUS_QUESTION_ISSUE,
                points_earned=0,
                points_possible=question.points,
                feedback=(
                    "Marked as question issue. Student claims answer is outside options. "
                    f"Typed answer: '{answer.typed_answer.strip() or 'N/A'}'."
                ),
            )

        return QuestionResult(
            qid=question.qid,
            status=STATUS_INCORRECT,
            points_earned=0,
            points_possible=question.points,
            feedback=(
                "Answer was outside given options, and this question was set to be "
                "graded strictly as MCQ. "
                f"Correct option: {question.correct_answer}. {question.explanation}"
            ),
        )

    if answer.selected_option == question.correct_answer:
        return QuestionResult(
            qid=question.qid,
            status=STATUS_CORRECT,
            points_earned=question.points,
            points_possible=question.points,
            feedback="Correct answer.",
        )

    return QuestionResult(
        qid=question.qid,
        status=STATUS_INCORRECT,
        points_earned=0,
        points_possible=question.points,
        feedback=(
            f"Selected '{answer.selected_option}', but correct answer is "
            f"'{question.correct_answer}'. {question.explanation}"
        ),
    )


def grade_sheet(questions: list[Question], answers: dict[str, StudentAnswer]) -> SheetResult:
    results: list[QuestionResult] = []

    for question in questions:
        answer = answers.get(question.qid, StudentAnswer(selected_option=NO_ANSWER))
        results.append(evaluate_question(question, answer))

    correct_count = sum(1 for r in results if r.status == STATUS_CORRECT)
    incorrect_count = sum(1 for r in results if r.status == STATUS_INCORRECT)
    unattempted_count = sum(1 for r in results if r.status == STATUS_UNATTEMPTED)
    question_issue_count = sum(1 for r in results if r.status == STATUS_QUESTION_ISSUE)

    score_correct = sum(r.points_earned for r in results)
    score_possible_strict = sum(r.points_possible for r in results)
    score_possible_excluding_issues = sum(
        r.points_possible for r in results if r.status != STATUS_QUESTION_ISSUE
    )

    return SheetResult(
        question_results=results,
        total_questions=len(questions),
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unattempted_count=unattempted_count,
        question_issue_count=question_issue_count,
        score_correct=score_correct,
        score_possible_strict=score_possible_strict,
        score_possible_excluding_issues=score_possible_excluding_issues,
    )
