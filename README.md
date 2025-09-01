# OCPP_FUZZING
OCPP Fuzzing Project

이 프로젝트는 Open Charge Point Protocol (OCPP) 1.6을 대상으로
보안성 검증을 수행하기 위한 퍼징(Fuzzing) 프레임워크입니다.

목표: 전기차 충전 인프라의 취약 가능 지점 탐색
방법: Seed Corpus → Mutator → Fuzz Sender → Collector → Analyzer
기대 효과: Crash/오류 응답/시퀀스 위반을 통해 서버 견고성 평가 및 보안 가이드라인 도출

Features
  1) Corpus Builder + Mutator
    기본 OCPP 시드(Authorize, BootNotification 등)를 자동 생성
    필드 누락/타입 변경/oversize/쓰레기 필드 추가 변형
  2) Fuzz Sender
    WebSocket (subprotocol=ocpp1.6) 기반으로 하나씩 전송
    CallResult/CallError/TIMEOUT/CLOSED 결과 수집
  3) Collector
    모든 케이스의 응답을 CSV 로그로 기록
    latency, errorCode, result 분류
  4)Analyzer (추가 예정)
    CSV 기반 통계/차트
    Crash/Timeout 패턴 분석
