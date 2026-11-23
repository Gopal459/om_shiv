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


@pytest.mark.asyncio
async def test_dynamic_role_crud_and_soft_delete(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)

    # 1. Create a dynamic custom role
    create_payload = {
        "name": "Senior Channel Partner",
        "code": "SR_CHANNEL_PARTNER",
        "department_code": "SALES",
        "permissions": {
            "leads": ["create", "view_assigned"],
            "properties": ["view_all"],
        },
    }
    create_resp = await test_client.post("/v1/admin/roles", json=create_payload)
    assert create_resp.status_code == 201
    created_role = create_resp.json()
    assert created_role["code"] == "SR_CHANNEL_PARTNER"
    assert created_role["name"] == "Senior Channel Partner"

    # 2. Update the dynamic role and test active status toggle
    update_payload = {
        "name": "Lead Channel Partner",
        "department_code": "SALES",
        "is_active": False,
    }
    update_resp = await test_client.put("/v1/admin/roles/SR_CHANNEL_PARTNER", json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Lead Channel Partner"
    assert update_resp.json()["is_active"] is False

    # 2b. Re-activate role
    reactivate_resp = await test_client.put("/v1/admin/roles/SR_CHANNEL_PARTNER", json={"is_active": True})
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["is_active"] is True

    # 2c. Cannot deactivate SUPER_ADMIN
    deact_super = await test_client.put("/v1/admin/roles/SUPER_ADMIN", json={"is_active": False})
    assert deact_super.status_code == 400

    # 3. Soft-delete the dynamic role
    del_resp = await test_client.delete("/v1/admin/roles/SR_CHANNEL_PARTNER")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # 4. Verify role is excluded from active roles list
    list_resp = await test_client.get("/v1/admin/roles")
    assert list_resp.status_code == 200
    active_codes = [r["code"] for r in list_resp.json()]
    assert "SR_CHANNEL_PARTNER" not in active_codes

    # 5. SUPER_ADMIN deletion safeguard
    del_super_admin = await test_client.delete("/v1/admin/roles/SUPER_ADMIN")
    assert del_super_admin.status_code == 400


@pytest.mark.asyncio
async def test_staff_soft_delete_and_role_protection(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)
    await seed_admin_user(db_session)

    # Create staff under TELECALLER role
    staff_payload = {
        "name": "Sunita Verma",
        "username": "sunita",
        "password": "Sunita@123",
        "mobile": "9829099999",
        "department_code": "SALES",
        "role_code": "TELECALLER",
    }
    create_resp = await test_client.post("/v1/admin/staff", json=staff_payload)
    assert create_resp.status_code == 201
    emp_id = create_resp.json()["employee_id"]

    # Test staff active status toggle
    toggle_staff = await test_client.put(f"/v1/admin/staff/{emp_id}", json={"is_active": False})
    assert toggle_staff.status_code == 200
    assert toggle_staff.json()["is_active"] is False

    # Cannot deactivate EMP-0001
    deact_admin_fail = await test_client.put("/v1/admin/staff/EMP-0001", json={"is_active": False})
    assert deact_admin_fail.status_code == 400

    # Re-activate staff so role protection applies
    reactivate_staff = await test_client.put(f"/v1/admin/staff/{emp_id}", json={"is_active": True})
    assert reactivate_staff.status_code == 200
    assert reactivate_staff.json()["is_active"] is True

    # Role deletion should fail because an active employee is assigned
    del_role_fail = await test_client.delete("/v1/admin/roles/TELECALLER")
    assert del_role_fail.status_code == 400
    assert "active staff member" in del_role_fail.json()["detail"]

    # Soft-delete the staff member
    del_staff = await test_client.delete(f"/v1/admin/staff/{emp_id}")
    assert del_staff.status_code == 200
    assert del_staff.json()["status"] == "success"

    # Verify staff is excluded from staff list
    list_resp = await test_client.get("/v1/admin/staff")
    staff_ids = [s["employee_id"] for s in list_resp.json()]
    assert emp_id not in staff_ids

    # Super Admin cannot be deleted
    del_admin_fail = await test_client.delete("/v1/admin/staff/EMP-0001")
    assert del_admin_fail.status_code == 400
