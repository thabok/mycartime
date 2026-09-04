"""
AI assistant service: explains the driving plan / members and proposes
edits, backed by the Anthropic API with a `claude` CLI fallback.

Both backends are given the same system prompt and are expected to answer
with a single fenced ```json envelope (see SKILL.md), so there is exactly
one response-parsing path regardless of which backend answered.
"""
import json
import logging
import os
import re
import subprocess
import threading

import config

logger = logging.getLogger(__name__)

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.join(_MODULE_DIR, 'assistant', 'skill')
_REPO_ROOT = os.path.abspath(os.path.join(_MODULE_DIR, '..', '..'))
_INTERNAL_DOC_PATH = os.path.join(_REPO_ROOT, 'doc', 'internal_doc.md')
_DEBUG_LOG_PATH = os.path.join(_MODULE_DIR, 'backend_debug.log')

_DEBUG_LOG_TAIL_LINES = 500
_DEBUG_LOG_TAIL_MAX_CHARS = 20000

_JSON_ENVELOPE_RE = re.compile(r'```(?:json)?\s*(\{.*\})\s*```', re.DOTALL)


def _read_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except OSError as e:
        logger.warning(f"Could not read {path}: {e}")
        return ''


def _algorithm_notes() -> str:
    doc = _read_file(_INTERNAL_DOC_PATH)
    if not doc:
        return ''
    start = doc.find('## Algorithm')
    end = doc.find('## User Interface')
    if start == -1:
        return ''
    return doc[start:end if end != -1 else None].strip()


def _debug_log_tail() -> str:
    content = _read_file(_DEBUG_LOG_PATH)
    if not content:
        return ''
    lines = content.splitlines()[-_DEBUG_LOG_TAIL_LINES:]
    tail = '\n'.join(lines)
    return tail[-_DEBUG_LOG_TAIL_MAX_CHARS:]


def build_system_prompt(context: dict) -> str:
    """Assemble the skill instructions, glossaries, algorithm reference and
    live app context into a single system prompt."""
    skill = _read_file(os.path.join(_SKILL_DIR, 'SKILL.md'))
    glossary_en = _read_file(os.path.join(_SKILL_DIR, 'glossary_en.md'))
    glossary_de = _read_file(os.path.join(_SKILL_DIR, 'glossary_de.md'))
    algorithm_notes = _algorithm_notes()
    debug_log = _debug_log_tail()

    app_context = {
        'members': context.get('members', []),
        'plan': context.get('plan'),
        'uiContext': context.get('uiContext', {}),
    }

    parts = [
        skill,
        '## Glossary (English)\n\n' + glossary_en,
        '## Glossar (Deutsch)\n\n' + glossary_de,
    ]
    if algorithm_notes:
        parts.append('## Algorithm reference\n\n' + algorithm_notes)
    parts.append('## Current app state (JSON)\n\n```json\n' + json.dumps(app_context) + '\n```')
    if debug_log:
        parts.append('## Recent backend log (tail)\n\n```\n' + debug_log + '\n```')

    return '\n\n'.join(parts)


def _parse_envelope(text: str) -> dict:
    match = _JSON_ENVELOPE_RE.search(text)
    candidate = match.group(1) if match else text.strip()
    try:
        envelope = json.loads(candidate)
        reply = envelope.get('reply')
        actions = envelope.get('actions')
        if isinstance(reply, str) and isinstance(actions, list):
            return {'reply': reply, 'actions': actions}
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning("Assistant response did not match the expected JSON envelope; returning raw text")
    return {'reply': text.strip(), 'actions': []}


_JSON_STRING_ESCAPES = {'"': '"', '\\': '\\', '/': '/', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}


def _extract_partial_reply(buffer: str) -> str | None:
    """Best-effort decode of the `"reply"` string value out of a (possibly
    incomplete) JSON envelope, so the UI can show it as it streams in rather
    than waiting for the closing fence. Returns None if the value hasn't
    started yet; otherwise the text decoded so far (which keeps growing,
    monotonically, as `buffer` grows)."""
    key_idx = buffer.find('"reply"')
    if key_idx == -1:
        return None
    colon_idx = buffer.find(':', key_idx + len('"reply"'))
    if colon_idx == -1:
        return None
    i = colon_idx + 1
    while i < len(buffer) and buffer[i] in ' \t\n\r':
        i += 1
    if i >= len(buffer) or buffer[i] != '"':
        return None
    i += 1

    out = []
    while i < len(buffer):
        ch = buffer[i]
        if ch == '"':
            break
        if ch == '\\':
            if i + 1 >= len(buffer):
                break  # escape sequence cut off mid-chunk; wait for more
            esc = buffer[i + 1]
            if esc == 'u':
                if i + 6 > len(buffer):
                    break  # \uXXXX cut off mid-chunk; wait for more
                try:
                    out.append(chr(int(buffer[i + 2:i + 6], 16)))
                except ValueError:
                    break
                i += 6
                continue
            mapped = _JSON_STRING_ESCAPES.get(esc)
            if mapped is None:
                break
            out.append(mapped)
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


class _PartialReplyTracker:
    """Incremental equivalent of calling `_extract_partial_reply` on the
    whole accumulated buffer after every chunk. Re-scanning and re-decoding
    the entire buffer from scratch on each of the (many, small) chunks a
    stream produces is O(reply length) *per chunk*, i.e. O(reply length^2)
    over a whole reply -- this instead remembers where it left off and
    returns only the newly decoded text, so total work stays O(reply
    length)."""

    def __init__(self):
        self._buffer = ''
        self._value_start: int | None = None
        self._pos = 0
        self._out: list[str] = []

    def feed(self, chunk: str) -> str | None:
        """Returns the newly decoded text from this chunk, or None if
        nothing new was decoded (value hasn't started yet, or stalled on an
        escape sequence cut off mid-chunk)."""
        self._buffer += chunk
        buf = self._buffer

        if self._value_start is None:
            key_idx = buf.find('"reply"')
            if key_idx == -1:
                return None
            colon_idx = buf.find(':', key_idx + len('"reply"'))
            if colon_idx == -1:
                return None
            i = colon_idx + 1
            while i < len(buf) and buf[i] in ' \t\n\r':
                i += 1
            if i >= len(buf) or buf[i] != '"':
                return None
            self._value_start = i + 1
            self._pos = self._value_start

        out_before = len(self._out)
        i = self._pos
        while i < len(buf):
            ch = buf[i]
            if ch == '"':
                break
            if ch == '\\':
                if i + 1 >= len(buf):
                    break  # escape sequence cut off mid-chunk; wait for more
                esc = buf[i + 1]
                if esc == 'u':
                    if i + 6 > len(buf):
                        break  # \uXXXX cut off mid-chunk; wait for more
                    try:
                        self._out.append(chr(int(buf[i + 2:i + 6], 16)))
                    except ValueError:
                        break
                    i += 6
                    continue
                mapped = _JSON_STRING_ESCAPES.get(esc)
                if mapped is None:
                    break
                self._out.append(mapped)
                i += 2
                continue
            self._out.append(ch)
            i += 1
        self._pos = i

        if len(self._out) == out_before:
            return None
        return ''.join(self._out[out_before:])


def _call_sdk_stream(system_prompt: str, messages: list[dict]):
    import anthropic

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=config.ASSISTANT_MODEL,
        max_tokens=config.ASSISTANT_MAX_TOKENS,
        system=system_prompt,
        messages=[{'role': m['role'], 'content': m['content']} for m in messages],
    ) as stream:
        yield from stream.text_stream


def _call_cli_stream(system_prompt: str, messages: list[dict]):
    transcript = '\n\n'.join(f"{m['role']}: {m['content']}" for m in messages)
    prompt = f"{system_prompt}\n\n---\n\nConversation so far:\n\n{transcript}\n\nRespond now as the assistant, following the JSON envelope contract above."

    # `--` marks end-of-options: the prompt can start with `-` (SKILL.md's
    # YAML frontmatter fence) which would otherwise be misparsed as a CLI flag.
    # `--include-partial-messages` (with `--verbose`, which stream-json
    # requires in print mode) is what gets us token-level text deltas
    # instead of one message dumped at the end.
    process = subprocess.Popen(
        ['claude', '-p', '--output-format', 'stream-json', '--include-partial-messages', '--verbose', '--', prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # An inactivity timeout, not a total-duration one: a real answer can take
    # well over ASSISTANT_CLI_TIMEOUT_SECONDS to finish once you count a large
    # system prompt (members/plan/debug log) plus a long streamed reply, so
    # the watchdog is reset on every line received and only fires if the CLI
    # actually stalls.
    timer = threading.Timer(config.ASSISTANT_CLI_TIMEOUT_SECONDS, process.kill)
    timer.start()
    try:
        for line in process.stdout:
            timer.cancel()
            timer = threading.Timer(config.ASSISTANT_CLI_TIMEOUT_SECONDS, process.kill)
            timer.start()
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get('type') != 'stream_event':
                continue
            inner = event.get('event', {})
            if inner.get('type') != 'content_block_delta':
                continue
            delta = inner.get('delta', {})
            if delta.get('type') == 'text_delta' and delta.get('text'):
                yield delta['text']
        process.wait()
    finally:
        timer.cancel()
        process.stdout.close()

    if process.returncode != 0:
        stderr = process.stderr.read()
        process.stderr.close()
        detail = ' (killed after inactivity timeout)' if process.returncode == -9 else ''
        raise RuntimeError(f"claude CLI exited {process.returncode}{detail}: {stderr.strip()}")
    process.stderr.close()


def _stream_chunks(system_prompt: str, messages: list[dict]):
    """Yield raw text chunks from whichever backend answers: the Anthropic
    SDK if an API key is configured, falling back to the claude CLI if the
    SDK errors out before producing any output (same fallback behavior as
    the old non-streaming implementation)."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        sdk_chunks = _call_sdk_stream(system_prompt, messages)
        try:
            first_chunk = next(sdk_chunks)
        except StopIteration:
            return
        except Exception as e:
            logger.warning(f"Anthropic SDK stream failed ({e}); falling back to claude CLI")
        else:
            yield first_chunk
            yield from sdk_chunks
            return

    yield from _call_cli_stream(system_prompt, messages)


def _is_valid_party_ref(plan: dict, day_key: str, party_ref: dict) -> dict | None:
    if not plan or not day_key or not isinstance(party_ref, dict):
        return None
    day_plan = (plan.get('dayPlans') or {}).get(day_key)
    if not day_plan:
        return None
    for party in day_plan.get('parties', []):
        if party.get('driver') == party_ref.get('driver') and party.get('time') == party_ref.get('time'):
            return party
    return None


def _find_day_key(plan: dict, day_unique_number) -> str | None:
    for key, day_plan in (plan.get('dayPlans') or {}).items():
        if day_plan.get('dayOfWeekABCombo', {}).get('uniqueNumber') == day_unique_number:
            return key
    return None


def _validate_move_passenger(action: dict, plan: dict) -> bool:
    """Same invariants as the Edit Day Plan dialog: same direction, and the
    target party must not be a lonely-driver (solo) party."""
    if not plan:
        return False
    day_key = _find_day_key(plan, action.get('dayUniqueNumber'))
    if not day_key:
        return False
    from_party = _is_valid_party_ref(plan, day_key, action.get('fromParty'))
    to_party = _is_valid_party_ref(plan, day_key, action.get('toParty'))
    if not from_party or not to_party:
        return False
    if from_party is to_party:
        return False
    if action.get('passenger') not in from_party.get('passengers', []):
        return False
    if from_party.get('schoolbound') != to_party.get('schoolbound'):
        return False
    if to_party.get('isLonelyDriver'):
        return False
    return True


def _drop_capacity_violating_move_passengers(actions: list[dict], plan: dict, members: list[dict]) -> list[dict]:
    """The assistant may propose several movePassenger actions in one
    response as a swap/batch (e.g. two passengers trading parties). A move
    that overfills a car partway through is fine as long as the *net*
    result across the whole batch respects every car's seat count, so
    capacity is checked once against the combined effect of all
    movePassenger actions rather than one action at a time."""
    move_actions = [a for a in actions if a.get('type') == 'movePassenger']
    if not move_actions or not plan:
        return actions

    seats_by_initials = {
        m.get('initials', '').lower(): m.get('numberOfSeats')
        for m in members if isinstance(m, dict)
    }

    net_change: dict[tuple, int] = {}
    for action in move_actions:
        day_key = _find_day_key(plan, action.get('dayUniqueNumber'))
        if not day_key:
            continue
        for party_ref, delta in ((action.get('fromParty'), -1), (action.get('toParty'), 1)):
            if not isinstance(party_ref, dict):
                continue
            party_key = (day_key, party_ref.get('driver'), party_ref.get('time'))
            net_change[party_key] = net_change.get(party_key, 0) + delta

    for (day_key, driver, time), change in net_change.items():
        if change <= 0:
            continue
        party = _is_valid_party_ref(plan, day_key, {'driver': driver, 'time': time})
        if not party:
            continue
        seats = seats_by_initials.get((driver or '').lower())
        if seats is None:
            continue
        if len(party.get('passengers', [])) + change > seats - 1:
            logger.warning(
                f"Dropping movePassenger batch: {driver}'s car would exceed capacity "
                f"({len(party.get('passengers', []))} passengers + {change} net > {seats - 1} seats)"
            )
            return [a for a in actions if a.get('type') != 'movePassenger']

    return actions


def _validate_actions(actions: list[dict], plan: dict, members: list[dict] | None = None) -> list[dict]:
    validated = []
    for action in actions:
        if not isinstance(action, dict) or 'type' not in action:
            continue
        if action['type'] == 'movePassenger' and not _validate_move_passenger(action, plan):
            logger.warning(f"Dropping invalid movePassenger action from assistant response: {action}")
            continue
        validated.append(action)
    return _drop_capacity_violating_move_passengers(validated, plan, members or [])


def ask_stream(messages: list[dict], context: dict):
    """Send the conversation + app context to Claude and yield incremental
    {"type": "delta", "text": str} events as the `reply` text streams in,
    followed by exactly one {"type": "final", "reply": str, "actions":
    list[dict]} event once the full response has been parsed and validated."""
    system_prompt = build_system_prompt(context)

    raw_chunks = []
    partial_reply_tracker = _PartialReplyTracker()
    for chunk in _stream_chunks(system_prompt, messages):
        raw_chunks.append(chunk)
        new_text = partial_reply_tracker.feed(chunk)
        if new_text:
            yield {'type': 'delta', 'text': new_text}

    envelope = _parse_envelope(''.join(raw_chunks))
    envelope['actions'] = _validate_actions(envelope['actions'], context.get('plan'), context.get('members'))
    yield {'type': 'final', 'reply': envelope['reply'], 'actions': envelope['actions']}


def ask(messages: list[dict], context: dict) -> dict:
    """Non-streaming convenience wrapper around `ask_stream` that returns
    just the final {"reply": str, "actions": list[dict]} envelope."""
    for event in ask_stream(messages, context):
        if event['type'] == 'final':
            return {'reply': event['reply'], 'actions': event['actions']}
    raise RuntimeError('assistant stream ended without a final response')
