import json, random, argparse, copy
import string
from pathlib import Path
from typing import List, Union, Any
from ocpp_seeds import DEFAULT_SEEDS, DICT_MUTATE_PROB, DICT_JUNK_PROB, LIST_APPEND_PROB, ACTION_SWAP_PROB, HEADER_CORRUPT_PROB 

def make_dir(path):
    path.mkdir(parents=True, exist_ok=True)

def normalize_action_name(action):
    raw_name = str(action or "Unknown")
    return "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "_"
        for ch in raw_name
    )

def mutate_payload(payload):
    """
    주어진 payload를 (깊은 복사 후) 무작위 규칙으로 재귀 변형하여 반환합니다.

    규칙
      1) dict
         - 50%: 임의의 키를 선택해 (a) 필드 제거 또는 (b) 해당 값 재귀 변형
         - 30%: 임시 필드 추가(랜덤 영숫자 1~50자)
      2) list
         - 모든 원소 재귀 변형
         - 20%: 리스트 끝에 None 추가
      3) str
         - 무작위로 다음 중 하나 적용: 유지 / 빈문자열 / oversize(뒤에 'A' 25~200개 추가) / 정수로 강제(12345)
      4) int/float
         - -1, 0, 원래값, 10**9 중 하나로 치환

    반환값:
      - 변형된 payload (원본은 보존)
    """
    # 원본 변경 방지
    payload = copy.deepcopy(payload)

    # dict 처리
    if isinstance(payload, dict):
        field_names = list(payload.keys())

        # 50% 확률로 임의의 필드 하나를 제거하거나 그 값만 재귀 변형
        if field_names and random.random() < DICT_MUTATE_PROB:
            key_to_change = random.choice(field_names)
            if random.random() < DICT_MUTATE_PROB:
                # 필드 누락
                payload.pop(key_to_change, None)
            else:
                # 재귀 변형
                payload[key_to_change] = mutate_payload(payload.get(key_to_change))

        # 30% 확률로 쓰레기(junk) 필드 추가
        if random.random() < DICT_JUNK_PROB:
            junk_length = random.randint(1, 50)
            payload["__junk__"] = "".join(
                random.choices(string.ascii_letters + string.digits, k=junk_length)
            )

    # list 처리
    elif isinstance(payload, list):
        # 각 원소 재귀 변형
        payload = [mutate_payload(element) for element in payload]

        # 20% 확률로 None 추가
        if random.random() < LIST_APPEND_PROB :
            payload.append(None)

    # str
    elif isinstance(payload, str):
        mutation_kind = random.choice(["keep", "empty", "oversize", "as_int"])
        if mutation_kind == "empty":
            return ""
        if mutation_kind == "oversize":
            # oversize: 뒤에 'A'를 25~200개 추가
            return payload + ("A" * random.randint(25, 200))
        if mutation_kind == "as_int":
            # 타입 변경: 문자열을 정수로 강제 변경
            return 12345
        # "keep"인 경우 원문 그대로 반환

    # 숫자 처리 (int/float)
    elif isinstance(payload, (int, float)):
        payload = random.choice([-1, 0, payload, 10**9])

    # 기타 타입은 그대로 반환
    return payload

def make_variants(message_frame: list, n_variants: int):
    """
    주어진 OCPP 프레임을 여러 개 변형하여 반환합니다.

    프레임 구조 가정:
        [2, unique_id, Action, payload]
        - 첫 번째 요소: 메시지 타입(예: 2 = CALL)
        - 두 번째 요소: unique_id (변형하지 않고 저장 후, Sender 단계에서 치환)
        - 세 번째 요소: 액션(Action)
        - 네 번째 요소: payload (dict 또는 list)

    변형 규칙(확률 기반):
        1) 액션(Action) 스왑 (20%)
           - 정의된 액션 중 하나 또는 임의의 잘못된 액션으로 교체
        2) 페이로드(payload) 변형
           - payload가 dict 또는 list일 경우 mutate_payload() 재귀 변형 적용
        3) 헤더 파괴 (10%)
           - 첫 번째 요소(메시지 타입)를 비정상 값으로 교체

    Args:
        message_frame (list): 원본 메시지 프레임
        n_variants (int): 생성할 변형 개수

    Returns:
        List[list]: 변형된 메시지 프레임들의 리스트
    """
    variants = []

    for _ in range(n_variants):
        # 원본을 깊은 복사하여 변형 시작
        frame_copy = copy.deepcopy(message_frame)

        # 액션(Action) 스왑
        if len(frame_copy) >= 3 and random.random() < ACTION_SWAP_PROB:
            frame_copy[2] = random.choice([
                "BootNotification", "Authorize", "StartTransaction",
                "StatusNotification", "MeterValues", "TotallyUnknownAction"
            ])

        # 페이로드 변형 - payload가 dict 또는 list인 경우
        if len(frame_copy) >= 4 and isinstance(frame_copy[3], (dict, list)):
            frame_copy[3] = mutate_payload(frame_copy[3])

        # 헤더 파괴 - 10% 확률로 첫 번째 요소를 이상한 값으로 바꿈
        if random.random() < HEADER_CORRUPT_PROB:
            frame_copy[0] = random.choice(["2", -1, 999])

        variants.append(frame_copy)

    return variants

# --- 확률/파라미터 상수 -------------------------------------------------------
BASELINE_SAVE_PROB = 0.2  # baseline 프레임 저장 확률(옵션 켜진 경우)

def main():
    """
    OCPP Fuzz JSON 코퍼스를 생성합니다.

    입력 시드: DEFAULT_SEEDS (각 시드는 [2, unique_id, Action, payload] 가정)
    출력: --dir 에 fuzz/baseline JSON 파일들 기록
    개수: --target 개수 맞출 때까지 생성 (baseline 포함 여부는 옵션/확률에 따름)
    """
    parser = argparse.ArgumentParser(description="Create OCPP Fuzz JSON corpus")
    parser.add_argument("--dir", default="corpus_out", help="출력 디렉터리")
    parser.add_argument("--target", type=int, required=True, help="생성할 총 파일 개수")
    parser.add_argument("--min", type=int, default=1, help="Variant 최소값")
    parser.add_argument("--max", type=int, default=5, help="Variant 최대값")
    parser.add_argument("--baseline", action="store_true", help="원본 프레임도 포함(일부 확률)")
    parser.add_argument("--seed", type=int, default=None, help="재현성용 난수 시드(예: 42)")
    args = parser.parse_args()

    # 재현성(옵션)
    if args.seed is not None:
        random.seed(args.seed)

    # 출력 디렉터리 준비
    output_dir = Path(args.dir)
    make_dir(output_dir)

    # 시드 풀 준비
    seed_pool = list(DEFAULT_SEEDS)

    # 파라미터 정리 (하한/상한 방어)
    min_variants = max(0, args.min)
    max_variants = max(min_variants, args.max)
    target_files = max(1, args.target)

    file_index = 0          # 파일명 번호(0001, 0002, …)
    written_count = 0       # 실제로 쓴 파일 수

    # 랜덤 생성 루프: target_files 개수 채울 때까지
    while written_count < target_files:
        seed_frame = random.choice(seed_pool)

        # 액션명 추출 → 파일명 안전화
        if isinstance(seed_frame, list) and len(seed_frame) > 2:
            action_name = seed_frame[2]
        else:
            action_name = "Unknown"
        safe_action_name = normalize_action_name(str(action_name))

        # (옵션) baseline 저장: baseline 플래그 on 이고, 확률에 당첨되면 저장
        if args.baseline and random.random() < BASELINE_SAVE_PROB and written_count < target_files:
            file_index += 1
            (output_dir / f"{file_index:04d}_{safe_action_name}_baseline.json").write_text(
                json.dumps(seed_frame, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            written_count += 1
            if written_count >= target_files:
                break

        # 변형 개수 결정 및 변형 생성
        n_variants = random.randint(min_variants, max_variants)
        variant_frames = make_variants(seed_frame, n_variants)

        # 각 변형을 파일로 기록
        for variant in variant_frames:
            if written_count >= target_files:
                break
            file_index += 1
            (output_dir / f"{file_index:04d}_{safe_action_name}_fuzz.json").write_text(
                json.dumps(variant, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            written_count += 1

    print(f"wrote {written_count} files to {output_dir}")

if __name__ == "__main__":
    main()
