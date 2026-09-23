"""
Minimal WebUntis JSON-RPC 2.0 client.

Replaces the vendored python-webuntis fork (formerly a git submodule): this
implements only what TimetableService actually needs - login/logout,
schoolyears, subject/room/class name lookups, and a teacher's timetable
queried by name (the one feature the fork added on top of upstream
python-webuntis, since upstream only supported numeric teacher IDs).
"""
import base64
import hashlib
import hmac
import re
import struct
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import requests

_TEACHER_ELEMENT_TYPE = 2


class WebUntisError(Exception):
    """Base class for all WebUntis-specific errors."""


class RemoteError(WebUntisError):
    """The server returned a JSON-RPC error response, or a malformed one."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class AuthError(RemoteError):
    """Errors while logging in."""


class BadCredentialsError(AuthError):
    """Invalid or missing username or password."""


class NotLoggedInError(AuthError):
    """The session expired or we never logged in."""


_ERROR_CODES = {
    -8504: BadCredentialsError,
    -8520: NotLoggedInError,
}
"""WebUntis JSON-RPC error codes this client knows how to interpret."""


@dataclass
class SchoolYear:
    id: int
    name: str
    start: datetime
    end: datetime


@dataclass
class Element:
    id: int
    name: str
    long_name: str


def _normalize_server_url(url: str) -> str:
    """
    Accepts a bare hostname or a full URL and returns a full WebUntis
    JSON-RPC endpoint URL, e.g. "my-school.webuntis.com" becomes
    "https://my-school.webuntis.com/WebUntis/jsonrpc.do".
    """
    if not re.match(r'^https?://', url):
        url = 'https://' + url

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError('Not a valid URL or hostname')

    path = parsed.path if parsed.path not in ('', '/') else '/WebUntis/jsonrpc.do'
    return f'{parsed.scheme}://{parsed.netloc}{path}'


def _parse_date(value: int) -> datetime:
    return datetime.strptime(str(value), '%Y%m%d')


def _totp(secret: str, digits: int = 6, period: int = 30) -> int:
    """
    RFC 6238 TOTP, computed from the Base32 "Schlüssel" shown alongside the
    WebUntis mobile app QR code (profile > Freigaben). This is the same
    secret WebUntis's own mobile app uses, so it authenticates independently
    of however the user signs into the web page (password or an SSO
    provider like IServ's "Anmelden über iserv", which has no equivalent
    JSON-RPC login).
    """
    padded = secret.strip().upper()
    padded += '=' * (-len(padded) % 8)
    key = base64.b32decode(padded)
    counter = struct.pack('>Q', int(time.time()) // period)
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % (10 ** digits)
    return code


class Session:
    """A WebUntis JSON-RPC 2.0 session (login, query, logout)."""

    def __init__(self, server: str, school: str, username: str, useragent: str,
                 password: Optional[str] = None, secret: Optional[str] = None):
        if not password and not secret:
            raise ValueError('Session requires either a password or a secret')
        self.url = _normalize_server_url(server) + '?school=' + school
        self.useragent = useragent
        self.username = username
        self.password = password
        self.secret = secret
        self._jsessionid: Optional[str] = None
        self._http = requests.Session()

    def login(self) -> 'Session':
        """
        Raises:
            BadCredentialsError, AuthError, RemoteError: see _request.
            requests.exceptions.RequestException: on network-level failures.
        """
        if self.secret:
            return self._login_with_secret()

        result = self._request('authenticate', {
            'user': self.username,
            'password': self.password,
            'client': self.useragent,
        })

        if 'sessionId' not in result:
            raise AuthError('Something went wrong while authenticating')
        self._jsessionid = result['sessionId']
        return self

    def _login_with_secret(self) -> 'Session':
        """
        Logs in via the shared secret from WebUntis profile > Freigaben,
        using a TOTP the same way the official mobile app does (see
        _totp). Unlike the password login, the session id comes back as a
        Set-Cookie header rather than in the JSON body.
        """
        url = self.url.replace('/WebUntis/jsonrpc.do', '/WebUntis/jsonrpc_intern.do')
        url += '&m=getUserData2017&v=i2.2'
        body = {
            'id': str(time.time()),
            'method': 'getUserData2017',
            'params': [{
                'auth': {
                    'clientTime': int(time.time() * 1000),
                    'user': self.username,
                    'otp': _totp(self.secret),
                },
            }],
            'jsonrpc': '2.0',
        }
        headers = {
            'User-Agent': self.useragent,
            'Content-Type': 'application/json',
        }
        response = self._http.post(url, json=body, headers=headers)

        try:
            result = response.json()
        except ValueError:
            raise RemoteError(f'Invalid JSON: {response.text[:200]}')

        if 'error' in result:
            error = result['error']
            code = error.get('code')
            message = error.get('message', 'Login with the secret key failed.')
            raise _ERROR_CODES.get(code, RemoteError)(message, code)

        session_id = self._http.cookies.get('JSESSIONID')
        if not session_id:
            raise AuthError('Something went wrong while authenticating with the secret key')
        self._jsessionid = session_id
        return self

    def logout(self):
        if self._jsessionid is None:
            return
        try:
            self._request('logout')
        finally:
            self._jsessionid = None

    def schoolyears(self) -> List[SchoolYear]:
        result = self._request('getSchoolyears')
        return [
            SchoolYear(
                id=sy['id'],
                name=sy['name'],
                start=_parse_date(sy['startDate']),
                end=_parse_date(sy['endDate']),
            )
            for sy in result
        ]

    def subjects(self) -> List[Element]:
        return self._elements('getSubjects')

    def rooms(self) -> List[Element]:
        return self._elements('getRooms')

    def klassen(self) -> List[Element]:
        return self._elements('getKlassen')

    def _elements(self, method: str) -> List[Element]:
        result = self._request(method)
        return [
            Element(id=e['id'], name=e.get('name', ''), long_name=e.get('longName', ''))
            for e in result
        ]

    def timetable_extended(self, start: int, end: int, teacher: str, teacher_fields: List[str],
                            is_part_time: bool = False) -> List[dict]:
        """
        Fetch a teacher's timetable, looked up by name (not numeric ID),
        for the given date range (as YYYYMMDD ints).

        `is_part_time` is ignored here - WebUntis has no concept of it, it's
        purely local mycartime app state. It's only accepted so callers can
        pass it uniformly to a real or mock Session (see MockSession, which
        uses it to fabricate a plausible part-time schedule).

        Returns:
            The raw list of period dicts, exactly as WebUntis sends them
            (e.g. each with 'date', 'startTime', 'endTime', 'te', 'su', ...).
        """
        options = {
            'element': {'id': teacher, 'type': _TEACHER_ELEMENT_TYPE, 'keyType': 'name'},
            'startDate': start,
            'endDate': end,
            'teacherFields': teacher_fields,
            'onlyBaseTimetable': False,
            'showBooking': True,
            'showInfo': True,
            'showSubstText': True,
            'showLsText': True,
            'showLsNumber': True,
            'showStudentgroup': True,
        }
        return self._request('getTimetable', {'options': options})

    def _request(self, method: str, params: Optional[dict] = None):
        """
        Send a single WebUntis JSON-RPC 2.0 request and return its 'result'.

        Raises:
            NotLoggedInError: if called before login() (except for
                'authenticate' itself).
            BadCredentialsError, AuthError, RemoteError: on a JSON-RPC error
                response, based on its error code.
            RemoteError: if the response isn't valid JSON, or its 'id'
                doesn't match the request's - both usually mean the server
                answered with something other than a normal WebUntis
                response (e.g. an HTML error page for a wrong school id).
        """
        headers = {
            'User-Agent': self.useragent,
            'Content-Type': 'application/json',
        }
        if method != 'authenticate':
            if self._jsessionid is None:
                raise NotLoggedInError("Don't have a session. Did you already log out?")
            headers['Cookie'] = f'JSESSIONID={self._jsessionid}'

        request_id = str(time.time())
        body = {
            'id': request_id,
            'method': method,
            'params': params or {},
            'jsonrpc': '2.0',
        }
        response = self._http.post(self.url, json=body, headers=headers)

        try:
            result = response.json()
        except ValueError:
            raise RemoteError(f'Invalid JSON: {response.text[:200]}')

        if result.get('id') != request_id:
            raise RemoteError(
                f"Request ID was not the same one as returned. {request_id} -- {result.get('id')}"
            )

        if 'result' in result:
            return result['result']

        error = result.get('error', {})
        code = error.get('code')
        message = error.get('message', 'Some error happened and there is no information provided what went wrong.')
        raise _ERROR_CODES.get(code, RemoteError)(message, code)
