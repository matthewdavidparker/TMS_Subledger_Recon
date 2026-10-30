// stg_Hierarchy
// Staging: the allocation hierarchy ("bill of materials").
// Each row says what share of a parent's balance flows to a child:
//   positions -> deals, and deals -> client sub-accounts.

let
    // All files in the data folder (folder path comes from the DataFolder parameter)
    Source = src_DataFolder,

    // Keep only the hierarchy file
    FilterToFile = Table.SelectRows(Source, each [Name] = "allocation_hierarchy.xlsx"),

    // Get the file's contents by name only, so the query works from any folder
    FileContent = FilterToFile{[Name = "allocation_hierarchy.xlsx"]}[Content],

    // Open the workbook (true = delay type detection; we set types ourselves below)
    Workbook = Excel.Workbook(FileContent, null, true),

    // Select the Hierarchy sheet
    HierarchySheet = Workbook{[Item = "Hierarchy", Kind = "Sheet"]}[Data],

    // First row holds the column names
    PromoteHeaders = Table.PromoteHeaders(HierarchySheet, [PromoteAllScalars = true]),

    // Set types. Share stays a decimal number (not Currency.Type),
    // because it is a percentage and needs full precision.
    SetTypes = Table.TransformColumnTypes(
        PromoteHeaders,
        {
            {"Parent ID", type text},
            {"Child ID",  type text},
            {"Share",     type number}
        }
    )
in
    SetTypes