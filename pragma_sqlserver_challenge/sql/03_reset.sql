USE PragmaDataChallenge;
GO

DELETE FROM dbo.statistics_history;
DELETE FROM dbo.processed_files;
DELETE FROM dbo.transactions;

UPDATE dbo.pipeline_statistics
SET
    total_rows = 0,
    valid_price_count = 0,
    price_sum = 0,
    avg_price = NULL,
    min_price = NULL,
    max_price = NULL,
    updated_at = SYSUTCDATETIME()
WHERE statistics_id = 1;
GO

DBCC CHECKIDENT ('dbo.statistics_history', RESEED, 0);
DBCC CHECKIDENT ('dbo.transactions', RESEED, 0);
GO
