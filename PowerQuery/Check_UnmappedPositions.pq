// Check_UnmappedPositions
// Quality check: TMS positions that have no entry in the hierarchy.
// Their money can't be allocated to any client, so it would never
// reach the reconciliation. Any row returned needs a hierarchy update.
// Expected result: no rows. (The test data plants one: TBILL-NEW.)

let
    // TMS positions, one row per position per day
    Source = stg_TMS,

    // Left Anti join: keep only positions with NO matching Parent ID
    // in the hierarchy (the opposite of an inner join)
    FindUnmapped = Table.NestedJoin(
        Source, {"Position ID"},
        stg_Hierarchy, {"Parent ID"},
        "Hierarchy",
        JoinKind.LeftAnti
    ),

    // The merged column is always empty for unmatched rows, so drop it
    RemoveEmptyColumn = Table.RemoveColumns(FindUnmapped, {"Hierarchy"})
in
    RemoveEmptyColumn