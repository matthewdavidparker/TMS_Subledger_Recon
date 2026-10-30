// stg_TMS
// Staging: TMS positions (top level), one row per position per day.
// Reads tms_positions.xlsx from the data folder, promotes headers, sets types.

let
    // All files in the data folder (folder path comes from the DataFolder parameter)
    Source = src_DataFolder,

    // Keep only the TMS file
    FilterToFile = Table.SelectRows(Source, each [Name] = "tms_positions.xlsx"),

    // Get the file's contents by name only, so the query works from any folder
    FileContent = FilterToFile{[Name = "tms_positions.xlsx"]}[Content],

    // Open the workbook (true = delay type detection; we set types ourselves below)
    Workbook = Excel.Workbook(FileContent, null, true),

    // Select the Positions sheet
    PositionsSheet = Workbook{[Item = "Positions", Kind = "Sheet"]}[Data],

    // First row holds the column names
    PromoteHeaders = Table.PromoteHeaders(PositionsSheet, [PromoteAllScalars = true]),

    // Set types: dates, text, and fixed decimal for money
    SetTypes = Table.TransformColumnTypes(
        PromoteHeaders,
        {
            {"Value Date",      type date},
            {"Position ID",     type text},
            {"Bank",            type text},
            {"Instrument Type", type text},
            {"Currency",        type text},
            {"Amount",          Currency.Type}
        }
    )
in
    SetTypes