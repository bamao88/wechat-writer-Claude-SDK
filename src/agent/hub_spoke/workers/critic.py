"""Critic Agent for hub-spoke architecture.

The Critic performs rule-based quality checks on the draft article:
1. Word count check (≥800 chars)
2. Structure completeness (title, sections, paragraphs, conclusion)
3. Outline alignment (key points from outline appear in draft)

This is a pure code-based checker, does NOT call LLM.
"""
import re
from dataclasses import dataclass
from typing import List

from src.agent.hub_spoke.state import State
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Quality thresholds
MIN_WORD_COUNT = 800
PASS_SCORE_THRESHOLD = 8  # 提高通过线：需≥8分，确保论点覆盖充分


@dataclass
class CriticResult:
    """Result from Critic quality check.

    Attributes:
        score: Quality score (0-10)
        passed: Whether article passed quality check (score ≥7)
        reason: Detailed reason for the score
    """
    score: int
    passed: bool
    reason: str


class CriticWorker:
    """Critic agent that performs rule-based quality checks.

    This agent does NOT call LLM. It uses pure Python logic to check:
    - Word count
    - Structure completeness
    - Outline key points coverage

    Scoring:
    - Start with 10 points
    - Deduct points for each issue found
    - Pass threshold: ≥7 points
    """

    def __init__(self):
        """Initialize Critic worker."""
        pass

    def _check_word_count(self, draft: str) -> tuple[int, str]:
        """Check if draft meets minimum word count.

        Args:
            draft: Draft article text

        Returns:
            (deduction, reason) tuple
            deduction: Points to deduct (0-3)
            reason: Reason for deduction
        """
        char_count = len(draft.strip())

        if char_count == 0:
            return (10, "文章为空")

        if char_count < MIN_WORD_COUNT:
            shortage = MIN_WORD_COUNT - char_count
            deduction = min(3, int(shortage / 300) + 1)  # 1-3 points based on shortage
            return (deduction, f"字数不足（当前{char_count}字，要求≥{MIN_WORD_COUNT}字）")

        return (0, "")

    def _check_structure(self, draft: str) -> tuple[int, str]:
        """Check if draft has complete structure.

        Checks for:
        - Title (# or ##)
        - Multiple sections/paragraphs
        - Reasonable content distribution

        Args:
            draft: Draft article text

        Returns:
            (deduction, reason) tuple
        """
        issues = []
        deduction = 0

        # Check for title
        if not re.search(r'^#\s+.+', draft, re.MULTILINE):
            issues.append("缺少标题")
            deduction += 2

        # Check for sections (## headers)
        sections = re.findall(r'^##\s+.+', draft, re.MULTILINE)
        if len(sections) < 2:
            issues.append("缺少足够的章节结构（建议≥2个小节）")
            deduction += 1

        # Check for paragraphs
        paragraphs = [p for p in draft.split('\n\n') if len(p.strip()) > 50]
        if len(paragraphs) < 3:
            issues.append("段落数量不足（建议≥3个实质段落）")
            deduction += 1

        if issues:
            return (deduction, "结构不完整：" + "；".join(issues))

        return (0, "")

    def _extract_key_points(self, outline: str) -> List[str]:
        """Extract key points from outline.

        Looks for:
        - Lines starting with - or *
        - Section headers (##)
        - Numbered items (1. 2. etc)

        Args:
            outline: Outline text

        Returns:
            List of key point strings (lowercased for matching)
        """
        points = []

        # Extract bullet points (- or *)
        # Fixed regex: put - at the end to avoid range interpretation
        bullet_points = re.findall(r'^[\s*-]+(.+)$', outline, re.MULTILINE)
        points.extend(bullet_points)

        # Extract section headers (##)
        headers = re.findall(r'^##\s+(.+)$', outline, re.MULTILINE)
        points.extend(headers)

        # Extract numbered items
        numbered = re.findall(r'^\d+\.\s+(.+)$', outline, re.MULTILINE)
        points.extend(numbered)

        # Clean and filter
        cleaned_points = []
        for p in points:
            p = p.strip()
            # Remove common markdown/formatting
            p = re.sub(r'[#*\[\]()（）]', '', p)
            p = p.strip()
            if len(p) > 2:  # At least 3 chars
                cleaned_points.append(p)

        return cleaned_points

    def _check_outline_alignment(self, draft: str, outline: str) -> tuple[int, str]:
        """Check if outline key points appear in draft.

        Args:
            draft: Draft article text
            outline: Outline text

        Returns:
            (deduction, reason) tuple
        """
        if not outline or len(outline.strip()) < 10:
            # No meaningful outline provided, skip this check
            return (0, "")

        key_points = self._extract_key_points(outline)

        if len(key_points) == 0:
            # No key points found in outline
            return (0, "")

        missing_points = []
        for point in key_points:
            # Check if point appears in draft (case-insensitive, flexible matching)
            if point not in draft:
                missing_points.append(point)

        if missing_points:
            missing_ratio = len(missing_points) / len(key_points)
            if missing_ratio >= 0.5:
                # More than half missing
                deduction = 3
                reason = f"大纲核心论点缺失严重（{len(missing_points)}/{len(key_points)}个论点未体现）"
            elif missing_ratio >= 0.3:
                deduction = 2
                reason = f"部分大纲论点未充分体现（{len(missing_points)}/{len(key_points)}个论点缺失）"
            else:
                deduction = 1
                reason = f"少量大纲论点未体现（{len(missing_points)}/{len(key_points)}个论点缺失）"

            return (deduction, reason)

        return (0, "")

    def run(self, state: State) -> CriticResult:
        """Execute Critic quality check.

        Args:
            state: Current State object (reads draft, outline)

        Returns:
            CriticResult with score, passed, reason
        """
        draft = state.draft
        outline = state.outline

        # Start with perfect score
        score = 10
        reasons = []

        try:
            # Check 1: Word count
            word_deduction, word_reason = self._check_word_count(draft)
            if word_deduction > 0:
                score -= word_deduction
                reasons.append(word_reason)

            # Check 2: Structure
            struct_deduction, struct_reason = self._check_structure(draft)
            if struct_deduction > 0:
                score -= struct_deduction
                reasons.append(struct_reason)

            # Check 3: Outline alignment
            outline_deduction, outline_reason = self._check_outline_alignment(draft, outline)
            if outline_deduction > 0:
                score -= outline_deduction
                reasons.append(outline_reason)

            # Ensure score is in valid range
            score = max(0, min(10, score))

            # Determine pass/fail
            passed = score >= PASS_SCORE_THRESHOLD

            # Build reason string
            if passed:
                reason = f"质量检查通过（评分：{score}/10）"
                if reasons:
                    reason += f"。改进建议：{' '.join(reasons)}"
            else:
                reason = f"质量未达标（评分：{score}/10）。问题：{' '.join(reasons)}"

            logger.info(f"Critic result: score={score}, passed={passed}")

            return CriticResult(
                score=score,
                passed=passed,
                reason=reason
            )

        except Exception as e:
            logger.error(f"Critic execution error: {e}", exc_info=True)

            # Fallback: fail with error
            return CriticResult(
                score=0,
                passed=False,
                reason=f"质量检查出错：{str(e)}"
            )
