# OCPPServer.py (clean version, no emojis)

import asyncio
import logging
import argparse
from datetime import datetime, UTC

import websockets
from ocpp.routing import on
from ocpp.v16 import ChargePoint as ChargePointBase
from ocpp.v16 import call_result
from ocpp.v16.datatypes import IdTagInfo
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
    OCPP 1.6 CSMS 핸들러.
    """

    @on("BootNotification")
    async def on_boot(self, charge_point_model, charge_point_vendor, **kw):
        log.info("BootNotification received: vendor=%s, model=%s",
                 charge_point_vendor, charge_point_model)
        return call_result.BootNotification(
            current_time=datetime.now(UTC).isoformat(),
            interval=10,
            status="Accepted",
        )

    @on("Authorize")
    async def on_auth(self, id_tag, **kw):
        log.info("Authorize received: idTag=%s", id_tag)
        return call_result.Authorize(
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted)
        )

    @on("StartTransaction")
    async def on_start(self, connector_id, id_tag, meter_start, timestamp, **kw):
        log.info("StartTransaction received: connector=%s idTag=%s meterStart=%s",
                 connector_id, id_tag, meter_start)
        return call_result.StartTransaction(
            transaction_id=12345,
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted),
        )

    @on("MeterValues")
    async def on_meter(self, connector_id, meter_value, **kw):
        samples = sum(len(m.get("sampledValue", [])) for m in (meter_value or []))
        log.info("MeterValues received: connector=%s samples=%s", connector_id, samples)
        return call_result.MeterValues()


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
