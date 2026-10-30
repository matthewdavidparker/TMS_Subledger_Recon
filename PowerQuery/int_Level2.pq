// int_Level2
// Explode level 2: split each deal's amount across its client sub-accounts.
// Rows now represent one path: position -> deal -> client, per day.

let
    // Positions already split into deals (from level 1)
    Source = int_Level1,

    // Rename the level-1 columns so they don't collide with the next merge
    RenameDealColumns = Table.RenameColumns(
        Source,
        {
            {"Child ID",  "Deal ID"},
            {"Share",     "Deal Share"},
            {"Allocated", "Deal Amount"}
        }
    ),

    // Match each deal to its client sub-accounts in the same hierarchy table.
    // Left Outer keeps unmapped rows (e.g. TBILL-NEW) flowing through.
    MergeHierarchy = Table.NestedJoin(
        RenameDealColumns, {"Deal ID"},
        stg_Hierarchy, {"Parent ID"},
        "Hierarchy",
        JoinKind.LeftOuter
    ),

    // Bring in the client and its share of the deal, renaming as we expand
    ExpandHierarchy = Table.ExpandTableColumn(
        MergeHierarchy, "Hierarchy",
        {"Child ID",       "Share"},
        {"Sub-Account ID", "Client Share"}
    ),

    // The client's portion of this path: Deal Amount x Client Share
    AddClientAmount = Table.AddColumn(
        ExpandHierarchy, "Client Amount",
        each [Deal Amount] * [Client Share],
        Currency.Type
    )
in
    AddClientAmount