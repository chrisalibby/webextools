-- Fix answer_indicator column size
-- The column is currently NVARCHAR(10) but needs to be at least NVARCHAR(20)
-- to accommodate values like 'Yes-PostRedirect' (16 characters)

USE WebexCDR;
GO

-- Alter the column to increase its size
ALTER TABLE cdr_records
ALTER COLUMN answer_indicator NVARCHAR(50);
GO

PRINT 'Column answer_indicator resized to NVARCHAR(50)';
