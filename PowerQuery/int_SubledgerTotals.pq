// int_SubledgerTotals
// Rolls the subledger up to one row per client per day, and counts how many
// source rows went into each total. A Row Count above 1 means a duplicate.

let
    // Subledger balances, which SHOULD already be one row per client per day
    Source = stg_Subledger,

    // Group by date + client: sum the balance and count the rows.
    // Grouping protects the reconciliation if the source isn't clean;
    // a duplicate shows up as a doubled balance AND a Row Count of 2.
    GroupByClientDay = Table.Group(
        Source,
        {"Balance Date", "Sub-Account ID"},
        {
            {"Actual Balance", each List.Sum([Balance]),  Currency.Type},
            {"Row Count",      each Table.RowCount(_),    Int64.Type}
        }
    )
in
    GroupByClientDay