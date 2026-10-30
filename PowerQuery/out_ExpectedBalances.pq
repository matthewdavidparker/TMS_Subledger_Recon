// out_ExpectedBalances
// What each client's balance SHOULD be per day, based on the TMS
// exploded through the hierarchy. This is the expected side of the
// reconciliation.

let
    // Every position -> deal -> client path, per day
    Source = int_Level2,

    // Add up every path that reaches the same client on the same day.
    // A client funded through several deals or positions gets ONE total.
    GroupByClientDay = Table.Group(
        Source,
        {"Value Date", "Sub-Account ID"},
        {
            {"Expected Balance", each List.Sum([Client Amount]), Currency.Type}
        }
    ),

    // Remove rows with no client: TMS positions missing from the hierarchy.
    // They are reported separately in Check_UnmappedPositions,
    // so this money is moved to a check, not lost.
    RemoveUnmapped = Table.SelectRows(
        GroupByClientDay,
        each [#"Sub-Account ID"] <> null
    )
in
    RemoveUnmapped