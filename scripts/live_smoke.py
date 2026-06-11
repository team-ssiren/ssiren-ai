"""라이브 스모크 — 실제 OpenAI 호출로 ①분석·③챗봇 골든셋 검증.

비용이 드는 실호출이므로 단위 테스트와 분리. 실행:
    uv run python scripts/live_smoke.py
"""
# ruff: noqa: E402, E501  (dev script: path bootstrap before imports + wide print lines)

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.taxonomy import parent_of
from app.schemas.chatbot import (
    ChatAnswerRequest,
    ChatContext,
    ChatPlanRequest,
    ContextReport,
)
from app.services import chatbot
from app.services.analyzer import AnalyzeInput, ImageInput, analyze

# 준비된 멀티모달 픽스처 디렉터리 (manhall.json/.jpg, waste.json/.jpg).
FIXTURE_DIR = Path(os.environ.get("SSAIKA_DIR", r"C:/Users/hurwy/Downloads/SSAIKA"))

# (설명, 픽스처 stem, 기대 majorCode, 기대 minorCode)
FIXTURE_CASES = [
    ("맨홀 파손(분당 판교)", "manhall", "INFRASTRUCTURE_ROAD", "MANHOLE_DRAIN_DAMAGE"),
    ("길거리 쓰레기(분당 판교)", "waste", "LIVING_INCONVENIENCE", "WASTE_AND_DEBRIS"),
]

# (설명, 입력 텍스트, 기대 minorCode, 기대 긴급여부) — 텍스트 전용 골든셋(분당 좌표).
ANALYZE_CASES = [
    ("불법주정차", "횡단보도 앞에 차가 계속 서 있어서 길 건너기 위험해요", "ILLEGAL_PARKING", False),
    ("도로파손", "인도가 심하게 깨져 있어서 어제 발이 걸려 넘어질 뻔했어요", "ROAD_DAMAGE", False),
    ("주취자(→치안)", "술 취한 사람이 길에 누워서 소리지르고 있어요", "INTOXICATED_PERSON_CONCERN", False),
    ("긴급(화재)", "건물에서 연기가 막 나고 불이 보여요!! 사람들이 대피하고 있어요", "FIRE_RISK", True),
    ("제보 불성립", "ㅋㅋㅋ 심심해서 그냥 써봄 아무것도 아님", "INSUFFICIENT", False),
]


def _print_resp(label, expect_major, expect_minor, resp):
    major = resp.category.majorCode.value
    minor = resp.category.categoryCode.value
    ok_major = "✅" if (expect_major is None or major == expect_major) else "❌"
    ok_minor = "✅" if (expect_minor is None or minor == expect_minor) else "❌"
    r = resp.resolvedAgency
    print(f"\n[{label}] 기대={expect_major}/{expect_minor}")
    print(f"  title       : {resp.title}")
    print(f"  major       : {ok_major} {major}")
    print(f"  minor       : {ok_minor} {minor} (conf={resp.category.confidence})")
    print(f"  riskScore   : {resp.riskScore}")
    print(f"  suggested   : {resp.suggestedAgencyType} / {resp.suggestedDepartment}")
    print(f"  resolved    : {r.name} / {r.department} / {r.phone}")
    print(f"  emergency   : {resp.analysis.emergencyGuide.isEmergency} msg={resp.analysis.emergencyGuide.message}")
    print(f"  embedding   : dim={len(resp.embedding)}")


async def run_fixtures():
    print("=" * 70)
    print("① ANALYZE (multimodal fixtures → resolved agency)")
    print("=" * 70)
    for label, stem, expect_major, expect_minor in FIXTURE_CASES:
        meta_path = FIXTURE_DIR / f"{stem}.json"
        img_path = FIXTURE_DIR / f"{stem}.jpg"
        if not meta_path.exists() or not img_path.exists():
            print(f"\n[{label}] ⚠️  픽스처 없음: {meta_path} / {img_path}")
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        resp = await analyze(
            AnalyzeInput(
                content=meta["content"],
                latitude=meta["latitude"],
                longitude=meta["longitude"],
                occurred_at=meta.get("occurredAt"),
                road_address=meta.get("roadAddress"),
                sido=meta.get("sido"),
                sigungu=meta.get("sigungu"),
                eupmyeondong=meta.get("eupmyeondong"),
                images=[ImageInput(data=img_path.read_bytes(), content_type="image/jpeg")],
            )
        )
        _print_resp(label, expect_major, expect_minor, resp)


async def run_analyze():
    print("\n" + "=" * 70)
    print("① ANALYZE (text-only golden set, 분당)")
    print("=" * 70)
    for label, text, expect_code, expect_emergency in ANALYZE_CASES:
        resp = await analyze(
            AnalyzeInput(
                content=text,
                latitude=37.3826,
                longitude=127.1189,
                road_address="경기 성남시 분당구 성남대로 997",
                sido="경기도",
                sigungu="성남시 분당구",
                eupmyeondong="서현동",
            )
        )
        code = resp.category.categoryCode.value
        ok_code = "✅" if code == expect_code else "❌"
        ok_emg = "✅" if resp.analysis.emergencyGuide.isEmergency == expect_emergency else "❌"
        print(f"\n[{label}] 기대={expect_code}")
        print(f"  category    : {ok_code} {code} (parent={parent_of(code).value}, conf={resp.category.confidence})")
        print(f"  emergency   : {ok_emg} {resp.analysis.emergencyGuide.isEmergency}")
        print(f"  resolved    : {resp.resolvedAgency.name} / {resp.resolvedAgency.department}")


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
    await run_fixtures()
    await run_analyze()
    await run_chatbot()


if __name__ == "__main__":
    asyncio.run(main())
