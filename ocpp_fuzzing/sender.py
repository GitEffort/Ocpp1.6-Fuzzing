# 02_replay_sender.py (readability-focused, classic style)

import os
import json
import uuid
import argparse
import asyncio
import csv
from pathlib import Path

import websockets

DEFAULT_URI = "ws://127.0.0.1:9000/CP_REPLAY"
DEFAULT_SUBPROTOCOLS = ["ocpp1.6"]
RECV_TIMEOUT_SEC = 8          # 서버 응답 대기 타임아웃(초)
CSV_DEFAULT_PATH = "replay_result.csv"
UID_PLACEHOLDER = "$UID$"
FRAME_MIN_FIELDS = 3          # [msgTypeId, uniqueId, action, ...] 최소 3개

def iter_input_records(input_path):
    """
        @param input_path: JSON 파일/JSONL/디렉터리 경로
        @return: (Path(표시용), parsed JSON 객체) 튜플을 생성하는 Generatpor
        @note: Path(표시용)는 JSONL인 경우 "파일명:라인번호" 형태
    """
    p = Path(input_path)

    if p.is_dir():
        for json_path in sorted(p.glob("*.json")):
            yield json_path, json.loads(json_path.read_text(encoding="utf-8"))

    else:
        if p.suffix.lower() == ".jsonl":
            with p.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    display_name = Path(f"{p.name}:{line_no}")
                    yield display_name, json.loads(line)
        else:
            yield p, json.loads(p.read_text(encoding="utf-8"))


def replace_uid_if_enabled(frame, enable_replace):
    """
        @param frame: OCPP 메시지 프레임
        @param enable_replace: uniqueId 교체 여부
        @return: uniqueId가 교체된 새 프레임 (원본은 변경 안 함)
        @note: uniqueId가 "$UID$"이거나 문자열이면 새 uuid4로 교체
    """
    if not enable_replace:
        return frame

    # list로 강제 복사 (tuple 등도 list로 변환)
    new_frame = list(frame)
    if len(new_frame) >= 2:
        if new_frame[1] == UID_PLACEHOLDER or isinstance(new_frame[1], str):
            new_frame[1] = str(uuid.uuid4())
    return new_frame


def classify_response(resp):
    """
        @param resp: send_frame_and_receive() 반환값
        @return: 분류 문자열
        - CallResult   : "CallResult"
        - CallError    : "CallError:<errorCode>" 또는 "CallError"
        - 그외         : str(resp) (ex: "TIMEOUT", "CLOSED:<code>", "EXC:<msg>")
    """
    if isinstance(resp, list) and len(resp) >= 1:
        if resp[0] == 3:
            return "CallResult"
        if resp[0] == 4:
            try:
                return f"CallError:{resp[2]}"
            except Exception:
                return "CallError"
    return str(resp)


async def send_frame_and_receive(ws, frame, timeout=RECV_TIMEOUT_SEC):
    """
        @param ws:  websockets 연결 객체
        @param frame: 전송할 OCPP 메시지 프레임 (list)
        @param timeout: 응답 대기 타임아웃(초)
        @return: 서버 응답(CallResult/CallError) 또는 예외 상황 문자열

        @note:  서버 응답이 없을 경우 : TIMEOUT
                연결이 닫힐 경우 : CLOSED:<code>
                그 외 예외 : EXC:<msg>
    """
    try:
        await ws.send(json.dumps(frame))
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        return json.loads(raw)
    except asyncio.TimeoutError:
        return "TIMEOUT"
    except websockets.ConnectionClosed as e:
        return f"CLOSED:{e.code}"
    except Exception as e:
        return f"EXC:{e}"


async def main():
    """
        @note:
        - --input : (JSON 파일/JSONL/디렉터리) 입력
        - --replace-uid : uniqueId 교체
        - --csv : (결과 CSV 경로) 출력
        - --uri : WebSocket 서버
        - --subp : WebSocket subprotocols (기본: ocpp1.6)
        - --timeout : 서버 응답 타임아웃(초, 기본 8초)
        - CSV 컬럼: input, result
        - result: CallResult, CallError:<errorCode>, CallError, TIMEOUT, CLOSED:<code>, EXC:<msg>
    """
    parser = argparse.ArgumentParser(description="Replay OCPP JSON files to server.")
    parser.add_argument("--input", required=True, help="JSON 파일/JSONL/디렉터리 경로")
    parser.add_argument("--replace-uid", action="store_true",
                        help="uniqueId를 실행 시 새 uuid4로 교체")
    parser.add_argument("--csv", default=CSV_DEFAULT_PATH, help="결과 CSV 경로")
    parser.add_argument("--uri", default=DEFAULT_URI, help="WebSocket 서버 URI")
    parser.add_argument("--subp", nargs="*", default=DEFAULT_SUBPROTOCOLS,
                        help="WebSocket subprotocols (기본: ocpp1.6)")
    parser.add_argument("--timeout", type=int, default=RECV_TIMEOUT_SEC,
                        help="서버 응답 타임아웃(초)")
    args = parser.parse_args()

    # 입력 수집
    inputs = list(iter_input_records(args.input))
    if not inputs:
        print("No input JSON found.")
        return

    rows = []  # CSV 누적: [input_display, classified_result]

    # WebSocket 연결 (한 번 연결해서 전 케이스 전송)
    async with websockets.connect(args.uri, subprotocols=args.subp) as ws:
        print(f"[HS] negotiated subprotocol = {ws.subprotocol!r}")

        for display_path, parsed in inputs:
            # 프레임 보정: list 형태/필드 수 점검
            frame = replace_uid_if_enabled(parsed, args.replace_uid)

            if not isinstance(frame, list) or len(frame) < FRAME_MIN_FIELDS:
                result = "EXC:INVALID_FORMAT"
            else:
                # 자리표시자("$UID$") 방어적 치환 (replace-uid 옵션 없이도 안전)
                if frame[1] == UID_PLACEHOLDER:
                    frame[1] = str(uuid.uuid4())
                result = await send_frame_and_receive(ws, frame, timeout=args.timeout)

            cls = classify_response(result)
            print(f"{str(display_path):35s} -> {cls}")
            rows.append([str(display_path), cls])

    # CSV 작성
    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["input", "result"])
        writer.writerows(rows)

    print(f"wrote CSV: {args.csv}")


if __name__ == "__main__":
    asyncio.run(main())