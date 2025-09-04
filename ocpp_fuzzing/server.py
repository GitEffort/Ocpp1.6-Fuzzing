# OCPPServer.py (clean version, no emojis)

import asyncio
import logging
import argparse
from datetime import datetime, UTC

import websockets
from ocpp.routing import on
from ocpp.v16 import ChargePoint as ChargePointBase
from ocpp.v16 import call_result
from ocpp.v16.datatypes import IdTagInfo, KeyValue, ChargingSchedule, ChargingSchedulePeriod
from ocpp.v16.enums import AuthorizationStatus

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9000
REQUIRED_SUBPROTOCOL = "ocpp1.6"
PING_INTERVAL = None                 # 서버가 핑 안 보낼 경우
MAX_MESSAGE_BYTES = 2 * 1024 * 1024  # 최대 수신 페이로드 크기


LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.getLogger("ocpp").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
log = logging.getLogger("ocpp-server")


class CentralSystem(ChargePointBase):
    """
    OCPP 1.6 CSMS 데모 핸들러.
    - NORMAL_SEEDS의 표준 CP->CSMS 요청 처리
    - VIOLATION_SEEDS의 '방향 위반' 액션도 CallResult로 수용(테스트 편의 목적)
    - EDGECASE_SEEDS의 변형/경계값도 최소 스키마로 응답
    """

    # ===== NORMAL_SEEDS (CP -> CSMS 표준 요청) =====

    @on("BootNotification")
    async def on_boot(self, charge_point_model, charge_point_vendor, **kw):
        log.info("BootNotification: vendor=%s model=%s", charge_point_vendor, charge_point_model)
        return call_result.BootNotification(
            current_time=datetime.now(UTC).isoformat(),
            interval=10,
            status="Accepted",
        )

    @on("Authorize")
    async def on_authorize(self, id_tag, **kw):
        log.info("Authorize: idTag=%s", id_tag)
        return call_result.Authorize(
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted)
        )

    @on("StartTransaction")
    async def on_start_tx(self, connector_id, id_tag, meter_start, timestamp, **kw):
        log.info("StartTransaction: connector=%s idTag=%s meterStart=%s", connector_id, id_tag, meter_start)
        return call_result.StartTransaction(
            transaction_id=12345,
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted),
        )

    @on("StopTransaction")
    async def on_stop_tx(self, transaction_id, meter_stop, timestamp, **kw):
        log.info("StopTransaction: txId=%s meterStop=%s", transaction_id, meter_stop)
        # id_tag_info 응답은 선택(생략 가능). 여기선 간단 응답.
        return call_result.StopTransaction()

    @on("Heartbeat")
    async def on_heartbeat(self, **kw):
        log.info("Heartbeat")
        return call_result.Heartbeat(
            current_time=datetime.now(UTC).isoformat()
        )

    @on("MeterValues")
    async def on_meter_values(self, connector_id=None, meter_value=None, **kw):
        samples = sum(len(m.get("sampledValue", [])) for m in (meter_value or []))
        log.info("MeterValues: connector=%s samples=%s", connector_id, samples)
        return call_result.MeterValues()

    @on("StatusNotification")
    async def on_status_notification(self, connector_id, error_code, status, **kw):
        log.info("StatusNotification: connector=%s status=%s error=%s", connector_id, status, error_code)
        return call_result.StatusNotification()

    @on("DiagnosticsStatusNotification")
    async def on_diag_status(self, status, **kw):
        log.info("DiagnosticsStatusNotification: status=%s", status)
        return call_result.DiagnosticsStatusNotification()

    @on("FirmwareStatusNotification")
    async def on_fw_status(self, status, **kw):
        log.info("FirmwareStatusNotification: status=%s", status)
        return call_result.FirmwareStatusNotification()

    @on("DataTransfer")
    async def on_data_transfer(self, vendor_id, message_id=None, data=None, **kw):
        log.info("DataTransfer: vendorId=%s messageId=%s", vendor_id, message_id)
        # 상태: Accepted/Rejected/UnknownVendorId
        return call_result.DataTransfer(status="Accepted", data="ok")

    # ===== VIOLATION_SEEDS (원래는 CSMS->CP 요청이지만, 테스트 편의상 수용) =====
    # 아래 응답은 "CP가 보낼 확인(confirmation)" 스키마를 따라 최소 유효값으로 응답합니다.

    @on("ChangeAvailability")
    async def on_change_availability(self, connector_id, type, **kw):
        log.info("ChangeAvailability (violation): connector=%s type=%s", connector_id, type)
        return call_result.ChangeAvailability(status="Accepted")

    @on("ChangeConfiguration")
    async def on_change_configuration(self, key, value, **kw):
        log.info("ChangeConfiguration (violation): %s=%s", key, value)
        return call_result.ChangeConfiguration(status="Accepted")

    @on("ClearCache")
    async def on_clear_cache(self, **kw):
        log.info("ClearCache (violation)")
        return call_result.ClearCache(status="Accepted")

    @on("GetConfiguration")
    async def on_get_configuration(self, key=None, **kw):
        log.info("GetConfiguration (violation): keys=%s", key)
        # 최소 한 개의 KeyValue 제공(예시)
        kv = [KeyValue(key="AllowOfflineTxForUnknownId", readonly=True, value="true")]
        return call_result.GetConfiguration(configuration_key=kv, unknown_key=[])

    @on("RemoteStartTransaction")
    async def on_remote_start_tx(self, id_tag, **kw):
        log.info("RemoteStartTransaction (violation): idTag=%s", id_tag)
        return call_result.RemoteStartTransaction(status="Accepted")

    @on("RemoteStopTransaction")
    async def on_remote_stop_tx(self, transaction_id, **kw):
        log.info("RemoteStopTransaction (violation): txId=%s", transaction_id)
        return call_result.RemoteStopTransaction(status="Accepted")

    @on("Reset")
    async def on_reset(self, type, **kw):
        log.info("Reset (violation): type=%s", type)
        return call_result.Reset(status="Accepted")

    @on("UnlockConnector")
    async def on_unlock_connector(self, connector_id, **kw):
        log.info("UnlockConnector (violation): connector=%s", connector_id)
        # UnlockStatus: Unlocked / UnlockFailed / NotSupported
        return call_result.UnlockConnector(status="Unlocked")

    @on("GetDiagnostics")
    async def on_get_diagnostics(self, location, **kw):
        log.info("GetDiagnostics (violation): location=%s", location)
        # file_name은 선택. 예시로 단순 문자열 반환.
        return call_result.GetDiagnostics(file_name="diag_0001.tar")

    @on("UpdateFirmware")
    async def on_update_firmware(self, location, retrieve_date, **kw):
        log.info("UpdateFirmware (violation): location=%s retrieveDate=%s", location, retrieve_date)
        # 빈 확인 응답
        return call_result.UpdateFirmware()

    @on("GetLocalListVersion")
    async def on_get_local_list_version(self, **kw):
        log.info("GetLocalListVersion (violation)")
        return call_result.GetLocalListVersion(list_version=1)

    @on("SendLocalList")
    async def on_send_local_list(self, list_version, update_type, local_authorisation_list=None, **kw):
        log.info("SendLocalList (violation): version=%s type=%s", list_version, update_type)
        return call_result.SendLocalList(status="Accepted")

    @on("TriggerMessage")
    async def on_trigger_message(self, requested_message, **kw):
        log.info("TriggerMessage (violation): requestedMessage=%s", requested_message)
        return call_result.TriggerMessage(status="Accepted")

    @on("ReserveNow")
    async def on_reserve_now(self, connector_id, expiry_date, id_tag, reservation_id, **kw):
        log.info("ReserveNow (violation): connector=%s reservationId=%s", connector_id, reservation_id)
        return call_result.ReserveNow(status="Accepted")

    @on("CancelReservation")
    async def on_cancel_reservation(self, reservation_id, **kw):
        log.info("CancelReservation (violation): reservationId=%s", reservation_id)
        return call_result.CancelReservation(status="Accepted")

    @on("GetCompositeSchedule")
    async def on_get_composite_schedule(self, connector_id, duration, charging_rate_unit=None, **kw):
        log.info("GetCompositeSchedule (violation): connector=%s duration=%s", connector_id, duration)
        # 최소 스케줄(선택) 제공 예시
        schedule_periods = [ChargingSchedulePeriod(start_period=0, limit=11000)]
        schedule = ChargingSchedule(
            charging_rate_unit=charging_rate_unit or "W",
            charging_schedule_period=schedule_periods
        )
        return call_result.GetCompositeSchedule(status="Accepted", connector_id=connector_id, schedule=schedule)

    @on("SetChargingProfile")
    async def on_set_charging_profile(self, connector_id, cs_charging_profiles, **kw):
        log.info("SetChargingProfile (violation): connector=%s", connector_id)
        return call_result.SetChargingProfile(status="Accepted")

    @on("ClearChargingProfile")
    async def on_clear_charging_profile(self, id=None, connector_id=None, charging_profile_purpose=None, stack_level=None, **kw):
        log.info("ClearChargingProfile (violation): id=%s connector=%s", id, connector_id)
        return call_result.ClearChargingProfile(status="Accepted")


async def handle_connection(ws):
    """
    클라이언트와의 핸드셰이크가 끝난 후 호출되는 엔트리.
    - 서브프로토콜 확인
    - 경로에서 ChargePoint ID 추출
    - 중앙 시스템 핸들러 구동
    """
    try:
        peer = getattr(ws, "remote_address", None)
        path = getattr(ws, "path", "/")
        log.info("[HS] peer=%s subprotocol=%r path=%s", peer, ws.subprotocol, path)

        # 필수 서브프로토콜 확인
        if ws.subprotocol != REQUIRED_SUBPROTOCOL:
            log.warning("[HS] Subprotocol mismatch: got=%r need=%r",
                        ws.subprotocol, REQUIRED_SUBPROTOCOL)
            await ws.close(code=1002, reason=f"Subprotocol required: {REQUIRED_SUBPROTOCOL}")
            return

        # 경로를 CP 식별자로 사용 (예: ws://host:port/<CP_ID>)
        cp_id = (path.strip("/") or "UNKNOWN_CP")

        # ChargePoint 핸들러 시작 (루프 생명주기 관장)
        await CentralSystem(cp_id, ws).start()

    except Exception as e:
        log.error("[SERVER] Exception: %s", e)


async def main(host=DEFAULT_HOST, port=DEFAULT_PORT):
    server = await websockets.serve(
        handle_connection,
        host=host,
        port=port,
        subprotocols=[REQUIRED_SUBPROTOCOL],
        ping_interval=PING_INTERVAL,
        max_size=MAX_MESSAGE_BYTES,
    )
    log.info("CSMS listening on ws://%s:%s", host, port)
    await server.wait_closed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCPP 1.6 Central System Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Listen port (default: 9000)")
    args = parser.parse_args()

    asyncio.run(main(host=args.host, port=args.port))
