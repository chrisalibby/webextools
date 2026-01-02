-- Webex CDR Database Schema
-- Platform: Microsoft SQL Server
-- Purpose: Store Webex Call Detail Records and sync metadata

-- Table 1: CDR Records
-- Stores call detail records from Webex Analytics API
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cdr_records' AND xtype='U')
BEGIN
    CREATE TABLE cdr_records (
        -- Primary Key & Metadata
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        ingestion_timestamp DATETIME2 DEFAULT GETUTCDATE(),

        -- Core Identifiers
        call_id NVARCHAR(150) NOT NULL,
        correlation_id NVARCHAR(150),
        local_session_id NVARCHAR(150),
        final_local_session_id NVARCHAR(150),
        remote_session_id NVARCHAR(150),
        final_remote_session_id NVARCHAR(150),

        -- Call Timing (UTC)
        start_time DATETIME2 NOT NULL,
        answer_time DATETIME2,
        release_time DATETIME2,
        call_transfer_time DATETIME2,
        duration INT,  -- seconds

        -- Call Details
        direction NVARCHAR(20),  -- ORIGINATING/TERMINATING
        call_type NVARCHAR(50),
        call_outcome NVARCHAR(50),
        call_outcome_reason NVARCHAR(100),

        -- Party Information
        calling_number NVARCHAR(50),
        calling_line_id NVARCHAR(150),
        called_number NVARCHAR(50),
        called_line_id NVARCHAR(150),
        dialed_digits NVARCHAR(50),

        -- User/Location/Organization
        user_id NVARCHAR(150),
        user_email NVARCHAR(255),
        user_type NVARCHAR(50),
        location_id NVARCHAR(150),
        location_name NVARCHAR(255),
        department_id NVARCHAR(150),
        org_id NVARCHAR(150),

        -- Device Information
        device_mac NVARCHAR(17),
        client_type NVARCHAR(50),
        client_version NVARCHAR(50),
        model NVARCHAR(100),

        -- Authorization & Routing
        authorization_code NVARCHAR(50),
        inbound_trunk NVARCHAR(255),
        outbound_trunk NVARCHAR(255),
        route_group NVARCHAR(255),

        -- Call Features
        answered BIT,
        answer_indicator NVARCHAR(50),  -- Increased from 10 to accommodate 'Yes-PostRedirect'
        redirecting_number NVARCHAR(50),
        redirect_reason NVARCHAR(100),

        -- International
        international_country NVARCHAR(100),

        -- Transfer Related
        transfer_related_call_id NVARCHAR(150),

        -- Site Information
        site_uuid NVARCHAR(150),
        site_main_number NVARCHAR(50),
        site_timezone NVARCHAR(50),

        -- Raw JSON for future-proofing
        raw_json NVARCHAR(MAX),

        -- Unique constraint for duplicate prevention
        CONSTRAINT UQ_call_id_start_time UNIQUE (call_id, start_time)
    );
    PRINT 'Table cdr_records created successfully';
END
ELSE
BEGIN
    PRINT 'Table cdr_records already exists';
END
GO

-- Table 2: Sync State Tracking
-- Records successful sync runs and metadata
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cdr_sync_state' AND xtype='U')
BEGIN
    CREATE TABLE cdr_sync_state (
        id INT IDENTITY(1,1) PRIMARY KEY,
        last_successful_run_utc DATETIME2 NOT NULL,
        last_successful_end_time_utc DATETIME2 NOT NULL,
        records_fetched INT NOT NULL,
        sync_duration_seconds INT NOT NULL,
        api_calls_made INT NOT NULL,
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        notes NVARCHAR(500)
    );
    PRINT 'Table cdr_sync_state created successfully';
END
ELSE
BEGIN
    PRINT 'Table cdr_sync_state already exists';
END
GO

-- Table 3: Error Logging
-- Tracks errors for troubleshooting
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cdr_sync_errors' AND xtype='U')
BEGIN
    CREATE TABLE cdr_sync_errors (
        id INT IDENTITY(1,1) PRIMARY KEY,
        error_timestamp DATETIME2 DEFAULT GETUTCDATE(),
        error_type NVARCHAR(100),  -- API_ERROR, DB_ERROR, AUTH_ERROR, etc.
        error_message NVARCHAR(MAX),
        stack_trace NVARCHAR(MAX),
        recovered BIT DEFAULT 0,
        recovery_timestamp DATETIME2
    );
    PRINT 'Table cdr_sync_errors created successfully';
END
ELSE
BEGIN
    PRINT 'Table cdr_sync_errors already exists';
END
GO
