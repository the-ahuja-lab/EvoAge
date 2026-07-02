import pandas as pd
from pathlib import Path

base_dir = Path(
    "/storage/Arushi/090526_EvoAge/kg_formation/orthology_mapping/Biomart_ensemble/Human_Ortholog_Mapping_3"
)

species_list = [
    "Yeast",
    "Celegans",
    "Drosophila",
    "Zebrafish",
    "Mouse",
]

for species in species_list:

    species_dir = base_dir / species

    one2one_file = species_dir / f"{species}_byType_ortholog_one2one.csv"
    one2many_file = species_dir / f"{species}_byType_ortholog_one2many.csv"

    output_file = species_dir / f"{species}_byType_ortholog_one2one_plus_one2many.csv"

    df1 = pd.read_csv(one2one_file)
    df2 = pd.read_csv(one2many_file)

    merged = pd.concat([df1, df2], ignore_index=True)

    # remove exact duplicate rows
    merged = merged.drop_duplicates()

    merged.to_csv(output_file, index=False)

    print(
        f"{species}: "
        f"1to1={len(df1):,}, "
        f"1toMany={len(df2):,}, "
        f"saved={len(merged):,}"
    )

print("\nDone.")