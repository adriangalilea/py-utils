"""Runnable demonstration of py_utils offensive programming primitives.

This is the integration test for offensive.py. Run it after any change:

    uv run python example_offensive.py

Every block demonstrates one primitive, catches the expected error, and
prints a confirmation line. If any section raises unexpectedly or fails to
raise when it should, the script exits non-zero.

See the module docstring at the top of src/py_utils/offensive.py for rationale.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from py_utils import (  # noqa: E402
    ContractError,
    InvariantError,
    PostconditionError,
    PreconditionError,
    SourcedError,
    boundary,
    ensure,
    invariant,
    log,
    must,
    require,
)


def expect(exc_type: type[BaseException], label: str):
    """Context helper: assert that `exc_type` is raised inside the `with` block."""

    class _Expect:
        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            if et is None:
                raise SystemExit(f"{label}: expected {exc_type.__name__}, none raised")
            if not issubclass(et, exc_type):
                raise SystemExit(
                    f"{label}: expected {exc_type.__name__}, got {et.__name__}"
                )
            log.info(f"  → caught {et.__name__}: {ev}")
            return True

    return _Expect()


def demo_require() -> None:
    log.info("require() — preconditions")

    def charge(amount: int) -> None:
        require(amount > 0, "amount must be positive", amount=amount)

    charge(100)
    log.info("  → charge(100) passed")

    with expect(PreconditionError, "require"):
        charge(-5)


def demo_invariant() -> None:
    log.info("invariant() — internal state")

    balance = 100
    balance -= 50
    invariant(balance >= 0, "balance went negative", balance=balance)
    log.info(f"  → balance={balance} invariant holds")

    with expect(InvariantError, "invariant"):
        invariant(False, "simulated bug", where="demo_invariant")


def demo_ensure() -> None:
    log.info("ensure() — postconditions")

    def load(user_id: str) -> dict[str, str]:
        result: dict[str, str] | None = None  # simulate lookup failure
        ensure(result is not None, "load returned None", user_id=user_id)
        return result  # type: ignore[return-value]

    with expect(PostconditionError, "ensure"):
        load("u_123")


def demo_must() -> None:
    log.info("must() — Optional[T] unwrap")

    users: dict[str, str] = {"u_1": "alice"}
    name = must(users.get("u_1"), "user not found", user_id="u_1")
    log.info(f"  → must returned {name!r}")

    with expect(InvariantError, "must"):
        must(users.get("u_missing"), "user not found", user_id="u_missing")


def demo_sourced_error() -> None:
    log.info("SourcedError — raise explicitly")

    def fake_api_call() -> None:
        try:
            raise ValueError("card declined")
        except ValueError as e:
            raise SourcedError(
                source="stripe",
                operation="charge_customer",
                message=str(e),
                status=402,
                cause=e,
                customer_id="cus_ABC",
                amount=5000,
            ) from e

    try:
        fake_api_call()
    except SourcedError as e:
        assert e.source == "stripe"
        assert e.operation == "charge_customer"
        assert e.status == 402
        assert e.context["customer_id"] == "cus_ABC"
        assert isinstance(e.__cause__, ValueError)
        log.info(f"  → source={e.source} status={e.status} context={e.context}")
        log.info(f"  → to_dict={e.to_dict()}")


def demo_boundary_wraps() -> None:
    log.info("@boundary — auto-wraps raw exceptions")

    @boundary("openai")
    def complete(prompt: str) -> str:
        raise RuntimeError("rate limited")

    with expect(SourcedError, "boundary wrap"):
        complete("hello")


def demo_boundary_passthrough() -> None:
    log.info("@boundary — ContractError passes through unwrapped")

    @boundary("db")
    def query(limit: int) -> list[int]:
        require(limit > 0, "limit must be positive", limit=limit)
        return []

    with expect(PreconditionError, "boundary passthrough"):
        query(-1)


def demo_hierarchy() -> None:
    log.info("Exception hierarchy — ContractError subclasses AssertionError")
    assert issubclass(PreconditionError, ContractError)
    assert issubclass(ContractError, AssertionError)
    log.info("  → PreconditionError → ContractError → AssertionError ✓")


def main() -> None:
    with log.task("offensive programming demo"):
        demo_require()
        demo_invariant()
        demo_ensure()
        demo_must()
        demo_sourced_error()
        demo_boundary_wraps()
        demo_boundary_passthrough()
        demo_hierarchy()
    log.info("all offensive primitives verified")


if __name__ == "__main__":
    main()
