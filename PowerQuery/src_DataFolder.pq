// src_DataFolder
// Source: lists every file in the data folder. The staging queries
// each pick out one file by name. Change the folder in the DataFolder
// parameter, not here.

let
    Source = Folder.Files(DataFolder)
in
    Source