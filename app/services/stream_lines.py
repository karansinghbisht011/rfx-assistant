"""Spot each finished line of a quotation while the model is still writing the answer.

Only for the live preview: the complete answer is always validated separately, so a problem here can
at worst lose the preview, never the result.
"""

import json
import re

_LINES_KEY = re.compile(r'"lines"\s*:\s*\[')


class LineStreamParser:
    def __init__(self) -> None:
        self._buf = ""
        self._i = 0
        self._state = "seek"        # seek -> array -> obj -> array ... -> done
        self._depth = 0
        self._in_string = False
        self._escaped = False
        self._start = 0

    def feed(self, chunk: str) -> list[dict]:
        """Add streamed text; return every line object that became complete."""
        self._buf += chunk
        buf, found = self._buf, []
        while self._i < len(buf) and self._state != "done":
            if self._state == "seek":
                match = _LINES_KEY.search(buf, self._i)
                if not match:
                    self._i = max(self._i, len(buf) - 16)  # keep a tail: the key may be split across chunks
                    break
                self._i, self._state = match.end(), "array"
            elif self._state == "array":
                c = buf[self._i]
                if c == "{":
                    self._state, self._depth, self._start = "obj", 1, self._i
                    self._in_string = self._escaped = False
                elif c == "]":
                    self._state = "done"
                self._i += 1
            else:  # inside one line object
                c = buf[self._i]
                if self._in_string:
                    if self._escaped:
                        self._escaped = False
                    elif c == "\\":
                        self._escaped = True
                    elif c == '"':
                        self._in_string = False
                elif c == '"':
                    self._in_string = True
                elif c == "{":
                    self._depth += 1
                elif c == "}":
                    self._depth -= 1
                    if self._depth == 0:
                        try:
                            found.append(json.loads(buf[self._start:self._i + 1]))
                        except ValueError:
                            pass
                        self._state = "array"
                self._i += 1
        return found
