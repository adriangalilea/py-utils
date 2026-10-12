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
    Logger,
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


def expect(s: Logger, exc_type: type[BaseException], label: str):
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
            s.step("caught", err=ev)
            return True

    return _Expect()


def demo_require(s: Logger) -> None:
    s.info("require() checks preconditions")

    def charge(amount: int) -> None:
        require(amount > 0, "amount must be positive", amount=amount)

    charge(100)
    s.step("charge passed", amount=100)

    with expect(s, PreconditionError, "require"):
        charge(-5)


def demo_invariant(s: Logger) -> None:
    s.info("invariant() checks internal state")

    balance = 100
    balance -= 50
    invariant(balance >= 0, "balance went negative", balance=balance)
    s.step("invariant holds", balance=balance)

    with expect(s, InvariantError, "invariant"):
        invariant(False, "simulated bug", where="demo_invariant")


def demo_ensure(s: Logger) -> None:
    s.info("ensure() checks postconditions")

    def load(user_id: str) -> dict[str, str]:
        result: dict[str, str] | None = None  # simulate lookup failure
        ensure(result is not None, "load returned None", user_id=user_id)
        return result  # type: ignore[return-value]

    with expect(s, PostconditionError, "ensure"):
        load("u_123")


def demo_must(s: Logger) -> None:
    s.info("must() unwraps Optional[T]")

    users: dict[str, str] = {"u_1": "alice"}
    name = must(users.get("u_1"), "user not found", user_id="u_1")
    s.step("must returned", name=name)

    with expect(s, InvariantError, "must"):
        must(users.get("u_missing"), "user not found", user_id="u_missing")


def demo_sourced_error(s: Logger) -> None:
    s.info("SourcedError raised explicitly")

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
        s.step("caught", err=e)
        s.step("transport form", to_dict=e.to_dict())


def demo_boundary_wraps(s: Logger) -> None:
    s.info("@boundary wraps raw exceptions")

    @boundary("openai")
    def complete(prompt: str) -> str:
        raise RuntimeError("rate limited")

    with expect(s, SourcedError, "boundary wrap"):
        complete("hello")


def demo_boundary_passthrough(s: Logger) -> None:
    s.info("@boundary lets ContractError pass through unwrapped")

    @boundary("db")
    def query(limit: int) -> list[int]:
        require(limit > 0, "limit must be positive", limit=limit)
        return []

    with expect(s, PreconditionError, "boundary passthrough"):
        query(-1)


def demo_hierarchy(s: Logger) -> None:
    s.info("ContractError subclasses AssertionError")
    assert issubclass(PreconditionError, ContractError)
    assert issubclass(ContractError, AssertionError)
    s.step("PreconditionError, ContractError, AssertionError: hierarchy holds")


def main() -> None:
    with log.span("offensive programming demo") as s:
        demo_require(s)
        demo_invariant(s)
        demo_ensure(s)
        demo_must(s)
        demo_sourced_error(s)
        demo_boundary_wraps(s)
        demo_boundary_passthrough(s)
        demo_hierarchy(s)
    log.success("all offensive primitives verified")


if __name__ == "__main__":
    main()
