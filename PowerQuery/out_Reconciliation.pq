// out_Reconciliation
// Compares expected client balances (TMS exploded through the hierarchy)
// to actual client balances (subledger), one row per client per day.

let
    // Expected side: TMS positions exploded to client level and summed
    Source = out_ExpectedBalances,

    // Full outer join on date + client so rows missing from EITHER side are kept
    MergeSubledger = Table.NestedJoin(
        Source, {"Value Date", "Sub-Account ID"},
        int_SubledgerTotals, {"Balance Date", "Sub-Account ID"},
        "Subledger",
        JoinKind.FullOuter
    ),

    // Bring in the subledger columns; "SL" prefix marks the subledger side
    ExpandSubledger = Table.ExpandTableColumn(
        MergeSubledger, "Subledger",
        {"Balance Date", "Sub-Account ID", "Actual Balance", "Row Count"},
        {"SL Date", "SL Sub-Account ID", "Actual Balance", "SL Row Count"}
    ),

    // Single date key: use the expected date, or the subledger date if expected is missing
    AddDate = Table.AddColumn(
        ExpandSubledger, "Date",
        each [Value Date] ?? [SL Date],
        type date
    ),

    // Single account key: same idea as the date
    AddAccount = Table.AddColumn(
        AddDate, "Account",
        each [#"Sub-Account ID"] ?? [#"SL Sub-Account ID"],
        type text
    ),

    // Actual minus expected; a missing side counts as 0 so the full amount shows
    AddDifference = Table.AddColumn(
        AddAccount, "Difference",
        each ([Actual Balance] ?? 0) - ([Expected Balance] ?? 0),
        type number
    ),

    // Label each row. Order matters: structural problems are checked
    // before amounts, so a missing or duplicate row is never mislabeled
    // as a simple balance break. Tolerance of $0.01 absorbs rounding.
    AddStatus = Table.AddColumn(
        AddDifference, "Status",
        each
            if [Expected Balance] = null then "Subledger only"
            else if [Actual Balance] = null then "Missing in subledger"
            else if [SL Row Count] > 1 then "Duplicate in subledger"
            else if Number.Abs([Difference]) > 0.01 then "Balance break"
            else "Matched",
        type text
    )
in
    AddStatus