# EvoAge vs BioChatter — comparison question set

Both systems run against the **same** Neo4j graph (`neo4j://192.168.3.153:3333`,
45.5M nodes / 1.24B relationships) and the **same** LLM (`deepseek-v4-flash` via
the OpenCode proxy). Only the framework differs.

- **EvoAge**: entity resolution → KG retrieval → RotatE/RESCAL scoring →
  4-bucket classification → evidence gathering → multi-agent swarm verdict.
- **BioChatter**: schema-driven Cypher generation → retrieval → LLM phrasing.
  No embedding model, no scoring, no verdict.

All entities below were verified present in the graph on 2026-08-02.

---

## How to read this set

The five tiers are deliberately ordered from "BioChatter should win or tie" to
"BioChatter structurally cannot compete". **Report all five.** A comparison in
which the baseline never wins anything is not persuasive — Tier 1 losses are
what make the Tier 4–5 results credible.

| Tier | What it tests | Expected outcome |
|---|---|---|
| 1 | Single-hop retrieval | **BioChatter competitive; may win** |
| 2 | Multi-hop / compositional retrieval | Close; EvoAge edges ahead |
| 3 | Aggregation & schema reasoning | BioChatter often wins (direct Cypher) |
| 4 | Cross-species / orthology | **EvoAge wins** — needs orthology framework |
| 5 | Novel-triple hypothesis testing | **EvoAge only** — BioChatter cannot score absent edges |

---

## Tier 1 — Single-hop retrieval (fair baseline; expect BioChatter to do well)

Answerable directly from graph content. Both systems should succeed; scoring is
about precision and whether the returned entities are correct.

1. Which genes are associated with Alzheimer disease?
2. Which biological processes is the gene SIRT1 involved in?
3. What chemicals are associated with the gene APOE?
4. Which diseases is the gene TP53 associated with?
5. What phenotypes are linked to the gene FOXO3?
6. Which proteins interact with the protein encoded by MTOR?
7. What anatomical entities are associated with the gene IGF1?
8. Which pathways is CDKN2A part of?
9. What molecular functions does the gene TERT have?
10. Which chemicals are associated with cellular senescence?

## Tier 2 — Multi-hop / compositional retrieval

Require chaining two or more relationships, or combining constraints. Tests
whether query generation holds up as compositional depth grows.

11. Which genes are associated with both Alzheimer disease and cellular senescence?
12. What chemicals target genes that are associated with Parkinson disease?
13. Which biological processes are shared between SIRT1 and FOXO3?
14. Find genes associated with diseases that also have a link to inflammation.
15. Which proteins are involved in pathways associated with type 2 diabetes?
16. What diseases share associated genes with Alzheimer disease?
17. Which chemicals inhibit biological processes that TP53 positively regulates?
18. Find genes linked to both oxidative stress-induced premature senescence and a named disease.

## Tier 3 — Aggregation & schema reasoning

Counting, ranking, and questions about the graph itself. BioChatter tends to do
well here because these map cleanly onto Cypher aggregates — include them, and
expect to lose some.

19. How many diseases are in the knowledge graph?
20. How many genes are associated with cellular senescence?
21. Which disease has the most associated genes?
22. What are the top 10 genes by number of associated biological processes?
23. How many relationship types connect Gene to BiologicalProcess?
24. Which species are represented in the knowledge graph?

## Tier 4 — Cross-species / orthology (EvoAge's structural advantage)

The graph holds 6 species (human 40,702 genes; mouse 14,827; *C. elegans* 14,540;
*D. melanogaster* 9,788; zebrafish 5,587; yeast 4,805) and 17,931 genes carrying
`ortholog_info`. EvoAge's human-centric orthology framework is built for these;
BioChatter must infer species handling from the schema alone and generally will
not use `node_species` or `ortholog_info` unless told to.

25. What is the *C. elegans* ortholog of the human gene SIRT1, and is it linked to lifespan?
26. Which aging-related genes are conserved between human and *Drosophila melanogaster*?
27. Do mouse and human share associated genes for cellular senescence?
28. Which yeast genes have human orthologs associated with aging?
29. Compare the biological processes annotated to FOXO3 in human versus its zebrafish ortholog.
30. Which genes associated with longevity have orthologs in at least three species?

> **Note for fairness:** if BioChatter fails these purely because it never
> discovered the `node_species` / `ortholog_info` properties, say so explicitly
> in the write-up, and consider re-running with those properties named in the
> prompt. A failure caused by prompt scaffolding is a weaker claim than a
> failure caused by architecture.

## Tier 5 — Novel-triple hypothesis testing (EvoAge only)

Each asserts a relationship **absent from the graph**. EvoAge scores absent
triples with RotatE/RESCAL and returns accept/reject with a confidence and a
swarm verdict. BioChatter can only retrieve what exists, so it returns empty —
and empty is not a verdict.

Verify absence in the graph before using each one, so "no result" is provably
about novelty and not a matching failure.

31. *(the verified example)* Betaine supplementation promotes healthy aging and
    inhibits cellular senescence. By acting as an exercise mimetic, betaine
    inhibits TBK1 activity, reducing systemic inflammation and delaying
    age-related physical decline.
    → **Verified 2026-08-02:** TBK1 present as a Gene; betaine present as
    `glycine betaine`; **no betaine–TBK1 edge of any type or direction.**
32. Metformin extends lifespan by inhibiting mTOR signalling in *C. elegans*.
33. Rapamycin treatment reverses cellular senescence markers in aged cardiac tissue.
34. NAD+ precursor supplementation restores mitochondrial function via SIRT3 activation.
35. Inhibition of CDKN2A promotes tissue regeneration in aged mammals.
36. Klotho overexpression protects against age-related cognitive decline through FGF23 signalling.
37. Spermidine induces autophagy and extends healthspan via TFEB activation.

---

## Scoring rubric

Score each system per question. Keep the graph and LLM fixed so the framework is
the only variable.

| Dimension | Scale | Notes |
|---|---|---|
| Answered at all | 0/1 | Did it return a non-empty, on-topic answer? |
| Factual correctness | 0–2 | Are returned entities right? Spot-check against source DBs |
| Grounding | 0–2 | Is the answer traceable to KG evidence, or LLM-generated prose? |
| Verdict quality | 0–2 | Tier 5 only: is there an accept/reject with confidence? |
| Latency | seconds | Wall-clock per question |
| LLM calls | count | BioChatter uses 4–5 per question; EvoAge more |

**Report per tier, not just as one total.** A single aggregate number hides the
finding that matters — that the two systems fail in *different places* for
*structural* reasons.

## What the honest headline claim is

Not "EvoAge scores higher than BioChatter." A reviewer will note the two tools
were built for different jobs.

The defensible claim, which the data above supports:

> On retrieval-answerable questions, EvoAge is competitive with BioChatter on
> the same graph and the same LLM. On cross-species orthology reasoning and on
> hypothesis evaluation over triples absent from the graph, BioChatter has no
> mechanism to compete — it is retrieval-only, with no embedding model and no
> scoring — while EvoAge returns a scored, classified verdict.

That is a capability-coverage argument, and it is much harder to attack than a
contested accuracy delta.

## Caveats to disclose

1. BioChatter's prompt was hand-tuned with EvoAge-specific conventions (label
   semantics, `id` vs `name`, `name_lower` matching, mandatory `LIMIT`). This
   makes the baseline **stronger**, which is the conservative direction — but
   state it.
2. BioChatter's vector-store RAG path over literature was **not** set up. Any
   claim about its retrieval breadth is therefore incomplete.
3. `DatabaseAgent.connect()` in biochatter 0.14.2 is patched locally to fix an
   upstream credential-passing bug (see `Biochatter/README.md`).
4. KRAGEN is a closer architectural comparison for the hypothesis task than
   BioChatter, since it also does hypothesis reasoning. Consider leading the
   hypothesis comparison with KRAGEN and using BioChatter for the retrieval one.
