"""
Minimal WebUntis JSON-RPC 2.0 client.

Replaces the vendored python-webuntis fork (formerly a git submodule): this
implements only what TimetableService actually needs - login/logout,
schoolyears, subject/room/class name lookups, and a teacher's timetable
queried by name (the one feature the fork added on top of upstream
python-webuntis, since upstream only supported numeric teacher IDs).
"""
import re
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


class Session:
    """A WebUntis JSON-RPC 2.0 session (login, query, logout)."""

    def __init__(self, server: str, school: str, username: str, password: str, useragent: str):
        self.url = _normalize_server_url(server) + '?school=' + school
        self.useragent = useragent
        self.username = username
        self.password = password
        self._jsessionid: Optional[str] = None
        self._http = requests.Session()

    def login(self) -> 'Session':
        """
        Raises:
            BadCredentialsError, AuthError, RemoteError: see _request.
            requests.exceptions.RequestException: on network-level failures.
        """
        result = self._request('authenticate', {
            'user': self.username,
            'password': self.password,
            'client': self.useragent,
        })

        if 'sessionId' not in result:
            raise AuthError('Something went wrong while authenticating')
        self._jsessionid = result['sessionId']
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

    def timetable_extended(self, start: int, end: int, teacher: str, teacher_fields: List[str]) -> List[dict]:
        """
        Fetch a teacher's timetable, looked up by name (not numeric ID),
        for the given date range (as YYYYMMDD ints).

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
