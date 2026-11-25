import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_setting_creates_audit_entry(auth_client_md: AsyncClient):
    payload = {"value": 24, "reason": "Extending untouched escalation window"}
    response = await auth_client_md.patch("/v1/settings/sla_untouched_hours", json=payload)
    assert response.status_code == 200
    assert response.json()["value"] == 24

    # Verify audit log recorded
    audit_resp = await auth_client_md.get("/v1/audit-logs?entity_name=system_settings&entity_id=sla_untouched_hours")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["items"]
    assert len(logs) > 0
    assert logs[0]["performed_by"] == "EMP-0001"
    assert logs[0]["action"] == "UPDATE"
    assert logs[0]["new_state"]["value"] == 24


@pytest.mark.asyncio
async def test_get_settings_list_and_category_filter(auth_client_md: AsyncClient):
    # Retrieve all settings
    response = await auth_client_md.get("/v1/settings")
    assert response.status_code == 200
    settings = response.json()
    assert isinstance(settings, list)
    assert len(settings) >= 10

    # Retrieve only SLA category settings
    response_sla = await auth_client_md.get("/v1/settings?category=SLA")
    assert response_sla.status_code == 200
    sla_settings = response_sla.json()
    assert len(sla_settings) > 0
    assert all(s["category"] == "SLA" for s in sla_settings)


@pytest.mark.asyncio
async def test_get_single_setting_by_key(auth_client_md: AsyncClient):
    response = await auth_client_md.get("/v1/settings/quiet_hours_start")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "quiet_hours_start"
    assert data["value"] == "21:00"
    assert data["category"] == "NOTIFICATION"

    # Non-existent key returns 404
    missing_resp = await auth_client_md.get("/v1/settings/non_existent_key_xyz")
    assert missing_resp.status_code == 404


@pytest.mark.asyncio
async def test_setting_data_type_validation(auth_client_md: AsyncClient):
    # Attempting to assign an invalid string to integer setting
    invalid_payload = {"value": "invalid_integer_string"}
    response = await auth_client_md.patch("/v1/settings/sla_untouched_hours", json=invalid_payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_audit_logs_query_filters(auth_client_md: AsyncClient):
    # Make another update
    await auth_client_md.patch(
        "/v1/settings/rent_agreement_fee_flat",
        json={"value": 750, "reason": "Inflation adjustment"},
    )

    # Query audit logs by entity_id
    resp = await auth_client_md.get("/v1/audit-logs?entity_id=rent_agreement_fee_flat")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert items[0]["entity_id"] == "rent_agreement_fee_flat"
    assert items[0]["new_state"]["value"] == 750


@pytest.mark.asyncio
async def test_update_non_existent_setting_returns_404(auth_client_md: AsyncClient):
    response = await auth_client_md.patch(
        "/v1/settings/non_existent_setting_key",
        json={"value": 100},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_settings_service_caching_and_invalidation(db_session):
    from app.services.settings_service import settings_service, seed_system_settings

    await seed_system_settings(db_session)
    settings_service.clear_cache()

    # Initial get populates memory cache
    val1 = await settings_service.get_setting(db_session, "doubletick_low_balance_threshold")
    assert val1 == 500
    assert "doubletick_low_balance_threshold" in settings_service._memory_cache

    # Update through service invalidates cache
    await settings_service.update_setting(
        db=db_session,
        key="doubletick_low_balance_threshold",
        value=800,
        performed_by="EMP-0001",
        reason="Higher volume alert requirement",
    )
    assert "doubletick_low_balance_threshold" not in settings_service._memory_cache

    # Subsequent get retrieves updated value and re-caches
    val2 = await settings_service.get_setting(db_session, "doubletick_low_balance_threshold")
    assert val2 == 800
    assert settings_service._memory_cache["doubletick_low_balance_threshold"] == 800


@pytest.mark.asyncio
async def test_generic_audit_log_and_model_properties(db_session):
    from app.services.settings_service import settings_service

    audit = await settings_service.log_audit_event(
        db=db_session,
        entity_name="leads",
        entity_id="LEAD-2026-0001",
        action="TRANSFER",
        performed_by="EMP-0001",
        old_state={"advisor": "EMP-0002"},
        new_state={"advisor": "EMP-0003"},
        ip_address="127.0.0.1",
    )
    assert audit.id is not None
    assert audit.old_values == {"advisor": "EMP-0002"}
    assert audit.new_values == {"advisor": "EMP-0003"}
    assert audit.action == "TRANSFER"

