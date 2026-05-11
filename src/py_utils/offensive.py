"""
Typed errors and forensics at boundaries.

    "A confused program SHOULD scream." — John Carmack

Python is already offensive by default — exceptions propagate, uncaught
crashes the process, `assert` is a keyword. This module does NOT replace
`assert`. It fills the one real gap Python has (typed forensics at
external-system boundaries) and adds a typed assertion complement for the
narrow case of catch-boundaries that route on bug-class.

Center of gravity
    @boundary(source)       decorator: wrap raw exceptions into SourcedError
    SourcedError            typed error carrying source/operation/status/
                            context/__cause__, with .to_dict() for transport

Ergonomic helper
    must(value, msg, **ctx)  unwrap Optional[T] → T (raises InvariantError if None)

Typed assertions — for catch-boundaries that route on whose bug it is
(HTTP handlers, worker loops). In scripts, plain `assert` is fine.
    require(cond, msg, **ctx)    precondition:  caller is wrong
    invariant(cond, msg, **ctx)  internal state: we are wrong
    ensure(cond, msg, **ctx)     postcondition: we broke our promise

Exception hierarchy
    AssertionError
    └── ContractError
        ├── PreconditionError   (require)
        ├── InvariantError      (invariant, must)
        └── PostconditionError  (ensure)
    Exception
    └── SourcedError

@boundary wraps raw exceptions into SourcedError but lets ContractError pass
through unwrapped — contract failures are bugs in us, not failures of the
external source, and must not be mislabeled.

Every failure logs structurally via py_utils.log before raising, so forensics
survive even if the exception is swallowed upstream.

Decision table
    Script or CLI                               → assert x, f"..."
    Calling an external system                  → @boundary("source")
    Unwrapping Optional[T] where None is a bug  → must(value, ...)
    Handler mapping exceptions to HTTP status   → require / invariant / ensure
    Anywhere else                               → assert is fine

See README for examples. Module name stays `offensive` for cross-language
lineage with go-utils/offensive.go — the Carmack principle is the thread:
scream at boundaries, carry forensics, type your bugs so catch sites can
route them.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from .log import log

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class ContractError(AssertionError):
    """Base class for contract violations. Subclasses AssertionError for compat."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        if not self.context:
            return self.message
        ctx = " ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{self.message} [{ctx}]"


class PreconditionError(ContractError):
    """A require() check failed — caller violated the contract."""


class InvariantError(ContractError):
    """An invariant() check failed — internal state is inconsistent."""


class PostconditionError(ContractError):
    """An ensure() check failed — function failed to deliver its promise."""


def _format_context(context: dict[str, Any]) -> str:
    if not context:
        return ""
    return " ".join(f"{k}={v!r}" for k, v in context.items())


def _fail(exc_cls: type[ContractError], message: str, context: dict[str, Any]) -> None:
    ctx = _format_context(context)
    log.error(f"{message} [{ctx}]" if ctx else message)
    raise exc_cls(message, context)


def require(
    condition: bool, message: str = "precondition failed", **context: Any
) -> None:
    """Precondition check. Raises PreconditionError with structured context on failure.

    Use at function entry to validate caller-supplied arguments.

    Example:
        def charge(customer_id: str, amount: int) -> Charge:
            require(amount > 0, "amount must be positive", amount=amount)
            require(customer_id, "customer_id required", customer_id=customer_id)
            ...
    """
    if not condition:
        _fail(PreconditionError, message, context)


def invariant(
    condition: bool, message: str = "invariant violated", **context: Any
) -> None:
    """Invariant check. Raises InvariantError with structured context on failure.

    Use mid-function to assert that internal state holds. If this fires, the bug
    is in *our* code, not the caller's.

    Example:
        invariant(self.balance >= 0, "balance went negative", user=self.id, balance=self.balance)
    """
    if not condition:
        _fail(InvariantError, message, context)


def ensure(
    condition: bool, message: str = "postcondition failed", **context: Any
) -> None:
    """Postcondition check. Raises PostconditionError with structured context on failure.

    Use before returning to verify the function delivered what it promised.

    Example:
        result = fetch_user(id)
        ensure(result is not None, "fetch_user returned None", id=id)
        return result
    """
    if not condition:
        _fail(PostconditionError, message, context)


def must(
    value: T | None, message: str = "expected non-None value", **context: Any
) -> T:
    """Unwrap Optional[T] → T. Raises InvariantError if None.

    Python's closest analogue to Go's Must() for (T, error) pairs. Use when a value
    must exist at this point in the program and its absence is a bug, not a handled case.

    Example:
        user = must(users.get(user_id), "user not found", user_id=user_id)
        # user: User (not User | None)
    """
    if value is None:
        _fail(InvariantError, message, context)
    return cast(T, value)


class SourcedError(Exception):
    """Error from a named external source with structured context.

    Raise these at boundaries with the messy world (HTTP APIs, databases, external
    processes). Every SourcedError carries enough context to reconstruct the failure
    without a debugger: which system, which operation, HTTP status if applicable,
    the underlying exception, and arbitrary keyword context.

    Example:
        try:
            return stripe.Charge.create(customer=cid, amount=amt)
        except stripe.error.StripeError as e:
            raise SourcedError(
                source="stripe",
                operation="charge_customer",
                message=str(e),
                status=getattr(e, "http_status", None),
                cause=e,
                customer_id=cid,
                amount=amt,
            )

    Prefer the @boundary("stripe") decorator for call sites that just want to
    auto-wrap every thrown exception.
    """

    def __init__(
        self,
        source: str,
        operation: str,
        message: str,
        *,
        status: int | None = None,
        cause: BaseException | None = None,
        **context: Any,
    ) -> None:
        self.source = source
        self.operation = operation
        self.status = status
        self.context: dict[str, Any] = context
        full = f"[{source}:{operation}] {message}"
        if status is not None:
            full = f"[{source}:{operation} status={status}] {message}"
        super().__init__(full)
        if cause is not None:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Serializable representation for transport across process boundaries."""
        return {
            "source": self.source,
            "operation": self.operation,
            "status": self.status,
            "message": str(self.args[0]) if self.args else "",
            "context": self.context,
            "cause": repr(self.__cause__) if self.__cause__ else None,
        }


def boundary(source: str, operation: str | None = None) -> Callable[[F], F]:
    """Decorator: wrap any exception raised by the function into a SourcedError.

    The operation defaults to the function name. SourcedError instances pass through
    unchanged — if you raise one explicitly with more context, the decorator respects it.

    Example:
        @boundary("stripe")
        def charge(customer_id: str, amount: int) -> Charge:
            return stripe.Charge.create(customer=customer_id, amount=amount)

        # Any stripe exception auto-wraps into:
        # SourcedError(source="stripe", operation="charge", cause=<original>)
    """

    def decorator(fn: F) -> F:
        op = operation or fn.__name__

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except SourcedError:
                raise
            except ContractError:
                # Contract violations are bugs in us, not the external source.
                raise
            except Exception as e:
                status = getattr(e, "status_code", None) or getattr(
                    e, "http_status", None
                )
                status_part = f" status={status}" if status is not None else ""
                log.error(f"[{source}:{op}{status_part}] {type(e).__name__}: {e}")
                raise SourcedError(
                    source=source,
                    operation=op,
                    message=str(e) or type(e).__name__,
                    status=status,
                    cause=e,
                ) from e

        return cast(F, wrapper)

    return decorator
