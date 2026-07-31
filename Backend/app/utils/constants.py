from typing import Dict, List
from textwrap import dedent

check_rev_rel: dict[str, str] = {
    'biologicalprocess_anatomicalentity': 'anatomicalentity_biologicalprocess',
    'cellularcomponent_anatomicalentity': 'anatomicalentity_cellularcomponent',
    'chemicalentity_anatomicalentity': 'anatomicalentity_chemicalentity',
    'cellularcomponent_biologicalprocess': 'biologicalprocess_cellularcomponent',
    'chemicalentity_cellularcomponent': 'cellularcomponent_chemicalentity',
    'pathway_chemicalentity': 'chemicalentity_pathway',
    'tissue_chemicalentity': 'chemicalentity_tissue',
    'anatomicalentity_disease': 'disease_anatomicalentity',
    'pathway_disease': 'disease_pathway',
    'molecularfunction_gene': 'gene_molecularfunction',
    'protein_gene': 'gene_protein',
    'tissue_gene': 'gene_tissue',
    'gene_mirna': 'mirna_gene',
    'chemicalentity_molecularfunction': 'molecularfunction_chemicalentity',
    'protein_mutation': 'mutation_protein',
    'chemicalentity_phenotype': 'phenotype_chemicalentity',
    'chemicalentity_plantspecies': 'plantspecies_chemicalentity',
    'disease_plantspecies': 'plantspecies_disease',
    'cellularcomponent_pmid': 'pmid_cellularcomponent',
    'chemicalentity_pmid': 'pmid_chemicalentity',
    'disease_pmid': 'pmid_disease',
    'protein_pmid': 'pmid_protein',
    'tissue_pmid': 'pmid_tissue',
    'cellularcomponent_protein': 'protein_cellularcomponent',
    'disease_protein': 'protein_disease',
    'pathway_protein': 'protein_pathway',
    'tissue_protein': 'protein_tissue',
    'cellularcomponent_phenotype': 'phenotype_cellularcomponent',
    'biologicalprocess_phenotype': 'phenotype_biologicalprocess',
    'molecularfunction_phenotype': 'phenotype_molecularfunction',
}

Ntype_split: dict[str, list[str]] = {
    'anatomicalentity_anatomicalentity': ['anatomicalentity', 'anatomicalentity'],
    'anatomicalentity_biologicalprocess': ['anatomicalentity', 'biologicalprocess'],
    'anatomicalentity_cellularcomponent': ['anatomicalentity', 'cellularcomponent'],
    'anatomicalentity_chemicalentity': ['anatomicalentity', 'chemicalentity'],
    'anatomicalentity_gene': ['anatomicalentity', 'gene'],
    'biologicalprocess_biologicalprocess': ['biologicalprocess', 'biologicalprocess'],
    'biologicalprocess_cellularcomponent': ['biologicalprocess', 'cellularcomponent'],
    'biologicalprocess_chemicalentity': ['biologicalprocess', 'chemicalentity'],
    'biologicalprocess_gene': ['biologicalprocess', 'gene'],
    'biologicalprocess_molecularfunction': ['biologicalprocess', 'molecularfunction'],
    'biologicalprocess_protein': ['biologicalprocess', 'protein'],
    'cellularcomponent_cellularcomponent': ['cellularcomponent', 'cellularcomponent'],
    'cellularcomponent_chemicalentity': ['cellularcomponent', 'chemicalentity'],
    'cellularcomponent_gene': ['cellularcomponent', 'gene'],
    'chemicalentity_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'chemicalentity_chemicalentity': ['chemicalentity', 'chemicalentity'],
    'chemicalentity_disease': ['chemicalentity', 'disease'],
    'chemicalentity_gene': ['chemicalentity', 'gene'],
    'chemicalentity_mutation': ['chemicalentity', 'mutation'],
    'chemicalentity_pathway': ['chemicalentity', 'pathway'],
    'chemicalentity_protein': ['chemicalentity', 'protein'],
    'chemicalentity_tissue': ['chemicalentity', 'tissue'],
    'chemicalentity_inhibits_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'chemicalentity_negativelyassociatedwith_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'chemicalentity_noeffect_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'chemicalentity_positivelyassociatedwith_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'chemicalentity_promotes_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'disease_anatomicalentity': ['disease', 'anatomicalentity'],
    'disease_chemicalentity': ['disease', 'chemicalentity'],
    'disease_disease': ['disease', 'disease'],
    'disease_gene': ['disease', 'gene'],
    'disease_mutation': ['disease', 'mutation'],
    'disease_pathway': ['disease', 'pathway'],
    'disease_phenotype': ['disease', 'phenotype'],
    'gene_anatomicalentity': ['gene', 'anatomicalentity'],
    'gene_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_cellularcomponent': ['gene', 'cellularcomponent'],
    'gene_chemicalentity': ['gene', 'chemicalentity'],
    'gene_disease': ['gene', 'disease'],
    'gene_gene': ['gene', 'gene'],
    'gene_inhibits_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_molecularfunction': ['gene', 'molecularfunction'],
    'gene_mutation': ['gene', 'mutation'],
    'gene_negativelyassociatedwith_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_notassociatedwith_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_pathway': ['gene', 'pathway'],
    'gene_phenotype': ['gene', 'phenotype'],
    'gene_promotes_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_protein': ['gene', 'protein'],
    'gene_positivelyassociatedwith_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_tissue': ['gene', 'tissue'],
    'mirna_gene': ['mirna', 'gene'],
    'molecularfunction_biologicalprocess': ['molecularfunction', 'biologicalprocess'],
    'molecularfunction_chemicalentity': ['molecularfunction', 'chemicalentity'],
    'molecularfunction_molecularfunction': ['molecularfunction', 'molecularfunction'],
    'molecularfunction_protein': ['molecularfunction', 'protein'],
    'mutation_chemicalentity': ['mutation', 'chemicalentity'],
    'mutation_disease': ['mutation', 'disease'],
    'mutation_gene': ['mutation', 'gene'],
    'mutation_protein': ['mutation', 'protein'],
    'mutation_mutation': ['mutation', 'mutation'],
    'pathway_gene': ['pathway', 'gene'],
    'pathway_pathway': ['pathway', 'pathway'],
    'phenotype_chemicalentity': ['phenotype', 'chemicalentity'],
    'phenotype_disease': ['phenotype', 'disease'],
    'phenotype_gene': ['phenotype', 'gene'],
    'phenotype_phenotype': ['phenotype', 'phenotype'],
    'phenotype_protein': ['phenotype', 'protein'],
    'plantspecies_chemicalentity': ['plantspecies', 'chemicalentity'],
    'plantspecies_disease': ['plantspecies', 'disease'],
    'pmid_cellularcomponent': ['pmid', 'cellularcomponent'],
    'pmid_chemicalentity': ['pmid', 'chemicalentity'],
    'pmid_disease': ['pmid', 'disease'],
    'pmid_protein': ['pmid', 'protein'],
    'pmid_tissue': ['pmid', 'tissue'],
    'protein_biologicalprocess': ['protein', 'biologicalprocess'],
    'protein_cellularcomponent': ['protein', 'cellularcomponent'],
    'protein_chemicalentity': ['protein', 'chemicalentity'],
    'protein_disease': ['protein', 'disease'],
    'protein_molecularfunction': ['protein', 'molecularfunction'],
    'protein_pathway': ['protein', 'pathway'],
    'protein_phenotype': ['protein', 'phenotype'],
    'protein_protein': ['protein', 'protein'],
    'protein_tissue': ['protein', 'tissue'],
    'chemicalentity_notassociatedwith_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'phenotype_cellularcomponent': ['phenotype', 'cellularcomponent'],
    'phenotype_biologicalprocess': ['phenotype', 'biologicalprocess'],
    'phenotype_molecularfunction': ['phenotype', 'molecularfunction'],
    'species_associatedwith': ['species', 'associatedwith'], 
}

mapping_reversed: Dict[str, str] = {
    "gene": "Gene",
    "protein": "Protein",
    "disease": "Disease",
    "chemicalentity": "ChemicalEntity",
    "phenotype": "Phenotype",
    "tissue": "Tissue",
    "anatomicalentity": "AnatomicalEntity",
    "biologicalprocess": "BiologicalProcess",
    "molecularfunction": "MolecularFunction",
    "cellularcomponent": "CellularComponent",
    "pathway": "Pathway",
    "mutation": "Mutation",
    "mirna": "Mirna",
    "pmid": "PMID",
    "species": "Species",
    "plantspecies": "Plantspecies",
}

def build_hypothesis_system_prompt(hypothesis: str) -> str:
    """
    Returns a formatted system prompt that embeds the provided hypothesis.
    """
    prompt = f"""
    You are an AI assistant tasked with analyzing scientific data. I will provide you with a JSON file containing the results from a knowledge graph model experiment. The purpose of this experiment was to test the following scientific hypothesis:

    Hypothesis: "{hypothesis}"

    Please review the provided JSON file, Strict, You need to evaluate all the triples in json file(went for prediction), and prepare a comprehensive summary of the findings. Your summary must be structured to directly evaluate whether the data supports, partially supports or refuses this hypothesis. Refusal of hypothesis will only come when no. of 4_inKG_true_REJECT is >(greater than) 2_inKG_false_ACCEPT.

    Your response should include:
    - Always give info of these "terms": [used in hypothesis],"entityUnionCount":,"tripleCount":,"categoryCounts": {"1_inKG_true_ACCEPT","2_inKG_false_ACCEPT","3_inKG_false_REJECT","4_inKG_true_REJECT","total_rows"}
    - A direct conclusion at the beginning, stating whether the KG model's results support the hypothesis, this should be based on all the triples  in json file.
    - A high-level statistical overview of the experiment, ** Strict** including the total number of predictions, exactly present in JSON, Not in vector chunk. 
        the number of accepted new triple predictions in whole JSON(2_inKG_false_ACCEPT), and the number of confirmed known relationships in whole JSON(1_inKG_true_ACCEPT) and rejected ground truth(4_inKG_true_REJECT)
    - No change in numbers and values which are in JSON file.
    - Don't directly evaluate no. of accepted Vs rejected count and give results, It should be based on 1_inKG_true_ACCEPT,2_inKG_false_ACCEPT,4_inKG_true_REJECT
    - A detailed breakdown of key thematic findings that connect the core concepts of the hypothesis (for example: Spermine, Hyperkinesis, Oxidative Stress, Neurotransmitters, and the Central Nervous System).
    - Quantitative evidence for each key finding. You must substantiate your claims by citing specific examples (atleast 10-15) of predicted relationships (triples) and their corresponding prediction scores from the JSON file. Please note that scores closer to zero indicate higher confidence.
    - also consider 2-3 external validation points for the asked hypothesis.
    - A concluding paragraph summarizing the overall implications of these findings for future research.
    Please adopt a formal, analytical tone suitable for a scientific report.

    For Example: I am attaching the desired results for this hypothesis: "Spermine, a polyamine involved in cellular metabolism and neuroprotection, may influence the development or severity of Hyperkinesis through its modulation of neurotransmitter signaling and oxidative stress pathways in the central nervous system."
    Desired sample output:
        Based on the knowledge graph analysis, the results provide strong computational support for the hypothesis. The model successfully identified numerous new connections, plausible connections that link Spermine, Hyperkinesis, neurotransmitter signaling, and oxidative stress within the central nervous system.

        Out of 3,577 relationships tested between 104 unique biological entities, the model accepted 642 as plausible. Of these, 592 are new link predictions not previously recorded in the knowledge graph, forming a cohesive network of evidence that directly supports the proposed mechanisms.
        The Big Picture: Statistical Overview 📊
        The model's performance highlights its ability to both validate existing knowledge and generate new, data-driven hypotheses:
        new connection Discoveries (Accepted): 592 new relationships were predicted as highly plausible.
        Confirmed Knowledge (Accepted): 50 known relationships were correctly identified with very strong scores, validating the model's accuracy.
        Rejected Triples: 2,935 potential relationships (both new and known) were correctly filtered out as unlikely, demonstrating the model's high selectivity.
        Key Thematic Findings with Quantitative Support 🔬
        The accepted predictions reveal strong thematic connections, with scores closer to zero indicating higher confidence in the predicted relationship.
        1. Direct Links Between Spermine Metabolism, Oxidative Stress, and Hyperkinesis
        The model established direct connections between the core components of the hypothesis with strong quantitative backing:
        Hyperkinesis ↔ Oxidative Stress Genes: Hyperkinesis was newly associated with several key oxidative stress genes with high confidence scores:
        Hyperkinesis ↔ OXSR1 (oxidative stress responsive kinase 1), score: -0.0316
        Hyperkinesis ↔ OSGIN2 (oxidative stress induced growth inhibitor 2), score: -0.0335
        Hyperkinesis ↔ OSGIN1 (oxidative stress induced growth inhibitor 1), score: -0.0404
        Spermine Metabolism ↔ Hyperkinesis: A direct link was predicted between spermine metabolism genes and the disease state:
        SMOX (spermine oxidase) ↔ Hyperkinesis, score: -0.0675
        Spermine Metabolism ↔ Oxidative Stress: A highly significant new gene-gene link was predicted between SMOX and OXSR1 with a score of -0.0074, suggesting a direct molecular interplay.

        2. The Role of Neurotransmitter Signaling 🧠
        The analysis strengthens the hypothesis by quantitatively connecting both spermine and oxidative stress to neurotransmitter functions:
        Spermine Metabolism → Neurotransmitter Function: Genes like SMS (spermine synthase) and SMOX were newly linked to key neurotransmitter processes with strong scores:
        SMS ↔ neurotransmitter secretion, score: -0.0245
        SMOX ↔ neurotransmitter transport, score: -0.0304
        Oxidative Stress ↔ Neurotransmitter Pathways: The model predicted robust links between key oxidative stress genes and specific neurotransmitter systems:
        Glutamate Neurotransmitter Release Cycle ↔ OXSR1, score: -0.0301
        Dopamine Neurotransmitter Release Cycle ↔ OSGIN1, score: -0.0385
        3. Validation in the Central Nervous System 🔗
        The anatomical context of the hypothesis was validated with exceptionally strong scores for known relationships and supported by new predictions:
        Confirmed Links: Foundational links between key genes and the central nervous system were confirmed with high confidence, including SAT1 (score: -0.0057) and OSGIN1 (score: -0.0077).

        new Link: A new relationship was predicted between Hyperkinesis and the central nervous system (score: -0.1178), computationally placing the disease within the correct anatomical context.

        Conclusion
        The knowledge graph model's results strongly corroborate the hypothesis by building a dense, interconnected network of evidence. The 592 new predictions, backed by strong confidence scores, provide a quantitative foundation for the proposed mechanisms. The findings highlight a clear pathway where spermine metabolism and oxidative stress are intertwined with neurotransmitter signaling in the CNS, offering a compelling, data-driven rationale for further experimental research into the molecular basis of Hyperkinesis.

    """
    return dedent(prompt).strip()
