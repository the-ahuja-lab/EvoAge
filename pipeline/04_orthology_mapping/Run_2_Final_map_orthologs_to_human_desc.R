library(biomaRt)
library(gprofiler2)     # g:Convert for robust, cross-namespace symbol -> Ensembl ID
library(dplyr)
library(readr)
library(stringr)
library(purrr)

# biomaRt pulls in AnnotationDbi, whose select()/etc. mask dplyr verbs.
# Force dplyr versions so the pipeline doesn't break mid-run.
select <- dplyr::select
filter <- dplyr::filter
count  <- dplyr::count
slice  <- dplyr::slice
rename <- dplyr::rename

# ---- Config -----------------------------------------------------------------
ENSEMBL_VERSION <- 114            # matches g:Profiler e114
CHUNK_SIZE      <- 200            # IDs per homolog request (keep small for stability)
MAX_TRIES       <- 5             # retries per request on transient 500s
# e114 = May 2025 archive host (stable, separate server -> avoids the default
# mirror's HTTP 500s and pins the release for reproducibility).
ENSEMBL_HOST    <- "https://may2025.archive.ensembl.org"
MIRRORS         <- c("www", "useast", "uswest", "asia")  # fallbacks if host is unreachable
OUTDIR          <- "Human_Ortholog_Mapping_final"
dir.create(OUTDIR, recursive = TRUE, showWarnings = FALSE)

# ---- g:Profiler version pinning ---------------------------------------------
GP_TARGET_ENSEMBL <- ENSEMBL_VERSION          # 114
GP_ARCHIVE_VER    <- "e114_eg62_p19"          # archive id, used only if 114 is no longer current
GP_DEFAULT_URL    <- "https://biit.cs.ut.ee/gprofiler"
GP_CHUNK          <- 1000                     # genes per g:Convert request (large lists -> chunk)
GP_NUMERIC_NS     <- ""

species_info <- tribble(
  ~species_name, ~file,                        ~gene_col,        ~dataset,                    ~species_label,                ~gp_organism,
  "Yeast",       "Yeast_unique_genes.csv",      "Yeast_gene",     "scerevisiae_gene_ensembl",  "Saccharomyces cerevisiae",    "scerevisiae",
  "Celegans",    "Celegans_unique_genes.csv",   "Celegans_gene",  "celegans_gene_ensembl",     "Caenorhabditis elegans",      "celegans",
  "Drosophila",  "Drosophila_unique_genes.csv", "Droso_gene",     "dmelanogaster_gene_ensembl","Drosophila melanogaster",     "dmelanogaster",
  "Mouse",       "Mouse_unique_genes.csv",      "Mouse_gene",     "mmusculus_gene_ensembl",    "Mus musculus",                "mmusculus",
  "Zebrafish",   "Zebrafish_unique_genes.csv",  "Zebrafish_gene", "drerio_gene_ensembl",       "Danio rerio",                 "drerio"
)

norm_key <- function(x) toupper(trimws(x))

HOM_ATTRS <- c(
  "ensembl_gene_id",
  "external_gene_name",
  "hsapiens_homolog_ensembl_gene",
  "hsapiens_homolog_associated_gene_name",
  "hsapiens_homolog_orthology_type",
  "hsapiens_homolog_orthology_confidence",
  "hsapiens_homolog_perc_id"
)

# ---- Robust mart connection: e114 archive host ONLY (no silent mirror fallback) -
CONNECT_TRIES <- 15
ALLOW_MIRROR_FALLBACK <- FALSE
connect_mart <- function(dataset) {
  for (attempt in seq_len(CONNECT_TRIES)) {
    m <- tryCatch(useEnsembl(biomart = "genes", dataset = dataset, host = ENSEMBL_HOST),
                  error = function(e) {
                    message(sprintf("  [connect e114 host] attempt %d/%d failed: %s",
                                    attempt, CONNECT_TRIES, conditionMessage(e)))
                    Sys.sleep(min(10 * attempt, 30))
                    NULL
                  })
    if (!is.null(m)) { message(sprintf("  >> connected to e114 archive (attempt %d)", attempt)); return(m) }
  }
  if (ALLOW_MIRROR_FALLBACK) {
    for (mir in MIRRORS) {
      m <- tryCatch(useEnsembl(biomart = "genes", dataset = dataset, mirror = mir),
                    error = function(e) NULL)
      if (!is.null(m)) { message(sprintf("  >> WARNING: mirror '%s' = CURRENT release, NOT e114", mir)); return(m) }
    }
  }
  stop("e114 archive host (", ENSEMBL_HOST, ") unreachable after ", CONNECT_TRIES,
       " tries. This is usually a short Ensembl outage window. Wait a few minutes and rerun. ",
       "Do NOT enable mirror fallback for the paper -- mirrors serve the current release, not e114.")
}

# ---- Retry wrapper for any getBM call ---------------------------------------
safe_getBM <- function(..., label = "query") {
  for (attempt in seq_len(MAX_TRIES)) {
    res <- tryCatch(getBM(...), error = function(e) {
      message(sprintf("  [%s] attempt %d/%d failed: %s", label, attempt, MAX_TRIES, conditionMessage(e)))
      Sys.sleep(3 * attempt)
      NULL
    })
    if (!is.null(res)) return(res)
  }
  stop(sprintf("[%s] failed after %d attempts.", label, MAX_TRIES))
}

# ---- Resolve which g:Profiler release to use (and report it) ----------------
setup_gprofiler <- function() {
  ver_of <- function(tag) {
    vi <- tryCatch(get_version_info(organism = "hsapiens"), error = function(e) NULL)
    if (is.null(vi)) { message(sprintf("  [g:Profiler %s] version check failed (network?)", tag)); return(NULL) }
    message(sprintf("  [g:Profiler %s] version=%s  (Ensembl %s)",
                    tag, vi$gprofiler_version, vi$biomart_version))
    vi
  }
  gprofiler2::set_base_url(GP_DEFAULT_URL)
  vi <- ver_of("current")
  if (!is.null(vi) && vi$biomart_version == as.character(GP_TARGET_ENSEMBL)) {
    message("  >> g:Profiler current release IS Ensembl ", GP_TARGET_ENSEMBL,
            " -- using default URL (no archive needed).")
    return(invisible(vi$gprofiler_version))
  }
  arch <- paste0("https://biit.cs.ut.ee/gprofiler_archive3/", GP_ARCHIVE_VER)
  message("  current release != Ensembl ", GP_TARGET_ENSEMBL, "; trying archive: ", arch)
  gprofiler2::set_base_url(arch)
  vi2 <- ver_of("archive")
  if (!is.null(vi2) && vi2$biomart_version == as.character(GP_TARGET_ENSEMBL)) {
    message("  >> pinned to g:Profiler archive ", GP_ARCHIVE_VER)
    return(invisible(vi2$gprofiler_version))
  }
  gprofiler2::set_base_url(GP_DEFAULT_URL)
  vi3 <- ver_of("fallback-current")
  warning("Could not pin g:Convert to Ensembl ", GP_TARGET_ENSEMBL,
          ". Using current release",
          if (!is.null(vi3)) paste0(" (", vi3$gprofiler_version, ")") else "",
          ". Symbol->ID resolution may be ~1 Ensembl release off the homolog query.")
  invisible(if (!is.null(vi3)) vi3$gprofiler_version else NA_character_)
}

# ---- chunked + retried g:Convert --------------------------------------------
safe_gconvert <- function(genes, gp_org) {
  genes <- unique(genes)
  if (!length(genes)) return(tibble(input = character(), target = character()))
  chunks <- split(genes, ceiling(seq_along(genes) / GP_CHUNK))
  out <- vector("list", length(chunks))
  for (j in seq_along(chunks)) {
    cat(sprintf("  gconvert chunk %d/%d (%d genes)\n", j, length(chunks), length(chunks[[j]])))
    res <- NULL
    for (attempt in seq_len(MAX_TRIES)) {
      res <- tryCatch(
        gconvert(query = chunks[[j]], organism = gp_org, target = "ENSG",
                 numeric_ns = GP_NUMERIC_NS, mthreshold = Inf, filter_na = TRUE),
        error = function(e) {
          message(sprintf("    [gconvert chunk %d] attempt %d/%d failed: %s",
                          j, attempt, MAX_TRIES, conditionMessage(e)))
          Sys.sleep(3 * attempt)
          NULL
        })
      if (!is.null(res)) break
    }
    if (!is.null(res) && nrow(res)) {
      res <- tibble(input  = as.character(res$input),
                    target = as.character(res$target))
    } else {
      res <- NULL
    }
    out[[j]] <- res
  }
  gc_df <- bind_rows(out)
  if (!nrow(gc_df)) return(tibble(input = character(), target = character()))
  gc_df |>
    transmute(input  = as.character(input),
              target = as.character(target)) |>
    filter(!is.na(target), !target %in% c("", "N/A", "None", "nan")) |>
    distinct()
}

# ---- Resolve input genes -> source Ensembl IDs (g:Convert + biomaRt fallback) -
resolve_to_ensembl <- function(genes, gp_org, id_map) {
  gc_df <- safe_gconvert(genes, gp_org)
  resolved <- gc_df |>
    transmute(input_gene = input, ensembl_gene_id = target) |>
    distinct()
  cat("  g:Convert resolved:", n_distinct(resolved$input_gene), "/", length(unique(genes)), "input genes\n")
  
  still <- setdiff(unique(genes), resolved$input_gene)
  if (length(still)) {
    sk <- norm_key(still)
    fb <- id_map |>
      filter(k_name %in% sk | k_id %in% sk) |>
      mutate(input_gene = if_else(k_name %in% sk,
                                  still[match(k_name, sk)],
                                  still[match(k_id, sk)])) |>
      transmute(input_gene, ensembl_gene_id) |>
      filter(!is.na(ensembl_gene_id), ensembl_gene_id != "") |>
      distinct()
    if (nrow(fb)) {
      cat("  biomaRt fallback recovered:", n_distinct(fb$input_gene), "more\n")
      resolved <- bind_rows(resolved, fb) |> distinct()
    }
  }
  resolved
}

# ---- Chunked homolog query by ensembl_gene_id -------------------------------
get_homologs_chunked <- function(ids, mart) {
  ids <- unique(ids)
  chunks <- split(ids, ceiling(seq_along(ids) / CHUNK_SIZE))
  out <- vector("list", length(chunks))
  for (j in seq_along(chunks)) {
    cat(sprintf("  homolog chunk %d/%d (%d ids)\n", j, length(chunks), length(chunks[[j]])))
    res <- safe_getBM(attributes = HOM_ATTRS,
                      filters = "ensembl_gene_id", values = chunks[[j]],
                      mart = mart, label = paste0("homolog_chunk_", j))
    res[] <- lapply(res, as.character)
    out[[j]] <- res
  }
  bind_rows(out)
}

# ---- Human gene descriptions (full names) from the HUMAN mart ---------------
.human_desc_cache <- new.env(parent = emptyenv())
get_human_descriptions <- function(ids, human_mart) {
  ids <- unique(ids[!is.na(ids) & ids != ""])
  if (!length(ids)) return(tibble(ensembl_gene_id = character(), human_description = character()))
  
  miss <- ids[!vapply(ids, function(i) exists(i, envir = .human_desc_cache, inherits = FALSE), logical(1))]
  if (length(miss)) {
    chunks <- split(miss, ceiling(seq_along(miss) / CHUNK_SIZE))
    for (j in seq_along(chunks)) {
      cat(sprintf("  human-desc chunk %d/%d (%d new ids)\n", j, length(chunks), length(chunks[[j]])))
      res <- safe_getBM(attributes = c("ensembl_gene_id", "description"),
                        filters = "ensembl_gene_id", values = chunks[[j]],
                        mart = human_mart, label = paste0("humandesc_chunk_", j))
      res[] <- lapply(res, as.character)
      got <- character(0)
      if (nrow(res)) {
        clean <- trimws(sub("\\s*\\[Source:.*\\]$", "", res$description))
        clean[clean == ""] <- NA_character_
        for (r in seq_len(nrow(res))) assign(res$ensembl_gene_id[r], clean[r], envir = .human_desc_cache)
        got <- res$ensembl_gene_id
      }
      for (i in setdiff(chunks[[j]], got)) assign(i, NA_character_, envir = .human_desc_cache)
    }
  }
  tibble(
    ensembl_gene_id   = ids,
    human_description = vapply(ids, function(i) get0(i, envir = .human_desc_cache, ifnotfound = NA_character_),
                               character(1))
  )
}

# ---- Per-species processing --------------------------------------------------
process_species <- function(sp, human_mart) {
  cat("\n=====================================================\n")
  cat("Processing:", sp$species_name, "\n")
  cat("=====================================================\n")
  
  # 1. Read & clean input gene list
  df <- read_csv(sp$file, show_col_types = FALSE)
  genes <- df[[sp$gene_col]] |> trimws() |> na.omit() |> unique()
  genes <- genes[genes != "" & genes != "-"]
  inp <- tibble(input_gene = genes, k = norm_key(genes)) |> distinct(k, .keep_all = TRUE)
  cat("Input genes (cleaned, unique):", nrow(inp), "\n")
  
  # 2. Connect to SOURCE species mart (e114 archive host)
  mart <- connect_mart(sp$dataset)
  
  # 3. CHEAP id map: id + symbol for the whole genome (g:Convert fallback)
  id_map <- safe_getBM(attributes = c("ensembl_gene_id", "external_gene_name"),
                       mart = mart, label = "id_map") |>
    mutate(k_name = norm_key(external_gene_name),
           k_id   = norm_key(ensembl_gene_id))
  
  # 4. Resolve input -> Ensembl IDs via g:Convert, biomaRt as fallback
  resolved <- resolve_to_ensembl(inp$input_gene, sp$gp_organism, id_map) |>
    filter(!is.na(ensembl_gene_id), ensembl_gene_id != "") |>
    distinct()
  
  not_found <- setdiff(inp$input_gene, resolved$input_gene)
  cat("Symbols resolved to Ensembl IDs:", n_distinct(resolved$input_gene),
      "| not found:", length(not_found), "\n")
  
  # 5. Query human homologs for resolved IDs, chunked + retried
  hom <- get_homologs_chunked(unique(resolved$ensembl_gene_id), mart) |>
    filter(hsapiens_homolog_ensembl_gene != "", !is.na(hsapiens_homolog_ensembl_gene))
  
  matched <- hom |>
    inner_join(resolved, by = "ensembl_gene_id", relationship = "many-to-many") |>
    transmute(
      source_species       = sp$species_label,
      input_gene,
      source_ensembl_id    = ensembl_gene_id,
      source_symbol        = external_gene_name,
      human_ensembl_id     = hsapiens_homolog_ensembl_gene,
      human_symbol         = hsapiens_homolog_associated_gene_name,
      orthology_type       = hsapiens_homolog_orthology_type,
      orthology_confidence = suppressWarnings(as.numeric(hsapiens_homolog_orthology_confidence)),
      perc_id              = suppressWarnings(as.numeric(hsapiens_homolog_perc_id))
    ) |>
    distinct()
  
  # 5b. Attach human gene description and place it after human_symbol
  human_desc <- get_human_descriptions(matched$human_ensembl_id, human_mart)
  matched <- matched |>
    left_join(human_desc, by = c("human_ensembl_id" = "ensembl_gene_id")) |>
    relocate(human_description, .after = human_symbol)
  
  # 6. Coverage
  unmapped <- setdiff(inp$input_gene, unique(matched$input_gene))
  cat("Genes with >=1 human ortholog:", n_distinct(matched$input_gene), "\n")
  cat("Unmapped genes (no human ortholog):", length(unmapped),
      sprintf("(%.1f%%)\n", 100 * length(unmapped) / nrow(inp)))
  
  # 7. Write outputs
  sp_dir <- file.path(OUTDIR, sp$species_name)
  dir.create(sp_dir, recursive = TRUE, showWarnings = FALSE)
  
  for (t in unique(matched$orthology_type)) {
    write_csv(filter(matched, orthology_type == t),
              file.path(sp_dir, paste0(sp$species_name, "_byType_", t, ".csv")))
  }
  if (length(unmapped))  writeLines(unmapped,  file.path(sp_dir, paste0(sp$species_name, "_UNMAPPED.txt")))
  if (length(not_found)) writeLines(not_found, file.path(sp_dir, paste0(sp$species_name, "_SYMBOL_NOT_FOUND.txt")))
  
  per_gene <- matched |> count(input_gene, orthology_type, name = "n_human_orthologs") |>
    arrange(desc(n_human_orthologs))
  write_csv(per_gene, file.path(sp_dir, paste0(sp$species_name, "_PerGene_Summary.csv")))
  
  cat("one2one genes:",   n_distinct(matched$input_gene[matched$orthology_type == "ortholog_one2one"]),
      "| one2many genes:", n_distinct(matched$input_gene[matched$orthology_type == "ortholog_one2many"]),
      "| many2many genes:", n_distinct(matched$input_gene[matched$orthology_type == "ortholog_many2many"]), "\n")
  
  tibble(
    Species              = sp$species_name,
    Input_Genes          = nrow(inp),
    Symbol_Not_Found     = length(not_found),
    Mapped_Genes         = n_distinct(matched$input_gene),
    Unmapped_Genes       = length(unmapped),
    OneToOne_Genes       = n_distinct(matched$input_gene[matched$orthology_type == "ortholog_one2one"]),
    OneToMany_Genes      = n_distinct(matched$input_gene[matched$orthology_type == "ortholog_one2many"]),
    ManyToMany_Genes     = n_distinct(matched$input_gene[matched$orthology_type == "ortholog_many2many"]),
    Total_Ortholog_Pairs = nrow(matched)
  )
}

# ---- Pin / report g:Profiler release ----------------------------------------
GP_USED_VERSION <- setup_gprofiler()

# ---- Human mart for gene descriptions, same e114 host -----------------------
cat("\nConnecting to HUMAN mart (hsapiens_gene_ensembl) for gene descriptions...\n")
human_mart <- connect_mart("hsapiens_gene_ensembl")

# ---- Run all species ---------------------------------------------------------
results <- lapply(seq_len(nrow(species_info)), function(i) process_species(species_info[i, ], human_mart))

# ---- Master summary ---------------------------------------------------------
master_sum <- map_dfr(results, identity)
write_csv(master_sum, file.path(OUTDIR, "AllSpecies_Orthology_Summary.csv"))

cat("\n================ MASTER SUMMARY ================\n")
print(master_sum)
cat("\nDone. Outputs in:", normalizePath(OUTDIR), "\n")