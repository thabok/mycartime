import pytest
import requests_mock

from carpoolparty import UntisAdapter
from carpoolparty.src.services.untis.UntisAdapter import UntisAdapter


def test_login_success():
    with requests_mock.Mocker() as m:
        # fake user data
        username = "john_doe"
        password = "secret"
        fake_school_name = "Hogwarts"
        fake_session_id = "token1337"

        # create untis adapter (sut)
        adapter = UntisAdapter(school_name=fake_school_name)

        # prepare request mock endpoint
        success_response = { "result": { "sessionId": fake_session_id } }
        m.post(adapter.untis_url_school, json=success_response, status_code=200)

        # make request
        result = adapter.login(username, password)

        # check results
        assert result.json() == success_response
        assert fake_session_id == adapter.session


def test_login_failure():
    with requests_mock.Mocker() as m:
        # fake user data
        username = "john_doe"
        password = "wrong_password"
        fake_school_name = "Hogwarts"

        # create untis adapter (sut)
        adapter = UntisAdapter(school_name=fake_school_name)

        # prepare request mock endpoint
        error_response = { "error": { "message": "Invalid credentials" } }
        m.post(adapter.untis_url_school, json=error_response, status_code=401)

        # make request with wrong credentials and expect an exception
        with pytest.raises(Exception) as excinfo:
            adapter.login(username, password)
        
        assert "Failed to authenticate: Invalid credentials" in str(excinfo.value)


def test_get_timetable_not_authenticated():
    fake_school_name = "Hogwarts"
    adapter = UntisAdapter(school_name=fake_school_name)

    with pytest.raises(Exception) as excinfo:
        adapter.get_timetable("JD", 20230101)
    
    assert "Not authenticated" in str(excinfo.value)


# Run tests
if __name__ == "__main__":
    test_login_success()
    test_login_failure()
    test_get_timetable_not_authenticated()
    print("All tests passed ✅")
    