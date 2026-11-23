"""Migration 0005: Create tbl_leads schema with all 54 legacy columns and soft-delete."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

requires_session = False


async def upgrade(engine: AsyncEngine) -> None:
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
        if is_sqlite:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_leads (
                        leads_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        assign_franch_id INTEGER NOT NULL DEFAULT 0,
                        assign_franchstaff_id INTEGER NOT NULL DEFAULT 0,
                        assignfranchisee_date TIMESTAMP NULL,
                        assignfranchiseestaff_date TIMESTAMP NULL,
                        property_id INTEGER NOT NULL DEFAULT 0,
                        lead_table_name VARCHAR(264) DEFAULT 'BUY',
                        dealer_have INTEGER NOT NULL DEFAULT 0,
                        lead_status_id INTEGER NULL,
                        lead_source_id INTEGER DEFAULT 1,
                        address TEXT NULL,
                        contact_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NULL,
                        mobile VARCHAR(32) NOT NULL,
                        permission TEXT NULL,
                        nextfollowup_datetime TIMESTAMP NULL,
                        deal_final_price DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                        registry_date TIMESTAMP NULL,
                        property_idno VARCHAR(200) NULL,
                        indv_property_address TEXT NULL,
                        approve_lead_remark TEXT NULL,
                        approve_by INTEGER NOT NULL DEFAULT 0,
                        approve_lead_date TIMESTAMP NULL,
                        deal_close_by INTEGER NOT NULL DEFAULT 0,
                        dealclose_date TIMESTAMP NULL,
                        deal_date TIMESTAMP NULL,
                        lead_status INTEGER NOT NULL DEFAULT 0,
                        lead_close_date TIMESTAMP NULL,
                        reference_relation_by VARCHAR(255) NULL,
                        refer_by_name VARCHAR(255) NULL,
                        refer_by_mobile VARCHAR(255) NULL,
                        alternate_contact_mobile VARCHAR(255) NULL,
                        create_by VARCHAR(255) NULL,
                        lead_unique_id VARCHAR(255) NULL,
                        lastfollowup_id INTEGER NOT NULL DEFAULT 0,
                        lastcallstatus_id INTEGER NOT NULL DEFAULT 0,
                        calls_status INTEGER NOT NULL DEFAULT 0,
                        lead_open INTEGER NOT NULL DEFAULT 1,
                        lead_remark TEXT NULL,
                        stage INTEGER NOT NULL DEFAULT 1,
                        location_lat VARCHAR(255) NULL,
                        location_long VARCHAR(255) NULL,
                        rating INTEGER NOT NULL DEFAULT 3,
                        current_update INTEGER NOT NULL DEFAULT 0,
                        update_userid INTEGER NOT NULL DEFAULT 0,
                        disqualified_reason INTEGER NOT NULL DEFAULT 0,
                        is_admin INTEGER NOT NULL DEFAULT 0,
                        call_status_qulified INTEGER NOT NULL DEFAULT 0,
                        last_callstatus_updatetime TIMESTAMP NULL,
                        sold_status INTEGER NOT NULL DEFAULT 0,
                        opportunity_converted INTEGER NOT NULL DEFAULT 0,
                        opportunity_id INTEGER NOT NULL DEFAULT 0,
                        opportunity_datetime TIMESTAMP NULL,
                        deleted_at TIMESTAMP NULL,
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )
            # Create indexes
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tbl_leads_mobile ON tbl_leads(mobile);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tbl_leads_status ON tbl_leads(lead_status);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tbl_leads_stage ON tbl_leads(stage);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tbl_leads_deleted ON tbl_leads(deleted_at);"))
        else:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_leads (
                        leads_id INT AUTO_INCREMENT PRIMARY KEY,
                        assign_franch_id INT NOT NULL DEFAULT 0,
                        assign_franchstaff_id INT NOT NULL DEFAULT 0,
                        assignfranchisee_date DATETIME NULL,
                        assignfranchiseestaff_date DATETIME NULL,
                        property_id INT NOT NULL DEFAULT 0,
                        lead_table_name VARCHAR(264) DEFAULT 'BUY',
                        dealer_have INT NOT NULL DEFAULT 0 COMMENT '1=>Yes, 2=>No',
                        lead_status_id INT NULL,
                        lead_source_id INT DEFAULT 1,
                        address TEXT NULL,
                        contact_name VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NULL,
                        mobile VARCHAR(32) NOT NULL,
                        permission TEXT NULL,
                        nextfollowup_datetime TIMESTAMP NULL DEFAULT NULL,
                        deal_final_price DECIMAL(18,2) NOT NULL DEFAULT 0.00,
                        registry_date DATETIME NULL,
                        property_idno VARCHAR(200) NULL,
                        indv_property_address TEXT NULL,
                        approve_lead_remark TEXT NULL,
                        approve_by INT NOT NULL DEFAULT 0,
                        approve_lead_date DATETIME NULL,
                        deal_close_by INT NOT NULL DEFAULT 0,
                        dealclose_date DATETIME NULL,
                        deal_date DATETIME NULL,
                        lead_status INT NOT NULL DEFAULT 0 COMMENT '0=>New, 1=>In progress, 2=>Disqualified, 3=>Solved, 4=>Qualified, 5=>Converted',
                        lead_close_date DATETIME NULL,
                        reference_relation_by VARCHAR(255) NULL,
                        refer_by_name VARCHAR(255) NULL,
                        refer_by_mobile VARCHAR(255) NULL,
                        alternate_contact_mobile VARCHAR(255) NULL,
                        create_by VARCHAR(255) NULL,
                        lead_unique_id VARCHAR(255) NULL,
                        lastfollowup_id INT NOT NULL DEFAULT 0,
                        lastcallstatus_id INT NOT NULL DEFAULT 0,
                        calls_status INT NOT NULL DEFAULT 0,
                        lead_open INT NOT NULL DEFAULT 1,
                        lead_remark TEXT NULL,
                        stage INT NOT NULL DEFAULT 1 COMMENT '1-General Follow-up, 2-Inspection, 3-Finalization, 4-Re-Site Visit Planned',
                        location_lat VARCHAR(255) NULL,
                        location_long VARCHAR(255) NULL,
                        rating INT NOT NULL DEFAULT 3 COMMENT '1-Hot Call, 2-Warm Call, 3-Cold Call',
                        current_update INT NOT NULL DEFAULT 0,
                        update_userid INT NOT NULL DEFAULT 0,
                        disqualified_reason INT NOT NULL DEFAULT 0 COMMENT '1-Inaccurate Data, 2-Not Interested, 3-Not response, 4-Disconnecting Call, 5-Rejected, 6-Other, 7-Property has Sold',
                        is_admin INT NOT NULL DEFAULT 0,
                        call_status_qulified INT NOT NULL DEFAULT 0 COMMENT '1-In Progress, 2-Closed',
                        last_callstatus_updatetime DATETIME NULL,
                        sold_status INT NOT NULL DEFAULT 0,
                        opportunity_converted INT NOT NULL DEFAULT 0,
                        opportunity_id INT NOT NULL DEFAULT 0,
                        opportunity_datetime DATETIME NULL,
                        deleted_at TIMESTAMP NULL,
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_tbl_leads_mobile (mobile),
                        INDEX idx_tbl_leads_status (lead_status),
                        INDEX idx_tbl_leads_stage (stage),
                        INDEX idx_tbl_leads_deleted (deleted_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
                    """
                )
            )
