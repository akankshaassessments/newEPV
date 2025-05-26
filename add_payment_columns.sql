-- Add transaction_id and payment_date columns to finance_entry table
ALTER TABLE finance_entry ADD COLUMN transaction_id VARCHAR(100) NULL;
ALTER TABLE finance_entry ADD COLUMN payment_date DATETIME NULL;
