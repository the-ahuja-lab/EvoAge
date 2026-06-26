# EvoAge Documentation Structure

This file maps out the complete documentation architecture and how to organize all sections.

---

## **Complete Documentation Roadmap**

```
📚 EvoAge Documentation (Zensical Site)
│
├── 📄 index.md                           [LANDING PAGE - Overview & Quick Stats]
│   └── Links to all sections
│
├── 🚀 GETTING STARTED
│   ├── installation.md                   [Setup, conda env, cluster config, verification]
│   ├── quick-start.md                    [Framework overview and file checklists]
│   ├── data-collection.md                [48+ source download, categories]
│   └── preprocessing.md                  [Cleaning, standardization, validation paradigms]
│
├── 🔗 KNOWLEDGE GRAPH CONSTRUCTION
│   ├── relation-processing.md            [60+ relation types, cross-source merge notebooks]
│   ├── ortholog-mapping.md               [Ensembl Compara BioMart mapping, 121 and 121+12M]
│   └── kg-construction.md                [Splitting into Aging-Specific vs Biomedical variants]
│
├── 🧠 TENSORS & SPLITTING
│   └── kg-tensors-and-splitting.md       [Global node ID map, tensor mapping, train/valid/test splits]
│
└── 📖 REFERENCE
    └── documentation-structure.md        [Site structure and roadmap]
```

---

## **Sections to Create (Priority Order)**

### **✅ COMPLETED**
- [x] `index.md` (adapted from original `README.md`)
- [x] `installation.md` (system prerequisites, cluster template, verify script)
- [x] `quick-start.md`
- [x] `data-collection.md` (master source table — 48+ sources)
- [x] `preprocessing.md` (Paradigms A and B, ID systems, outputs)
- [x] `relation-processing.md` (reconciliations, tags, worked example)
- [x] `ortholog-mapping.md` ( BioMart e114 mapping cascade, row explosion)
- [x] `kg-construction.md` (classify logic, splits)
- [x] `kg-tensors-and-splitting.md` (global maps, integer tensor building, AB_test splits)

---

## **Converting to Website (Zensical)**

### **Step 1: Install Zensical**
```bash
conda activate evoage_env
pip install zensical
```

### **Step 2: zensical.toml**
```toml
[project]
site_name = "EvoAge"
site_description = "Multi-species aging knowledge graph platform"
site_url = "https://the-ahuja-lab.github.io/EvoAge/"
site_author = "The Ahuja Lab"
copyright = "Copyright © 2026 The Ahuja Lab"
docs_dir = "doc"

nav = [
    { "Home" = "index.md" },
    { "Quick Start" = "quick-start.md" },
    { "Installation" = "installation.md" },
    { "Data Collection" = "data-collection.md" },
    { "Preprocessing" = "preprocessing.md" },
    { "Relation Processing" = "relation-processing.md" },
    { "Ortholog Mapping" = "ortholog-mapping.md" },
    { "KG Construction" = "kg-construction.md" },
    { "Tensors & Splitting" = "kg-tensors-and-splitting.md" },
    { "Structure" = "documentation-structure.md" }
]

[project.theme]
variant = "modern"
```

### **Step 3: Build & Deploy**
```bash
zensical serve     # test locally at http://127.0.0.1:8000
zensical build     # build static site
```

---

## **Documentation Style Guide**

- Use `**bold**` for emphasis and key terms
- Use `` `code` `` for file paths, functions, variables
- Use fenced code blocks with language tags (python, bash, yaml, r)
- Use tables for comparisons and reference data
- Internal links: `[Text](file.md)` or `[Section](file.md#section-anchor)`
- Store images in `doc/images/`, reference as `![Alt text](images/filename.png)`

---

## **Maintenance & Updates**

- Keep documentation in Git alongside code
- Update `index.md` statistics when triple counts / model results change
- **Monthly**: check for broken external links
- **Quarterly**: update data statistics (triples, entities, etc.)
- **Before releases**: full content review

---

## **Deployment Checklist**

- [x] All sections created and reviewed
- [ ] Images added to `doc/images/`
- [x] `zensical.toml` configured
- [ ] Zensical builds without errors (`zensical build`)
- [ ] Tested locally (`zensical serve`)
- [x] All links validated
- [ ] GitHub Pages configured

---

**Last Updated**: June 2026
