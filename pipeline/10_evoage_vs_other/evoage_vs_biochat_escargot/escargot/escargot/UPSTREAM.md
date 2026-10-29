# Vendored upstream Escargot

This directory is the **unmodified** published Escargot framework, vendored so
the benchmark runs without a network fetch.

    source : https://github.com/EpistasisLab/escargot.git
    commit : 936a005
    licence: MIT (see LICENSE)

Nothing here was edited. Every adaptation needed to run Escargot against the
EvoAge knowledge graph lives outside this directory, in `../evoage/`, as
subclasses and configuration — see `../ESCARGOT_CHANGES_DOCUMENTATION.md`.

Two parts of the upstream tree are omitted because they are not used by this
benchmark and are large: `benchmarking/` (its own bundled datasets and result
pickles) and `agents/` (development notebooks). Re-clone at the commit above to
obtain them.
