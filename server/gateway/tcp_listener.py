"""Asynchronous TCP listener for Beatstar SocketGateway binary traffic."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.gateway.dispatcher import GatewayDispatcher

logger = logging.getLogger("beatstar.tcp_gateway")


class TcpSocketGatewayServer:
    """Asynchronous TCP server implementing SpaceApe WireCodec framing."""

    def __init__(
        self, dispatcher: GatewayDispatcher, host: str = "0.0.0.0", port: int = 9090
    ) -> None:
        self.dispatcher = dispatcher
        self.host = host
        self.port = port
        self.server: asyncio.Server | None = None

    async def start(self) -> None:
        """Binds and starts accepting incoming raw TCP connections."""
        self.server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        logger.info("SocketGateway TCP server listening on %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Closes the TCP server and waits for shutdown."""
        if not self.server:
            return
        self.server.close()
        await self.server.wait_closed()
        logger.info("SocketGateway TCP server stopped.")

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Reads framed binary messages and responds over persistent TCP connection."""
        peer = writer.get_extra_info("peername")
        logger.info("Nova conexão TCP recebida de %s", peer)
        try:
            await self._client_read_loop(reader, writer)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.info("Cliente desconectado: %s", peer)
        except Exception as exc:
            logger.error("Erro na conexão TCP com %s: %s", peer, exc)
        finally:
            writer.close()
            await writer.wait_closed()

    async def _client_read_loop(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Iterates over incoming wire frames until connection closes."""
        while not reader.at_eof():
            len_bytes = await reader.readexactly(4)
            payload_len = int.from_bytes(len_bytes, byteorder="big")
            payload_bytes = await reader.readexactly(payload_len)
            print(f"[TCP_RAW] Frame received: len={payload_len}, hex={payload_bytes[:64].hex()}", flush=True)
            full_frame = len_bytes + payload_bytes
            resp_frame = await self.dispatcher.dispatch_wire_frame(full_frame)
            writer.write(resp_frame)
            await writer.drain()
