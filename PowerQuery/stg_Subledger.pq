// stg_Subledger
// Staging: subledger client balances (bottom level), one row per
// client sub-account per day. This is the "actual" side of the reconciliation.

let
    // All files in the data folder (folder path comes from the DataFolder parameter)
    Source = src_DataFolder,

    // Keep only the subledger file
    FilterToFile = Table.SelectRows(Source, each [Name] = "subledger_balances.xlsx"),

    // Get the file's contents by name only, so the query works from any folder
    FileContent = FilterToFile{[Name = "subledger_balances.xlsx"]}[Content],

    // Open the workbook (true = delay type detection; we set types ourselves below)
    Workbook = Excel.Workbook(FileContent, null, true),

    // Select the Balances sheet
    BalancesSheet = Workbook{[Item = "Balances", Kind = "Sheet"]}[Data],

    // First row holds the column names
    PromoteHeaders = Table.PromoteHeaders(BalancesSheet, [PromoteAllScalars = true]),

    // Set types: dates, text, and fixed decimal for money
    SetTypes = Table.TransformColumnTypes(
        PromoteHeaders,
        {
            {"Balance Date",   type date},
            {"Sub-Account ID", type text},
            {"Client Name",    type text},
            {"Balance",        Currency.Type}
        }
    )
in
    SetTypes