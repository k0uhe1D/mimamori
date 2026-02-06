"""OpenAI GPT-4o Vision API client for newborn analysis."""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from src.analyzer.models import AnalysisResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは新生児モニタリングの専門家です。
カメラで撮影された新生児の画像を分析し、以下の情報をJSON形式で返してください。

{
  "posture": "仰向け / うつ伏せ / 横向き / 不明",
  "sleep_state": "睡眠中 / 覚醒 / 不明",
  "actions": ["観察された赤ちゃんの詳細な動作・状態のリスト"],
  "anomalies": ["検知された異常のリスト(なければ空配列)"],
  "summary": "総合的な状態の要約(1-2文)",
  "confidence": "high / medium / low"
}

actionsの記載例:
- "右手を挙げている", "左手を握っている", "両手をバタバタさせている"
- "あくびをしている", "口を動かしている", "指をしゃぶっている"
- "足をバタバタさせている", "体を反っている", "頭を横に向けている"
- "目を開けている", "泣いている表情", "笑顔のような表情"
- "おくるみに包まれている", "布団を蹴っている"
観察できる動作や状態をできるだけ具体的に記載してください。
何も観察できない場合は空配列にしてください。

重要な注意事項:
- うつ伏せ姿勢は危険です。検知した場合はanomaliesに必ず含めてください。
- 顔が見えない場合や布団で覆われている場合もanomaliesに含めてください。
- JSON以外のテキストを含めないでください。
"""


def analyze_frame(
    base64_image: str,
    api_key: str,
    model: str = "gpt-4o",
) -> AnalysisResult:
    """Analyze a single frame using OpenAI GPT-4o Vision API.

    Args:
        base64_image: Base64-encoded JPEG image string.
        api_key: OpenAI API key.
        model: OpenAI model name to use.

    Returns:
        AnalysisResult with parsed analysis data.
    """
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low",
                        },
                    },
                ],
            },
        ],
        max_tokens=500,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content or ""
    logger.debug("Raw LLM response: %s", raw_text)

    try:
        data: dict[str, object] = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON: %s", raw_text)
        return AnalysisResult.create_now(
            posture="不明",
            sleep_state="不明",
            summary=raw_text,
            confidence="low",
            raw_response=raw_text,
            anomalies=["LLM応答のJSON解析に失敗"],
        )

    anomalies_raw = data.get("anomalies", [])
    anomalies = anomalies_raw if isinstance(anomalies_raw, list) else []
    actions_raw = data.get("actions", [])
    actions = actions_raw if isinstance(actions_raw, list) else []

    return AnalysisResult.create_now(
        posture=str(data.get("posture", "不明")),
        sleep_state=str(data.get("sleep_state", "不明")),
        summary=str(data.get("summary", "")),
        confidence=str(data.get("confidence", "low")),
        raw_response=raw_text,
        anomalies=[str(a) for a in anomalies],
        actions=[str(a) for a in actions],
    )
