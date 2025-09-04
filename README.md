# OCPP Fuzzing Project
Open Charge Point Protocol (OCPP) 1.6 기반 전기차 충전 서버의 보안성을 검증하기 위한 퍼징 프레임워크입니다.

Seed corpus → 변형(뮤테이션) → 전송 → 수집 → 분석까지의 간단한 파이프라인을 제공합니다.

# 목표
1) 전기차 충전 인프라에서 잠재적인 취약 지점 탐색
2) 프로토콜 준수 여부 및 예외 처리 로직 검증
3) Crash / 오류 응답 / 시퀀스 위반 사례를 통해 서버 견고성 평가 및 보안 가이드라인 도출

# Directory Layout
```
OCPP_FUZZING/
├── corpus_out/                 # 생성된 fuzz/baseline JSON 출력 폴더
├── ocpp_fuzzing/               # 라이브러리 코드 (패키지)
│   ├── __init__.py
│   ├── seeds.py                # 기본 시드 모음
│   ├── generator.py            # corpus 생성기 (mutator 포함)
│   ├── sender.py               # WebSocket 전송 및 응답 수집
│   └── server.py               # OCPP 1.6 테스트용 CSMS 서버
├── scripts/                    # 실행용 진입 스크립트
│   ├── run_generator.py
│   ├── run_sender.py
│   └── run_server.py
├── README.md
└── requirements.txt
```
# 아키텍처
퍼징 과정은 다음 단계로 구성됩니다
1) Seeds (ocpp_fuzzing/seeds.py)
    - NORMAL_SEEDS : 표준 CP→CSMS 요청
    - VIOLATION_SEEDS : 원래 CSMS→CP가 보내는 요청을 CP가 보낸 것으로 가정하는 “방향 위반” 시나리오
    - EDGECASE_SEEDS : 빈/이상치/경계값 등의 케이스
2) Generator (ocpp_fuzzing/generator.py)
  OCPP 시드 메시지(Authorize, BootNotification 등) 자동 생성
  변형 적용
    - 필드 누락
    - 타입 변경
    - oversize 문자열 삽입
    - 의미없는 필드 추가

3) Sender (ocpp_fuzzing/sender.py)
    - WebSocket (subprotocol=ocpp1.6) 기반 메시지 전송
    - 서버 응답(CallResult / CallError) 및 예외 상황(TIMEOUT / CLOSED) 수집

5) Server (ocpp_fuzzing/server.py)
    - 모든 테스트 케이스의 응답을 CSV 로그로 저장
    - 주요 지표: latency, errorCode, result

# Quick Start
1) 테스트 서버 실행 (CSMS)
python scripts/run_server.py --host 0.0.0.0 --port 9000
2) corpus 생성
python scripts/run_generator.py \
  --dir corpus_out --target 50 --min 1 --max 5 --baseline --seed 42
3) 전송
python scripts/run_sender.py \
  --input corpus_out --replace-uid --csv replay_result.csv \
  --uri ws://127.0.0.1:9000/CP_REPLAY

# Features
1) 자동 시드/변형 생성 기반 퍼징
2) WebSocket 통신으로 실시간 서버 응답 검증
3) 결과 자동 수집 및 CSV 로그화
4) 분석 모듈 확장 가능 구조 (추후 시각화 및 리포트 기능 포함 예정)
