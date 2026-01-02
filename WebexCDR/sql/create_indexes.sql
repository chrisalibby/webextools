-- Webex CDR Performance Indexes
-- Platform: Microsoft SQL Server
-- Purpose: Optimize common queries on CDR data

-- Index on start_time for time-based queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_start_time' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_start_time ON cdr_records(start_time);
    PRINT 'Index IX_cdr_records_start_time created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_start_time already exists';
END
GO

-- Index on calling_number for caller searches
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_calling_number' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_calling_number ON cdr_records(calling_number);
    PRINT 'Index IX_cdr_records_calling_number created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_calling_number already exists';
END
GO

-- Index on called_number for called party searches
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_called_number' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_called_number ON cdr_records(called_number);
    PRINT 'Index IX_cdr_records_called_number created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_called_number already exists';
END
GO

-- Index on user_email for user activity queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_user_email' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_user_email ON cdr_records(user_email);
    PRINT 'Index IX_cdr_records_user_email created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_user_email already exists';
END
GO

-- Index on direction for filtering inbound/outbound calls
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_direction' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_direction ON cdr_records(direction);
    PRINT 'Index IX_cdr_records_direction created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_direction already exists';
END
GO

-- Index on call_outcome for success/failure analysis
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_call_outcome' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_call_outcome ON cdr_records(call_outcome);
    PRINT 'Index IX_cdr_records_call_outcome created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_call_outcome already exists';
END
GO

-- Index on location_name for location-based reporting
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_location_name' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_location_name ON cdr_records(location_name);
    PRINT 'Index IX_cdr_records_location_name created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_location_name already exists';
END
GO

-- Index on correlation_id for tracing related calls
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_correlation_id' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_correlation_id ON cdr_records(correlation_id);
    PRINT 'Index IX_cdr_records_correlation_id created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_correlation_id already exists';
END
GO

-- Composite index for common time + direction queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_cdr_records_start_time_direction' AND object_id = OBJECT_ID('cdr_records'))
BEGIN
    CREATE INDEX IX_cdr_records_start_time_direction ON cdr_records(start_time, direction);
    PRINT 'Index IX_cdr_records_start_time_direction created successfully';
END
ELSE
BEGIN
    PRINT 'Index IX_cdr_records_start_time_direction already exists';
END
GO

PRINT 'All indexes created or verified successfully';
