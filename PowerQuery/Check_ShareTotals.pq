// Check_ShareTotals
// Quality check: the shares under every parent should add up to 100%.
// Any row returned is a mapping error in the hierarchy.
// Expected result: no rows. (The test data plants one: DEAL-E at 99%.)

let
    // The allocation hierarchy: Parent ID, Child ID, Share
    Source = stg_Hierarchy,

    // Add up the shares under each parent
    SumSharesByParent = Table.Group(
        Source,
        {"Parent ID"},
        {
            {"Total Share", each List.Sum([Share]), type number}
        }
    ),

    // Keep parents whose shares don't add up to 1.
    // Round to 4 decimals first: decimals are stored imperfectly,
    // so 0.1 + 0.2 + 0.7 can come out as 0.9999999999 and trigger a false alarm.
    KeepBadTotals = Table.SelectRows(
        SumSharesByParent,
        each Number.Round([Total Share], 4) <> 1
    )
in
    KeepBadTotals