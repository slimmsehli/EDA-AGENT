#!/usr/bin/env python3
"""Local HTTP MCP server for inspecting VCD simulation traces."""

import bisect
import heapq
import json
import os
import re
import uuid
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP as Server
    _V1 = True
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as Server
    _V1 = False


HOST = "127.0.0.1"
PORT = 8766
SERVER_NAME = "vcd_debug"
MAX_FILE_BYTES = int(os.environ.get("VCD_MAX_FILE_BYTES", str(128 * 1024 * 1024)))
MAX_CHANGES = int(os.environ.get("VCD_MAX_CHANGES", "2000000"))
MAX_OPEN_SESSIONS = int(os.environ.get("VCD_MAX_OPEN_SESSIONS", "4"))
MAX_PAGE_SIZE = 5000

mcp = Server(SERVER_NAME, host=HOST, port=PORT) if _V1 else Server(SERVER_NAME)
_sessions = {}


def _json_result(value):
    return json.dumps(value, ensure_ascii=False)


def _allowed_roots():
    configured = os.environ.get("VCD_ALLOWED_ROOTS")
    roots = configured.split(os.pathsep) if configured else [os.getcwd()]
    return [Path(root).expanduser().resolve() for root in roots if root]


def _source_file(path):
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError(f"VCD path is not a file: {source}")
    if not any(source.is_relative_to(root) for root in _allowed_roots()):
        raise ValueError(
            "VCD file is outside the allowed roots. Set VCD_ALLOWED_ROOTS to "
            "one or more trusted directories."
        )
    size = source.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(
            f"VCD file is {size} bytes; the configured limit is {MAX_FILE_BYTES}."
        )
    return source


def _consume_to_end(tokens):
    parts = []
    for token in tokens:
        if token == "$end":
            break
        parts.append(token)
    return parts


def _parse_vcd(source):
    scopes = []
    signals = []
    identifiers = {}
    timescale = None
    current_time = 0
    previous_timestamp = 0
    start_time = None
    end_time = 0
    change_count = 0
    enddefinitions_seen = False
    token_pattern = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*|s"(?:\\.|[^"\\])*"|"(?:\\.|[^"\\])*"|[^\s]+')

    def tokens():
        with source.open("r", encoding="utf-8", errors="strict") as vcd_file:
            for line in vcd_file:
                yield from token_pattern.findall(line)

    stream = iter(tokens())

    for token in stream:
        if token.startswith("$"):
            if token == "$scope":
                parts = _consume_to_end(stream)
                if len(parts) < 2:
                    raise ValueError("Malformed $scope declaration in VCD file.")
                scopes.append(parts[1])
            elif token == "$upscope":
                _consume_to_end(stream)
                if not scopes:
                    raise ValueError("VCD contains an unmatched $upscope.")
                scopes.pop()
            elif token == "$var":
                parts = _consume_to_end(stream)
                if len(parts) < 4:
                    raise ValueError("Malformed $var declaration in VCD file.")
                signal_type, width_text, identifier = parts[:3]
                try:
                    width = int(width_text)
                except ValueError as error:
                    raise ValueError(f"Invalid signal width: {width_text}") from error
                if width < 1:
                    raise ValueError(f"Invalid signal width: {width}.")
                reference = " ".join(parts[3:])
                range_match = re.search(r"\[[^\]]+\]", reference)
                signal_name = reference[:range_match.start()].rstrip() if range_match else reference
                signal_range = range_match.group(0) if range_match else None
                full_name = ".".join([*scopes, signal_name])
                signal = {
                    "signal_ref": f"sig_{len(signals) + 1:06d}",
                    "name": full_name,
                    "reference": signal_name,
                    "scope": ".".join(scopes),
                    "type": signal_type,
                    "width": width,
                    "range": signal_range,
                    "identifier": identifier,
                }
                signals.append(signal)
                identifiers.setdefault(identifier, []).append(signal)
            elif token == "$timescale":
                parts = _consume_to_end(stream)
                timescale = " ".join(parts)
            elif token == "$enddefinitions":
                _consume_to_end(stream)
                enddefinitions_seen = True
            elif token in ("$comment", "$date", "$version"):
                _consume_to_end(stream)
            elif token in ("$dumpvars", "$dumpall", "$dumpon", "$dumpoff"):
                continue
            elif token == "$end":
                continue
            else:
                _consume_to_end(stream)
            continue

        if token.startswith("#"):
            try:
                current_time = int(token[1:])
            except ValueError as error:
                raise ValueError(f"Invalid VCD timestamp: {token}") from error
            if current_time < 0:
                raise ValueError(f"VCD timestamp must not be negative: {token}")
            if current_time < previous_timestamp:
                raise ValueError("VCD timestamps must be in nondecreasing order.")
            previous_timestamp = current_time
            start_time = current_time if start_time is None else min(start_time, current_time)
            end_time = max(end_time, current_time)
            continue

        value = None
        identifier = None
        if len(token) > 1 and token[0].lower() in "01xz":
            value, identifier = token[0].lower(), token[1:]
        elif token and token[0].lower() in ("b", "r", "s"):
            try:
                identifier = next(stream)
            except StopIteration as error:
                raise ValueError("Incomplete VCD value change at end of file.") from error
            value = token[1:]
            if token[0].lower() == "b":
                value = value.lower()
                if not value or re.fullmatch(r"[01xz]+", value) is None:
                    raise ValueError(f"Invalid vector value in VCD: {token}")
                declared = identifiers.get(identifier, ())
                if declared:
                    width = declared[0]["width"]
                    if len(value) < width:
                        padding = value[0] if value[0] in "xz" else "0"
                        value = padding * (width - len(value)) + value
        else:
            continue

        if identifier not in identifiers:
            raise ValueError(f"VCD value references undeclared identifier {identifier!r}.")
        change_count += 1
        if change_count > MAX_CHANGES:
            raise ValueError(
                f"VCD exceeds the configured change limit of {MAX_CHANGES}; "
                "raise VCD_MAX_CHANGES only if sufficient memory is available."
            )
        for signal in identifiers[identifier]:
            signal.setdefault("times", []).append(current_time)
            signal.setdefault("values", []).append(value)

    if not enddefinitions_seen:
        raise ValueError("VCD is missing $enddefinitions.")
    if not signals:
        raise ValueError("VCD contains no signal declarations.")
    for aliases in identifiers.values():
        names = [signal["name"] for signal in aliases]
        for signal in aliases:
            signal["aliases"] = [name for name in names if name != signal["name"]]

    signals_by_ref = {signal["signal_ref"]: signal for signal in signals}
    signals_by_name = {}
    signals_by_reference = {}
    for signal in signals:
        signals_by_name.setdefault(signal["name"], []).append(signal)
        signals_by_reference.setdefault(signal["reference"], []).append(signal)

    return {
        "signals": signals,
        "signals_by_ref": signals_by_ref,
        "signals_by_name": signals_by_name,
        "signals_by_reference": signals_by_reference,
        "identifiers": identifiers,
        "timescale": timescale,
        "time_precision": timescale,
        "start_time": str(start_time if start_time is not None else 0),
        "end_time": str(end_time),
        "change_count": change_count,
        "scope_count": len({signal["scope"] for signal in signals}),
    }


def _session(session_id):
    try:
        return _sessions[session_id]
    except KeyError as error:
        raise ValueError(f"Unknown or closed VCD session: {session_id}") from error


def _signal_metadata(signal):
    return {
        "signal_ref": signal["signal_ref"],
        "name": signal["name"],
        "scope": signal["scope"],
        "type": signal["type"],
        "width": signal["width"],
        "range": signal["range"],
        "aliases": signal["aliases"],
    }


def _resolve_signal(session, name):
    by_ref = session["signals_by_ref"]
    if name in by_ref:
        return by_ref[name]
    matches = session["signals_by_name"].get(name, [])
    if not matches:
        matches = session["signals_by_reference"].get(name, [])
    if not matches:
        raise ValueError(f"No signal matches {name!r}. Use list_signals to inspect names.")
    if len(matches) > 1:
        choices = [signal["name"] for signal in matches[:20]]
        raise ValueError(
            f"Signal name {name!r} is ambiguous; use a full hierarchical name. "
            f"Matches: {choices}"
        )
    return matches[0]


def _parse_time(time):
    try:
        result = int(time)
    except (TypeError, ValueError) as error:
        raise ValueError("Time must be an integer number of VCD timestamp ticks.") from error
    if result < 0:
        raise ValueError("Time must not be negative.")
    return result


def _validate_window(start_time, end_time, limit, offset):
    start = _parse_time(start_time)
    end = _parse_time(end_time)
    if start > end:
        raise ValueError("start_time must be less than or equal to end_time.")
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}.")
    if offset < 0:
        raise ValueError("offset must not be negative.")
    return start, end


def _window_data(signals, start, end, limit, offset):
    initial_values = []
    identifiers = {}
    for signal in signals:
        identifiers.setdefault(signal["identifier"], []).append(signal)

    heap = []
    streams = []
    for identifier, aliases in identifiers.items():
        representative = aliases[0]
        times = representative.get("times", [])
        values = representative.get("values", [])
        initial_index = bisect.bisect_left(times, start) - 1
        initial = values[initial_index] if initial_index >= 0 else None
        for signal in aliases:
            initial_values.append({
                **_signal_metadata(signal),
                "value": initial,
                "has_value": initial is not None,
            })
        index = bisect.bisect_left(times, start)
        stop = bisect.bisect_right(times, end)
        streams.append((times, values, aliases, index, stop))
        stream_index = len(streams) - 1
        if index < stop:
            heapq.heappush(heap, (times[index], stream_index, index))

    page = []
    total_groups = 0
    while heap:
        timestamp = heap[0][0]
        changes = []
        while heap and heap[0][0] == timestamp:
            _, stream_index, event_index = heapq.heappop(heap)
            times, values, aliases, _, stop = streams[stream_index]
            for signal in aliases:
                changes.append({
                    "signal_ref": signal["signal_ref"],
                    "name": signal["name"],
                    "value": values[event_index],
                })
            next_index = event_index + 1
            streams[stream_index] = (times, values, aliases, next_index, stop)
            if next_index < stop:
                heapq.heappush(heap, (times[next_index], stream_index, next_index))
        if offset <= total_groups < offset + limit:
            page.append({"time": str(timestamp), "signals": changes})
        total_groups += 1

    next_offset = offset + len(page)
    return {
        "initial_values": initial_values,
        "changes": page,
        "total_timestamps": total_groups,
        "offset": offset,
        "next_offset": next_offset if next_offset < total_groups else None,
        "has_more": next_offset < total_groups,
    }


@mcp.tool()
def load_vcd(path: str) -> str:
    """Open and index a VCD file. Returns a session_id required by query tools."""
    if len(_sessions) >= MAX_OPEN_SESSIONS:
        raise ValueError(f"Maximum open VCD sessions reached ({MAX_OPEN_SESSIONS}).")
    source = _source_file(path)
    data = _parse_vcd(source)
    session_id = f"vcd_{uuid.uuid4().hex}"
    data["path"] = str(source)
    _sessions[session_id] = data
    return _json_result({
        "session_id": session_id,
        "file": str(source),
        "signal_count": len(data["signals"]),
        "scope_count": data["scope_count"],
        "start_time": data["start_time"],
        "end_time": data["end_time"],
        "timescale": data["timescale"],
        "time_precision": data["time_precision"],
        "value_change_count": data["change_count"],
    })


@mcp.tool()
def close_vcd(session_id: str) -> str:
    """Close a loaded VCD session and release its in-memory trace index."""
    if session_id not in _sessions:
        raise ValueError(f"Unknown or already closed VCD session: {session_id}")
    del _sessions[session_id]
    return _json_result({"closed": True, "session_id": session_id})


@mcp.tool()
def get_simulation_info(session_id: str) -> str:
    """Return trace duration, VCD timescale/precision, and signal/scope counts."""
    data = _session(session_id)
    return _json_result({
        "file": data["path"],
        "start_time": data["start_time"],
        "end_time": data["end_time"],
        "timescale": data["timescale"],
        "time_precision": data["time_precision"],
        "time_unit_note": "All query timestamps are integer ticks in the declared VCD timescale.",
        "signal_count": len(data["signals"]),
        "scope_count": data["scope_count"],
        "value_change_count": data["change_count"],
    })


@mcp.tool()
def list_signals(session_id: str, offset: int = 0, limit: int = 500) -> str:
    """List all declared VCD signals with stable refs; use offset/limit to paginate."""
    data = _session(session_id)
    if offset < 0 or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"offset must be nonnegative and limit between 1 and {MAX_PAGE_SIZE}.")
    selected = data["signals"][offset:offset + limit]
    next_offset = offset + len(selected)
    return _json_result({
        "signals": [_signal_metadata(signal) for signal in selected],
        "total": len(data["signals"]),
        "offset": offset,
        "next_offset": next_offset if next_offset < len(data["signals"]) else None,
        "has_more": next_offset < len(data["signals"]),
    })


@mcp.tool()
def get_signal_value(session_id: str, signal: str, time: str) -> str:
    """Return a signal's last recorded value at or before an integer VCD tick."""
    data = _session(session_id)
    item = _resolve_signal(data, signal)
    tick = _parse_time(time)
    times = item.get("times", [])
    index = bisect.bisect_right(times, tick) - 1
    return _json_result({
        **_signal_metadata(item),
        "time": str(tick),
        "value": item["values"][index] if index >= 0 else None,
        "has_value": index >= 0,
    })


@mcp.tool()
def get_signals_at_time(session_id: str, signals: list[str], time: str) -> str:
    """Return values at one timestamp for multiple signal refs or hierarchical names."""
    data = _session(session_id)
    tick = _parse_time(time)
    if not signals:
        raise ValueError("At least one signal must be supplied.")
    results = []
    for name in signals:
        try:
            item = _resolve_signal(data, name)
        except ValueError as error:
            results.append({"signal": name, "error": str(error)})
            continue
        times = item.get("times", [])
        index = bisect.bisect_right(times, tick) - 1
        results.append({
            **_signal_metadata(item),
            "time": str(tick),
            "value": item["values"][index] if index >= 0 else None,
            "has_value": index >= 0,
        })
    return _json_result({"time": str(tick), "signals": results})


@mcp.tool()
def get_signal_window(
    session_id: str,
    signal: str,
    start_time: str,
    end_time: str,
    limit: int = 500,
    offset: int = 0,
) -> str:
    """Return a signal's pre-window value and all value changes in the inclusive tick range."""
    data = _session(session_id)
    start, end = _validate_window(start_time, end_time, limit, offset)
    item = _resolve_signal(data, signal)
    result = _window_data([item], start, end, limit, offset)
    return _json_result({**result, "signal": _signal_metadata(item), "start_time": str(start), "end_time": str(end)})


@mcp.tool()
def get_signals_window(
    session_id: str,
    signals: list[str],
    start_time: str,
    end_time: str,
    limit: int = 500,
    offset: int = 0,
) -> str:
    """Return multiple signals' values and merged transitions over an inclusive tick range."""
    data = _session(session_id)
    start, end = _validate_window(start_time, end_time, limit, offset)
    if not signals:
        raise ValueError("At least one signal must be supplied.")
    resolved = []
    errors = []
    for name in signals:
        try:
            resolved.append(_resolve_signal(data, name))
        except ValueError as error:
            errors.append({"signal": name, "error": str(error)})
    resolved = list({item["signal_ref"]: item for item in resolved}.values())
    if not resolved and errors:
        raise ValueError(f"No requested signals could be resolved: {errors}")
    result = _window_data(resolved, start, end, limit, offset)
    return _json_result({
        **result,
        "signals": [_signal_metadata(item) for item in resolved],
        "errors": errors,
        "start_time": str(start),
        "end_time": str(end),
    })


@mcp.tool()
def get_next_edge(
    session_id: str,
    signal: str,
    after_time: str,
    edge: str = "either",
) -> str:
    """Find the next rising, falling, or either known edge strictly after a VCD tick."""
    data = _session(session_id)
    item = _resolve_signal(data, signal)
    after = _parse_time(after_time)
    if edge not in ("rising", "falling", "either"):
        raise ValueError("edge must be 'rising', 'falling', or 'either'.")
    if item["width"] != 1 or item["type"] in ("real", "realtime", "string"):
        raise ValueError("Edge queries require a one-bit logic signal.")

    times = item.get("times", [])
    values = item.get("values", [])
    index = bisect.bisect_right(times, after)
    for current in range(index, len(times)):
        current_value = values[current]
        previous_value = values[current - 1] if current > 0 else None
        if previous_value not in ("0", "1") or current_value not in ("0", "1"):
            continue
        found = (
            previous_value == "0" and current_value == "1" and edge in ("rising", "either")
        ) or (
            previous_value == "1" and current_value == "0" and edge in ("falling", "either")
        )
        if found:
            return _json_result({
                **_signal_metadata(item),
                "edge": "rising" if current_value == "1" else "falling",
                "time": str(times[current]),
                "previous_value": previous_value,
                "value": current_value,
            })
    return _json_result({
        **_signal_metadata(item),
        "edge": None,
        "time": None,
        "after_time": str(after),
        "found": False,
    })


if __name__ == "__main__":
    if _V1:
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
