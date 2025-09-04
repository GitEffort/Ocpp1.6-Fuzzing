# OCPP Fuzzing Project
OCPP Fuzzing Project는 Open Charge Point Protocol (OCPP) 1.6 기반 전기차 충전 서버의 보안성을 검증하기 위한 퍼징 프레임워크입니다.

# 목표
1) 전기차 충전 인프라에서 잠재적인 취약 지점 탐색
2) 프로토콜 준수 여부 및 예외 처리 로직 검증
3) Crash / 오류 응답 / 시퀀스 위반 사례를 통해 서버 견고성 평가 및 보안 가이드라인 도출

# 아키텍처
퍼징 과정은 다음 단계로 구성됩니다
1) Corpus Builder + Mutator
  OCPP 시드 메시지(Authorize, BootNotification 등) 자동 생성
  변형 적용
    - 필드 누락
    - 타입 변경
    - oversize 문자열 삽입
    - 의미없는 필드 추가

2) Fuzz Sender
  WebSocket (subprotocol=ocpp1.6) 기반 메시지 전송
  서버 응답(CallResult / CallError) 및 예외 상황(TIMEOUT / CLOSED) 수집

3) Collector
  모든 테스트 케이스의 응답을 CSV 로그로 저장
  주요 지표: latency, errorCode, result

4) Analyzer (개발 예정)
  CSV 기반 통계/차트 분석
  Crash/Timeout 패턴 분석 및 보고서 생성

# Features
1) 자동 시드/변형 생성 기반 퍼징
2) WebSocket 통신으로 실시간 서버 응답 검증
3) 결과 자동 수집 및 CSV 로그화
4) 분석 모듈 확장 가능 구조 (추후 시각화 및 리포트 기능 포함 예정)
