from typing import Dict, List
from textwrap import dedent

check_rev_rel: dict[str, str] = {
    'chemicalentity_phenotype': 'phenotype_chemicalentity',
    'chemicalentity_molecularfunction': 'molecularfunction_chemicalentity',
    'anatomy_disease': 'disease_anatomy',
    'disease_protein': 'protein_disease',
    'cellularcomponent_protein': 'protein_cellularcomponent',
    'phenotype_protein': 'protein_phenotype',
    'protein_mutation': 'mutation_protein',
    'tissue_chemicalentity': 'chemicalentity_tissue',
    'protein_chemicalentity': 'chemicalentity_protein',
    'biologicalprocess_protein': 'protein_biologicalprocess',
    'molecularfunction_gene': 'gene_molecularfunction',
    'pathway_chemicalentity': 'chemicalentity_pathway',
    'tissue_gene': 'gene_tissue',
    'mutation_chemicalentity': 'chemicalentity_mutation',
    'pathway_protein': 'protein_pathway',
    'protein_gene': 'gene_protein',
    'molecularfunction_protein': 'protein_molecularfunction',
    'biologicalprocess_molecularfunction': 'molecularfunction_biologicalprocess',
    'tissue_protein': 'protein_tissue',
    'chemicalentity_plantextract': 'plantextract_chemicalentity',
    'disease_plantextract': 'plantextract_disease',
    'cellularcomponent_pmid': 'pmid_cellularcomponent',
    'chemicalentity_pmid': 'pmid_chemicalentity',
    'disease_pmid': 'pmid_disease',
    'protein_pmid': 'pmid_protein',
    'tissue_pmid': 'pmid_tissue',
    #'biologicalprocess_promotes_genes': 'gene_promotes_biologicalprocess',
    #'biologicalprocess_inhibits_chemicalentity': chemicalentity_inhibits_biologicalprocess',
}


Ntype_split: dict[str, list[str]] = {
    'phenotype_chemicalentity': ['phenotype', 'chemicalentity'],
    'mutation_disease': ['mutation', 'disease'],
    'molecularfunction_chemicalentity': ['molecularfunction', 'chemicalentity'],
    'disease_anatomy': ['disease', 'anatomy'],
    'chemicalentity_disease': ['chemicalentity', 'disease'],
    'disease_disease': ['disease', 'disease'],
    'biologicalprocess_gene': ['biologicalprocess', 'gene'],
    'protein_protein': ['protein', 'protein'],
    'gene_phenotype': ['gene', 'phenotype'],
    'protein_disease': ['protein', 'disease'],
    'anatomy_gene': ['anatomy', 'gene'],
    'chemicalentity_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'disease_gene': ['disease', 'gene'],
    'gene_cellularcomponent': ['gene', 'cellularcomponent'],
    'chemicalentity_chemicalentity': ['chemicalentity', 'chemicalentity'],
    'cellularcomponent_gene': ['cellularcomponent', 'gene'],
    'gene_disease': ['gene', 'disease'],
    'protein_cellularcomponent': ['protein', 'cellularcomponent'],
    'protein_phenotype': ['protein', 'phenotype'],
    'mutation_protein': ['mutation', 'protein'],
    'chemicalentity_gene': ['chemicalentity', 'gene'],
    'chemicalentity_tissue': ['chemicalentity', 'tissue'],
    'chemicalentity_protein': ['chemicalentity', 'protein'],
    'biologicalprocess_biologicalprocess': ['biologicalprocess', 'biologicalprocess'],
    'phenotype_phenotype': ['phenotype', 'phenotype'],
    'phenotype_gene': ['phenotype', 'gene'],
    'chemicalentity_inhibits_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'gene_inhibits_biologicalprocess': ['gene', 'biologicalprocess'],
    'protein_biologicalprocess': ['protein', 'biologicalprocess'],
    'gene_promotes_biologicalprocess': ['gene', 'biologicalprocess'],
    'gene_molecularfunction': ['gene', 'molecularfunction'],
    'gene_pathway': ['gene', 'pathway'],
    'chemicalentity_pathway': ['chemicalentity', 'pathway'],
    'gene_tissue': ['gene', 'tissue'],
    'disease_phenotype': ['disease', 'phenotype'],
    'chemicalentity_mutation': ['chemicalentity', 'mutation'],
    'gene_anatomy': ['gene', 'anatomy'],
    'phenotype_disease': ['phenotype', 'disease'],
    'pathway_gene': ['pathway', 'gene'],
    'disease_chemicalentity': ['disease', 'chemicalentity'],
    'disease_mutation': ['disease', 'mutation'],
    'gene_chemicalentity': ['gene', 'chemicalentity'],
    'protein_pathway': ['protein', 'pathway'],
    'gene_protein': ['gene', 'protein'],
    'gene_noeffect_biologicalprocess': ['gene', 'biologicalprocess'],
    'chemicalentity_promotes_biologicalprocess': ['chemicalentity', 'biologicalprocess'],
    'gene_biologicalprocess': ['gene', 'biologicalprocess'],
    'protein_molecularfunction': ['protein', 'molecularfunction'],
    'mutation_gene': ['mutation', 'gene'],
    'gene_gene': ['gene', 'gene'],
    'molecularfunction_molecularfunction': ['molecularfunction', 'molecularfunction'],
    'gene_mutation': ['gene', 'mutation'],
    'molecularfunction_biologicalprocess': ['molecularfunction', 'biologicalprocess'],
    'protein_tissue': ['protein', 'tissue'],
    'cellularcomponent_cellularcomponent': ['cellularcomponent', 'cellularcomponent'],
    'pathway_pathway': ['pathway', 'pathway'],
    'anatomy_anatomy': ['anatomy', 'anatomy'],
    'biologicalprocess_chemicalentity': ['biologicalprocess', 'chemicalentity'],
    'plantextract_chemicalentity': ['plantextract', 'chemicalentity'],
    'plantextract_disease': ['plantextract', 'disease'],
    'pmid_cellularcomponent': ['pmid', 'cellularcomponent'],
    'pmid_chemicalentity': ['pmid', 'chemicalentity'],
    'pmid_disease': ['pmid', 'disease'],
    'pmid_protein': ['pmid', 'protein'],
    'pmid_tissue': ['pmid', 'tissue'],
    # 'species_associatedwith_nodes': ['species', 'nodes'],
}

mapping_reversed: Dict[str, str] = {
    "gene": "Gene",
    "protein": "Protein",
    "disease": "Disease",
    "chemicalentity": "ChemicalEntity",
    "phenotype": "Phenotype",
    "tissue": "Tissue",
    "anatomy": "Anatomy",
    "biologicalprocess": "BiologicalProcess",
    "molecularfunction": "MolecularFunction",
    "cellularcomponent": "CellularComponent",
    "pathway": "Pathway",
    "mutation": "Mutation",
    "pmid": "PMID",
    "species": "Species",
    "plantextract": "PlantExtract",
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
