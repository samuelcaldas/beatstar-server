"""Player authentication tickets: opaque, stored server-side as digests, and expiring."""

import sqlite3

import pytest

from server.admin.database import create_admin_engine, create_admin_session_maker
from server.handlers.session_handler import SessionHandler
from server.models.headers import ClientHeader
from server.player_auth.store import PlayerTicketStore
from server.storage.database import DatabaseManager
from server.storage.migrations.runner import upgrade_to_head
from server.storage.player_repository import PlayerRepository

CINTA = "676d4d53-f0cb-41c6-8c27-4bb3c3c3c905"
LIFETIME_SECONDS = 3600


class Clock:
    """A controllable clock so expiry is tested without sleeping."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
async def migrated_database(tmp_path):
    """Creates the legacy and migrated tables on a disposable database and disposes its engine."""
    database_file = str(tmp_path / "tickets.db")
    database = DatabaseManager(database_file)
    await database.initialize()
    upgrade_to_head(database_file)
    engine = create_admin_engine(database_file)
    yield database_file, database, engine
    await engine.dispose()


@pytest.fixture
def clock():
    return Clock(now=1_000_000.0)


@pytest.fixture
def store(migrated_database, clock):
    _, _, engine = migrated_database
    return PlayerTicketStore(create_admin_session_maker(engine), LIFETIME_SECONDS, clock=clock)


async def test_issued_ticket_resolves_to_its_player(store):
    """Breaks if a login ticket cannot be traced back to the player it was issued for."""
    ticket = await store.issue(CINTA)

    assert await store.resolve(ticket) == CINTA


async def test_unknown_ticket_resolves_to_nothing(store):
    """Breaks if an arbitrary string is accepted as a ticket."""
    await store.issue(CINTA)

    assert await store.resolve("auth-forged-by-a-client") is None


async def test_ticket_stops_resolving_after_its_lifetime(store, clock):
    """Breaks if a ticket stays valid indefinitely after login."""
    ticket = await store.issue(CINTA)

    clock.now += LIFETIME_SECONDS + 1

    assert await store.resolve(ticket) is None


async def test_ticket_still_resolves_just_before_its_lifetime_ends(store, clock):
    """Breaks if tickets expire early and reject legitimate players."""
    ticket = await store.issue(CINTA)

    clock.now += LIFETIME_SECONDS - 1

    assert await store.resolve(ticket) == CINTA


async def test_each_login_receives_a_distinct_ticket(store):
    """Breaks if tickets are predictable or shared between logins."""
    first = await store.issue(CINTA)
    second = await store.issue(CINTA)

    assert first != second
    assert await store.resolve(first) == CINTA
    assert await store.resolve(second) == CINTA


async def test_database_holds_only_a_digest_of_the_ticket(store, migrated_database):
    """Breaks if a database read exposes usable ticket values."""
    database_file, _, _ = migrated_database
    ticket = await store.issue(CINTA)

    connection = sqlite3.connect(database_file)
    try:
        stored = [str(value) for row in connection.execute("SELECT * FROM player_tickets") for value in row]
    finally:
        connection.close()

    assert stored
    assert all(ticket not in value for value in stored)


async def test_tickets_survive_a_restart_on_the_same_database(migrated_database, clock):
    """Breaks if tickets live only in memory and players must log in again after a restart."""
    _, _, engine = migrated_database
    issuing = PlayerTicketStore(create_admin_session_maker(engine), LIFETIME_SECONDS, clock=clock)
    ticket = await issuing.issue(CINTA)

    restarted = PlayerTicketStore(create_admin_session_maker(engine), LIFETIME_SECONDS, clock=clock)

    assert await restarted.resolve(ticket) == CINTA


async def test_login_handler_issues_a_ticket_the_store_resolves(migrated_database, store):
    """Breaks if the login response carries a ticket that the server never recorded."""
    _, database, _ = migrated_database
    handler = SessionHandler(PlayerRepository(database), store)
    header = ClientHeader(service="userservice", rpcthing="rpc-1")

    response = await handler.handle(header, {"all_in_one_login": {"cinta": CINTA}})

    ticket = response["resp_login_of_some_type"]["authenticationTicket"]
    assert await store.resolve(ticket) == CINTA
