// int_Level1
// Explode level 1: split each TMS position across the deals it funds.
// One position row becomes one row per deal, with the amount split by Share.

let
    // TMS positions, one row per position per day
    Source = stg_TMS,

    // Match each position to its child deals in the hierarchy.
    // Left Outer keeps positions with NO mapping (e.g. TBILL-NEW) as rows
    // with blank Child ID, so unmapped money never disappears silently.
    MergeHierarchy = Table.NestedJoin(
        Source, {"Position ID"},
        stg_Hierarchy, {"Parent ID"},
        "Hierarchy",
        JoinKind.LeftOuter
    ),

    // Bring in the deal (Child ID) and its share of the position.
    // A position with 3 deals now appears on 3 rows.
    ExpandHierarchy = Table.ExpandTableColumn(
        MergeHierarchy, "Hierarchy",
        {"Child ID", "Share"},
        {"Child ID", "Share"}
    ),

    // The deal's portion of the position: Amount x Share.
    // Unmapped positions have a null Share, so Allocated is null too.
    AddAllocated = Table.AddColumn(
        ExpandHierarchy, "Allocated",
        each [Amount] * [Share],
        Currency.Type
    )
in
    AddAllocated