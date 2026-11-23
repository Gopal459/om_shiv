import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.identity_seed import seed_departments_and_roles, seed_admin_user


@pytest.mark.asyncio
async def test_admin_list_and_create_staff(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)
    await seed_admin_user(db_session)

    # 1. List staff - should include admin
    resp = await test_client.get("/v1/admin/staff")
    assert resp.status_code == 200
    staff_list = resp.json()
    assert len(staff_list) >= 1
    assert any(s["username"] == "admin" for s in staff_list)

    # 2. Create new staff member
    new_staff_payload = {
        "name": "Rajesh Kumar",
        "username": "rajesh",
        "password": "Rajesh@123",
        "mobile": "9829012345",
        "email": "rajesh@omshiv.in",
        "department_code": "SALES",
        "role_code": "SALES_MANAGER",
    }
    create_resp = await test_client.post("/v1/admin/staff", json=new_staff_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["username"] == "rajesh"
    assert created["name"] == "Rajesh Kumar"
    assert created["role_code"] == "SALES_MANAGER"
    assert created["employee_id"].startswith("EMP-")

    # 3. Duplicate username should return 409 Conflict
    dup_resp = await test_client.post("/v1/admin/staff", json=new_staff_payload)
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_admin_roles_and_update_permissions(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)

    # 1. List roles
    resp = await test_client.get("/v1/admin/roles")
    assert resp.status_code == 200
    roles = resp.json()
    assert len(roles) >= 6
    telecaller_role = next((r for r in roles if r["code"] == "TELECALLER"), None)
    assert telecaller_role is not None

    # 2. Update TELECALLER permissions
    updated_perms = {
        "leads": ["view_assigned", "create", "edit_stage", "convert_inquiries", "export"],
        "properties": ["view_all", "post_listing"],
    }
    put_resp = await test_client.put(
        "/v1/admin/roles/TELECALLER/permissions",
        json={"permissions": updated_perms},
    )
    assert put_resp.status_code == 200
    res_data = put_resp.json()
    assert res_data["code"] == "TELECALLER"
    assert "export" in res_data["permissions"]["leads"]

    # 3. Non-existent role returns 404
    bad_resp = await test_client.put(
        "/v1/admin/roles/NON_EXISTENT_ROLE/permissions",
        json={"permissions": updated_perms},
    )
    assert bad_resp.status_code == 404
