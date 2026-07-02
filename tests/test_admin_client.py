import responses

from app.admin_client import AdminClient


@responses.activate
def test_list_users_paginates():
    client = AdminClient(api_key="sk-ant-admin-test")
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/users",
        json={
            "data": [{"id": "user_1", "email": "a@x.com", "name": "A", "role": "developer", "type": "user"}],
            "has_more": True,
            "first_id": "user_1",
            "last_id": "user_1",
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/users",
        json={
            "data": [{"id": "user_2", "email": "b@x.com", "name": "B", "role": "admin", "type": "user"}],
            "has_more": False,
            "first_id": "user_2",
            "last_id": "user_2",
        },
        status=200,
    )

    users = client.list_users()
    assert [u["id"] for u in users] == ["user_1", "user_2"]


@responses.activate
def test_iter_usage_report_flattens_buckets_and_paginates():
    client = AdminClient(api_key="sk-ant-admin-test")
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/usage_report/messages",
        json={
            "data": [
                {
                    "starting_at": "2026-06-01T00:00:00Z",
                    "ending_at": "2026-06-02T00:00:00Z",
                    "results": [{"account_id": "user_1", "model": "claude-sonnet-4-6", "output_tokens": 10}],
                }
            ],
            "has_more": True,
            "next_page": "cursor123",
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/usage_report/messages",
        json={
            "data": [
                {
                    "starting_at": "2026-06-02T00:00:00Z",
                    "ending_at": "2026-06-03T00:00:00Z",
                    "results": [{"account_id": "user_1", "model": "claude-sonnet-4-6", "output_tokens": 20}],
                }
            ],
            "has_more": False,
        },
        status=200,
    )

    from datetime import datetime, timezone

    rows = list(client.iter_usage_report(starting_at=datetime(2026, 6, 1, tzinfo=timezone.utc)))
    assert [r["output_tokens"] for r in rows] == [10, 20]
    assert rows[0]["bucket_start"] == "2026-06-01T00:00:00Z"


@responses.activate
def test_get_retries_on_429_then_succeeds():
    client = AdminClient(api_key="sk-ant-admin-test", max_retries=3)
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/users",
        json={"error": {"message": "rate limited"}},
        status=429,
        headers={"retry-after": "0"},
    )
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/users",
        json={"data": [], "has_more": False, "first_id": "", "last_id": ""},
        status=200,
    )
    users = client.list_users()
    assert users == []


@responses.activate
def test_get_raises_admin_api_error_on_4xx():
    from app.admin_client import AdminAPIError

    client = AdminClient(api_key="sk-ant-admin-test")
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/organizations/users",
        json={"error": {"message": "invalid x-api-key"}},
        status=401,
    )
    try:
        client.list_users()
        assert False, "expected AdminAPIError"
    except AdminAPIError as exc:
        assert exc.status_code == 401
