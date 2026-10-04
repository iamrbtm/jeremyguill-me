from __future__ import annotations

from urllib.parse import quote

import pytest
from sqlalchemy import text

from portfolio.extensions import db


@pytest.mark.parametrize("payload", ["' OR 1=1 --", "'; DROP TABLE projects; --"])
def test_project_lookup_treats_sql_payload_as_data(client, payload):
    response = client.get(f"/work/{quote(payload)}")

    assert response.status_code == 404
    assert db.session.execute(text("SELECT count(*) FROM projects")).scalar_one() >= 0
