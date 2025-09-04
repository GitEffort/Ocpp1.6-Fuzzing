# ocpp_seeds.py
# OCPP 1.6 CP->CSMS 퍼징용 기본 시드 모음
# - NORMAL_SEEDS      : 표준에 맞는 정상 CP 요청
# - VIOLATION_SEEDS   : 원래 CSMS가 보내는 요청을 CP가 보낸 "방향 위반" 케이스 (논리 퍼징)
# - EDGECASE_SEEDS    : 최소/경계/이상치 입력 (Mutator 전에 baseline으로도 유용)

# NOTE:
#  - 프레임은 [2, "$UID$", "Action", {payload}] 형식
#  - "$UID$"는 런타임에서 치환
#  - timestamp/retrieveDate/expiryDate 등은 실행 시 갱신 권장

DICT_MUTATE_PROB = 0.5     # dict 필드 제거/재귀 변형
DICT_JUNK_PROB   = 0.3     # dict에 "__junk__" 추가
LIST_APPEND_PROB = 0.2     # list에 None 추가
ACTION_SWAP_PROB = 0.2     # 액션 스왑
PAYLOAD_MUTATE_PROB = 1.0  # payload 변형 (항상 시도)
HEADER_CORRUPT_PROB = 0.1  # 헤더 파괴 확률

NORMAL_SEEDS = [
    # ---- CP -> CSMS 정상 요청 ----
    # BootNotification
    [2, "$UID$", "BootNotification", {
        "chargePointVendor": "SeedCo",
        "chargePointModel": "S-01",
        "firmwareVersion": "1.0.0"
    }],
    # Authorize
    [2, "$UID$", "Authorize", {
        "idTag": "ABC123"
    }],
    # StartTransaction
    [2, "$UID$", "StartTransaction", {
        "connectorId": 1,
        "idTag": "ABC123",
        "meterStart": 0,
        "timestamp": "2025-08-31T00:00:00Z"
    }],
    # StopTransaction
    [2, "$UID$", "StopTransaction", {
        "transactionId": 12345,
        "meterStop": 100,
        "timestamp": "2025-08-31T00:05:00Z"
    }],
    # Heartbeat (payload 없음)
    [2, "$UID$", "Heartbeat", {}],
    # MeterValues (단일 샘플)
    [2, "$UID$", "MeterValues", {
        "connectorId": 1,
        "meterValue": [{
            "timestamp": "2025-08-31T00:01:00Z",
            "sampledValue": [{"value": "10.0"}]   # string
        }]
    }],
    # MeterValues (복합 샘플)
    [2, "$UID$", "MeterValues", {
        "connectorId": 1,
        "meterValue": [{
            "timestamp": "2025-08-31T00:02:00Z",
            "sampledValue": [
                {"measurand": "Voltage", "value": "220.0"},
                {"measurand": "Current.Import", "value": "10.5"}
            ]
        }]
    }],
    # StatusNotification
    [2, "$UID$", "StatusNotification", {
        "connectorId": 1,
        "errorCode": "NoError",
        "status": "Available",
        "timestamp": "2025-08-31T00:00:00Z"
    }],
    # DiagnosticsStatusNotification (여러 enum 예시)
    [2, "$UID$", "DiagnosticsStatusNotification", {"status": "Idle"}],
    [2, "$UID$", "DiagnosticsStatusNotification", {"status": "Uploading"}],
    [2, "$UID$", "DiagnosticsStatusNotification", {"status": "Uploaded"}],
    [2, "$UID$", "DiagnosticsStatusNotification", {"status": "UploadFailed"}],
    # FirmwareStatusNotification (여러 enum 예시)
    [2, "$UID$", "FirmwareStatusNotification", {"status": "Downloading"}],
    [2, "$UID$", "FirmwareStatusNotification", {"status": "Downloaded"}],
    [2, "$UID$", "FirmwareStatusNotification", {"status": "Installing"}],
    [2, "$UID$", "FirmwareStatusNotification", {"status": "Installed"}],
    # DataTransfer (확장 최소/확장형)
    [2, "$UID$", "DataTransfer", {"vendorId": "VENDORX"}],
    [2, "$UID$", "DataTransfer", {
        "vendorId": "VENDORX",
        "messageId": "customMsg",
        "data": "opaque-payload"
    }],
]

VIOLATION_SEEDS = [
    # ---- 논리 퍼징: 원래 CSMS->CP 요청을 CP가 Call로 보내는 케이스 ----
    # CSMS가 시작해야 할 액션들: ChangeAvailability, ChangeConfiguration, ClearCache, GetConfiguration,
    # RemoteStartTransaction, RemoteStopTransaction, Reset, UnlockConnector,
    # GetDiagnostics, UpdateFirmware, GetLocalListVersion, SendLocalList, TriggerMessage,
    # ReserveNow, CancelReservation, GetCompositeSchedule, SetChargingProfile, ClearChargingProfile

    [2, "$UID$", "ChangeAvailability", {"connectorId": 1, "type": "Operative"}],
    [2, "$UID$", "ChangeConfiguration", {"key": "MeterValueSampleInterval", "value": "10"}],
    [2, "$UID$", "ClearCache", {}],
    [2, "$UID$", "GetConfiguration", {"key": ["AllowOfflineTxForUnknownId"]}],
    [2, "$UID$", "RemoteStartTransaction", {"idTag": "ABC12345"}],
    [2, "$UID$", "RemoteStopTransaction", {"transactionId": 12345}],
    [2, "$UID$", "Reset", {"type": "Soft"}],
    [2, "$UID$", "UnlockConnector", {"connectorId": 1}],
    [2, "$UID$", "GetDiagnostics", {"location": "http://example.com/diag/"}],
    [2, "$UID$", "UpdateFirmware", {
        "location": "http://example.com/fw.bin",
        "retrieveDate": "2025-08-31T00:00:00Z"
    }],
    [2, "$UID$", "GetLocalListVersion", {}],
    [2, "$UID$", "SendLocalList", {
        "listVersion": 2,
        "updateType": "Full",
        "localAuthorisationList": [
            {"idTag": "ABC12345", "idTagInfo": {"status": "Accepted"}}
        ]
    }],
    [2, "$UID$", "TriggerMessage", {"requestedMessage": "BootNotification"}],
    [2, "$UID$", "ReserveNow", {
        "connectorId": 1,
        "expiryDate": "2025-08-31T00:20:00Z",
        "idTag": "ABC12345",
        "reservationId": 777
    }],
    [2, "$UID$", "CancelReservation", {"reservationId": 777}],
    [2, "$UID$", "GetCompositeSchedule", {"connectorId": 1, "duration": 1800}],
    [2, "$UID$", "SetChargingProfile", {
        "connectorId": 1,
        "csChargingProfiles": {
            "chargingProfileId": 1,
            "stackLevel": 0,
            "chargingProfilePurpose": "TxProfile",
            "chargingProfileKind": "Absolute",
            "chargingSchedule": {
                "chargingRateUnit": "W",
                "chargingSchedulePeriod": [{"startPeriod": 0, "limit": 11000}]
            }
        }
    }],
    [2, "$UID$", "ClearChargingProfile", {}],
]

EDGECASE_SEEDS = [
    # ---- 경계/엣지/형식 파괴 전용 시드 ----
    # 빈 페이로드
    [2, "$UID$", "BootNotification", {}],
    # 알 수 없는 액션
    [2, "$UID$", "TotallyUnknownAction", {}],
    # 과도한 문자열 / 특수문자 idTag
    [2, "$UID$", "Authorize", {"idTag": "🔥"*10}],
    # timestamp 형식 이상(문자열이지만 틀린 포맷)
    [2, "$UID$", "StartTransaction", {
        "connectorId": 1, "idTag": "ABC123", "meterStart": 0, "timestamp": "31-08-2025 00:00"
    }],
    # 음수/큰 수 등 수치 경계
    [2, "$UID$", "StopTransaction", {
        "transactionId": -1, "meterStop": 10**9, "timestamp": "2025-08-31T00:05:00Z"
    }],
    # MeterValues: 빈 sampledValue / None 삽입
    [2, "$UID$", "MeterValues", {
        "connectorId": 1, "meterValue": [{"timestamp": "2025-08-31T00:01:00Z", "sampledValue": []}]
    }],
]

# 최종 묶음: 필요에 따라 일부만 사용해도 됨
DEFAULT_SEEDS = NORMAL_SEEDS + VIOLATION_SEEDS + EDGECASE_SEEDS