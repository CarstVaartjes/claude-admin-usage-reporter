USERS = [
    {
        "id": "user_dev1",
        "email": "dev1@example.com",
        "name": "Dev One",
        "role": "developer",
        "type": "user",
        "added_at": "2025-01-01T00:00:00Z",
    },
    {
        "id": "user_dev2",
        "email": "dev2@example.com",
        "name": "Dev Two",
        "role": "developer",
        "type": "user",
        "added_at": "2025-01-01T00:00:00Z",
    },
    {
        "id": "user_admin1",
        "email": "admin1@example.com",
        "name": "Admin One",
        "role": "admin",
        "type": "user",
        "added_at": "2025-01-01T00:00:00Z",
    },
    {
        "id": "user_billing1",
        "email": "billing1@example.com",
        "name": "Billing One",
        "role": "billing",
        "type": "user",
        "added_at": "2025-01-01T00:00:00Z",
    },
]


def usage_row(
    account_id,
    model,
    bucket_start,
    uncached_input=0,
    output=0,
    cache_read=0,
    cache_write_5m=0,
    cache_write_1h=0,
):
    return {
        "account_id": account_id,
        "api_key_id": "apikey_x",
        "model": model,
        "uncached_input_tokens": uncached_input,
        "output_tokens": output,
        "cache_read_input_tokens": cache_read,
        "cache_creation": {
            "ephemeral_5m_input_tokens": cache_write_5m,
            "ephemeral_1h_input_tokens": cache_write_1h,
        },
        "bucket_start": bucket_start,
        "bucket_end": bucket_start,
    }


USAGE_ROWS = [
    usage_row("user_dev1", "claude-sonnet-4-6", "2026-06-01T00:00:00Z", uncached_input=1000, output=500),
    usage_row("user_dev1", "claude-sonnet-4-6", "2026-06-15T00:00:00Z", uncached_input=2000, output=1000),
    usage_row("user_dev1", "claude-opus-4-6", "2026-07-01T00:00:00Z", uncached_input=500, output=200),
    usage_row(
        "user_dev2",
        "claude-sonnet-4-6",
        "2026-06-10T00:00:00Z",
        uncached_input=100,
        output=50,
        cache_read=200,
        cache_write_5m=300,
    ),
    usage_row("user_admin1", "claude-haiku-4-5", "2026-06-01T00:00:00Z", uncached_input=10000, output=2000),
    # usage from a user_id that no longer exists in the users list (removed member)
    usage_row("user_ghost", "claude-sonnet-4-6", "2026-06-05T00:00:00Z", uncached_input=50, output=10),
]
