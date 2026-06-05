"""라이브 스모크 — 실제 OpenAI 호출로 ①분석·③챗봇 골든셋 검증.

비용이 드는 실호출이므로 단위 테스트와 분리. 실행:
    uv run python scripts/live_smoke.py
"""
# ruff: noqa: E402, E501  (dev script: path bootstrap before imports + wide print lines)

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.taxonomy import parent_of
from app.schemas.chatbot import (
    ChatAnswerRequest,
    ChatContext,
    ChatPlanRequest,
    ContextReport,
)
from app.services import chatbot
from app.services.analyzer import AnalyzeInput, analyze

# (설명, 입력 텍스트, 기대 categoryCode, 기대 긴급여부)
ANALYZE_CASES = [
    ("불법주정차", "횡단보도 앞에 차가 계속 서 있어서 길 건너기 위험해요", "ILLEGAL_PARKING", False),
    ("도로파손", "둔산동 인도가 심하게 깨져 있어서 어제 발이 걸려 넘어질 뻔했어요", "ROAD_DAMAGE", False),
    ("동물사체(타이브레이크→환경)", "도로 위에 고양이 사체가 있어요. 차들이 피해서 지나가요", "ANIMAL_CARCASS", False),
    ("주취자(타이브레이크→치안)", "술 취한 사람이 길에 누워서 소리지르고 있어요", "DRUNK_PERSON", False),
    ("긴급(화재)", "건물에서 연기가 막 나고 불이 보여요!! 사람들이 대피하고 있어요", "FIRE_EMERGENCY", True),
    ("허위/무관", "ㅋㅋㅋ 심심해서 그냥 써봄 아무것도 아님", "ETC_OTHER", False),
]


async def run_analyze():
    print("=" * 70)
    print("① ANALYZE (text-only golden set)")
    print("=" * 70)
    for label, text, expect_code, expect_emergency in ANALYZE_CASES:
        resp = await analyze(
            AnalyzeInput(
                content=text,
                latitude=36.3519,
                longitude=127.3785,
                road_address="대전광역시 서구 둔산로 1036",
                sido="대전광역시",
                sigungu="서구",
                eupmyeondong="둔산동",
            )
        )
        code = resp.category.categoryCode.value
        ok_code = "✅" if code == expect_code else "❌"
        ok_emg = "✅" if resp.analysis.emergencyGuide.isEmergency == expect_emergency else "❌"
        print(f"\n[{label}] 기대={expect_code}")
        print(f"  title       : {resp.title}")
        print(f"  category    : {ok_code} {code} (parent={parent_of(code).value}, conf={resp.category.confidence})")
        print(f"  riskScore   : {resp.riskScore}")
        print(f"  falseReport : suspicious={resp.analysis.falseReport.isSuspicious} score={resp.analysis.falseReport.score}")
        print(f"  emergency   : {ok_emg} {resp.analysis.emergencyGuide.isEmergency}  msg={resp.analysis.emergencyGuide.message}")
        print(f"  detected    : {resp.analysis.detectedObjects}")
        print(f"  embedding   : dim={len(resp.embedding)}")


async def run_chatbot():
    print("\n" + "=" * 70)
    print("③ CHATBOT plan / answer")
    print("=" * 70)

    plan_cases = [
        ("잡담→ANSWER_DIRECT", "안전신문고랑 싸이렌은 뭐가 달라?"),
        ("근처→SEARCH_NEARBY", "이 근처에 위험한 제보 있어?"),
        ("내제보→MY_REPORTS", "내가 신고한 거 처리됐어?"),
    ]
    for label, q in plan_cases:
        out = await chatbot.plan(ChatPlanRequest(question=q))
        print(f"\n[{label}] Q={q}")
        print(f"  action={out.action.value} params={out.params.model_dump()} answer={out.answer!r}")

    # answer — grounded (with reports)
    print("\n[answer · with context]")
    grounded = await chatbot.answer(
        ChatAnswerRequest(
            question="이 근처 위험한 제보 있어?",
            context=ChatContext(
                scope="SEARCH_NEARBY",
                reports=[
                    ContextReport(
                        reportId=15,
                        title="궁동 도로 파손",
                        summary="도로 파손으로 통행 위험",
                        category="도로 파손",
                        address="유성구 궁동",
                        riskScore=66.0,
                        distanceMeters=120.0,
                    )
                ],
            ),
        )
    )
    print(f"  answer={grounded.answer!r}")
    print(f"  usedReportIds={grounded.usedReportIds}")

    # answer — empty context (no hallucination)
    print("\n[answer · empty context]")
    empty = await chatbot.answer(
        ChatAnswerRequest(
            question="이 근처 위험한 제보 있어?",
            context=ChatContext(scope="SEARCH_NEARBY", reports=[]),
        )
    )
    print(f"  answer={empty.answer!r}")
    print(f"  usedReportIds={empty.usedReportIds}")


async def main():
    await run_analyze()
    await run_chatbot()


if __name__ == "__main__":
    asyncio.run(main())
