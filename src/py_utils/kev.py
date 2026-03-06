"""KEV - A Redis-style KV store for environment variables.

Default usage (no namespaces needed):
    api_key = kev.must_get("API_KEY")      # Raises if not found
    api_key = kev.get("API_KEY")           # Returns "" if not found
    api_key = kev.get("API_KEY", "dev")    # Returns "dev" if not found
    port = kev.int("PORT", 8080)           # With type conversion
    kev.set("DEBUG", "true")               # Sets in memory (fast)

    kev.get("DATABASE_URL")                # memory -> os -> .env -> cache result
    kev.get("DATABASE_URL")                # memory (cached!)

Customize the search order:
    kev.source.remove("os")                # Ignore OS env (perfect for tests!)
    kev.source.add(".env.local")           # Add more fallbacks
    kev.source.set(".env.test")            # Or replace entirely

Redis-style namespacing (when you need control):
    kev.get("os:PATH")                     # ONLY from OS, no fallback
    kev.get(".env:API_KEY")                # ONLY from .env file
    kev.set("os:DEBUG", "true")            # Write directly to OS
    kev.set(".env:API_KEY", "secret")      # Update .env file

Source tracking:
    value, source = kev.get_with_source("API_KEY")
    kev.source_of("API_KEY")               # ".env" or "os" or "default"
    kev.debug = True                       # Shows lookup chain
"""

from __future__ import annotations

import os
from pathlib import Path


class _SourceOps:
    def __init__(self, kev: Kev) -> None:
        self._kev = kev

    def set(self, *sources: str) -> None:
        self._kev._sources = list(sources)

    def add(self, *sources: str) -> None:
        self._kev._sources.extend(sources)

    def remove(self, *sources: str) -> None:
        self._kev._sources = [s for s in self._kev._sources if s not in sources]

    def list(self) -> list[str]:
        return list(self._kev._sources)

    def clear(self) -> None:
        self._kev._sources = []


class Kev:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[str, str]] = {}  # key -> (value, source)
        self._sources: list[str] = ["os", ".env"]
        self.source = _SourceOps(self)
        self.debug = False

    def _parse_key(self, key: str) -> tuple[str, str]:
        assert not key.startswith(":"), f"invalid key format - starts with colon: {key}"
        assert "::" not in key, f"invalid key format - double colon: {key}"
        if ":" in key:
            namespace, real_key = key.split(":", 1)
            assert namespace and real_key, (
                f"invalid key format - empty namespace or key: {key}"
            )
            return namespace, real_key
        return "", key

    def _get_from_namespace(self, namespace: str, key: str) -> str:
        if namespace == "os":
            return os.environ.get(key, "")
        if namespace.startswith(".") or "/" in namespace:
            return self._get_from_file(namespace, key)
        return ""

    def _get_from_file(self, path: str, key: str) -> str:
        try:
            for line in Path(path).read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) == 2 and parts[0].strip() == key:
                    value = parts[1].strip()
                    if (
                        len(value) >= 2
                        and value[0] in ('"', "'")
                        and value[-1] == value[0]
                    ):
                        value = value[1:-1]
                    return value
        except (FileNotFoundError, PermissionError):
            pass
        return ""

    def get(self, key: str, default: str = "") -> str:
        namespace, real_key = self._parse_key(key)
        _debug = self.debug and key != "LOG_LEVEL"

        if _debug:
            print(f"KEV: Looking for {key}")

        if namespace:
            val = self._get_from_namespace(namespace, real_key)
            if val:
                if _debug:
                    print(f"  + {namespace}: found {val}")
                return val
            if _debug:
                print(f"  - {namespace}: not found")
            return default

        # Check memory
        if real_key in self._memory:
            val, src = self._memory[real_key]
            if _debug:
                print(f"  + memory: {val} (from {src})")
            return val

        if _debug:
            print("  - memory: not found")

        # Search sources
        for source in self._sources:
            val = self._get_from_namespace(source, real_key)
            if val:
                if _debug:
                    print(f"  + {source}: found {val} (caching)")
                abs_source = (
                    str(Path(source).resolve())
                    if source not in ("os", "default", "set")
                    else source
                )
                self._memory[real_key] = (val, abs_source)
                return val
            if _debug:
                print(f"  - {source}: not found")

        # Cache default
        if default:
            if _debug:
                print(f"  -> using default: {default} (caching)")
            self._memory[real_key] = (default, "default")
            return default

        if _debug:
            print("  -> not found, returning empty")
        return ""

    def must_get(self, key: str) -> str:
        val = self.get(key)
        assert val, f"required key not found: {key}"
        return val

    def source_of(self, key: str) -> str:
        if key in self._memory:
            return self._memory[key][1]
        return ""

    def get_with_source(self, key: str, default: str = "") -> tuple[str, str]:
        value = self.get(key, default)
        if value:
            source = self.source_of(key)
            if not source:
                namespace, _ = self._parse_key(key)
                if namespace:
                    source = namespace
            return value, source
        return "", ""

    def set(self, key: str, value: str) -> None:
        namespace, real_key = self._parse_key(key)
        if namespace:
            self._set_to_namespace(namespace, real_key, value)
        else:
            self._memory[real_key] = (value, "set")

    def _set_to_namespace(self, namespace: str, key: str, value: str) -> None:
        if namespace == "os":
            os.environ[key] = value
        elif namespace.startswith(".") or "/" in namespace:
            self._set_to_file(namespace, key, value)

    def _set_to_file(self, path: str, key: str, value: str) -> None:
        lines: list[str] = []
        found = False
        p = Path(path)

        if p.exists():
            for line in p.read_text().splitlines():
                trimmed = line.strip()
                if not trimmed or trimmed.startswith("#"):
                    lines.append(line)
                    continue
                parts = trimmed.split("=", 1)
                if parts[0].strip() == key:
                    qval = f'"{value}"' if any(c in value for c in " \t\n") else value
                    lines.append(f"{key}={qval}")
                    found = True
                else:
                    lines.append(line)

        if not found:
            qval = f'"{value}"' if any(c in value for c in " \t\n") else value
            lines.append(f"{key}={qval}")

        p.write_text("\n".join(lines))

    def has(self, key: str) -> bool:
        """Returns True if get() would return a non-empty value.

        Includes cached defaults — use source_of() or get_with_source()
        to distinguish where a value came from.
        """
        namespace, real_key = self._parse_key(key)
        if namespace:
            return bool(self._get_from_namespace(namespace, real_key))
        if real_key in self._memory:
            return True
        return any(bool(self._get_from_namespace(s, real_key)) for s in self._sources)

    def int(self, key: str, default: int) -> int:
        val = self.get(key)
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            raise AssertionError(f"invalid int value for {key}: {val}")

    def bool(self, key: str, default: bool) -> bool:
        val = self.get(key).lower()
        if not val:
            return default
        if val in ("true", "1", "yes", "on"):
            return True
        if val in ("false", "0", "no", "off"):
            return False
        raise AssertionError(f"invalid bool value for {key}: {val}")

    def float(self, key: str, default: float) -> float:
        val = self.get(key)
        if not val:
            return default
        try:
            return float(val)
        except ValueError:
            raise AssertionError(f"invalid float value for {key}: {val}")

    def keys(self, pattern: str = "*") -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        namespace, key_pattern = self._parse_key(pattern)

        if namespace:
            for k in self._keys_from_namespace(namespace, key_pattern):
                full = f"{namespace}:{k}"
                if full not in seen:
                    result.append(full)
                    seen.add(full)
        else:
            for k in self._memory:
                if _match(k, key_pattern) and k not in seen:
                    result.append(k)
                    seen.add(k)
            for source in self._sources:
                for k in self._keys_from_namespace(source, key_pattern):
                    if k not in seen:
                        result.append(k)
                        seen.add(k)
        return result

    def _keys_from_namespace(self, namespace: str, pattern: str) -> list[str]:
        if namespace == "os":
            return [k for k in os.environ if _match(k, pattern)]
        if namespace.startswith(".") or "/" in namespace:
            keys: list[str] = []
            try:
                for line in Path(namespace).read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("=", 1)
                    if parts and _match(parts[0].strip(), pattern):
                        keys.append(parts[0].strip())
            except (FileNotFoundError, PermissionError):
                pass
            return keys
        return []

    def clear(self, *patterns: str) -> None:
        for p in patterns:
            assert ":" not in p, (
                "clear() with namespace is dangerous! Use unset() for namespaced keys."
            )
        if not patterns:
            self._memory.clear()
            return
        for p in patterns:
            for k in list(self._memory):
                if _match(k, p):
                    del self._memory[k]

    def unset(self, *keys: str) -> None:
        for key in keys:
            namespace, real_key = self._parse_key(key)
            if namespace == "os":
                os.environ.pop(real_key, None)
            elif not namespace:
                self._memory.pop(real_key, None)


def _match(key: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return key.startswith(pattern[:-1])
    if pattern.startswith("*"):
        return key.endswith(pattern[1:])
    if "*" in pattern:
        parts = pattern.split("*", 1)
        return key.startswith(parts[0]) and key.endswith(parts[1])
    return key == pattern


kev = Kev()
