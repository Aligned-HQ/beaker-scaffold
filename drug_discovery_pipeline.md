# Drug discovery pipeline \- representative tasks & tools

The drug discovery pipeline with in-silico workflows is represented below:


![Drug discovery pipeline: target ID & validation, modality/TPP decision node, modality-specific pipeline (structure/design, hit discovery, hit-to-lead, lead opt), safety/in vivo, translational, with data/ML/infrastructure and assay development as cross-cutting capabilities](assets/drug-discovery-pipeline.png)


## 1\. Target identification & validation

Establishing and confirming a target \- on biology **and** on tractability, competition, and patient evidence. A biologically ideal target with six clinical-stage competitors or blocking composition-of-matter claims is not a viable target.

**Representative tasks \- biology**

- Call variants from a BAM file, filter to high-confidence sites, and report the count of pathogenic variants against a truth set.  
- Run differential expression on bulk RNA-seq and return a ranked gene list scored against a reference.  
- Cluster a single-cell dataset and recover annotated cell-type marker genes.  
- Score a CRISPR knockout screen and confirm recovery of known essential genes.  
- Run pathway/GO enrichment on a gene set and return the top enriched terms.  
- Detect binding pockets on a target structure and report a druggability score. 

**Representative tasks \- human genetics**

- Run MR / GWAS colocalization and recover known gene–trait links.  
- Score loss-of-function tolerance for a candidate target.

**Representative tasks \- clinical precedent & tractability**

- Score a target's clinical precedent and assign a tractability bucket.  
- Map a target to historical trial outcomes; infer a safety prior from human LoF data. 

**Representative tasks \- biomarker & patient fraction**

- Identify a stratifying biomarker and estimate the addressable patient fraction. 


**Tools commonly used:** GATK, bcftools, samtools, DESeq2, edgeR, Scanpy, Seurat, MAGeCK, GSEA, g:Profiler, STRING, fpocket; Open Targets & Open Targets Genetics, GWAS Catalog, gnomAD, ChEMBL, DGIdb, Pharos/IDG; ClinicalTrials.gov, SureChEMBL / patent databases; TCGA, GTEx.

---

## 2\. Modality & Target Product Profile (TPP) decision node

The point where the pipeline diverges. It carries the Target Product Profile (route, exposure, target tissue, safety window, PD readout) and selects the modality that best addresses the target. In an idealized, modality-agnostic pipeline this follows Target ID; in the common real-world case modality is fixed upfront and instead *constrains* target selection \- the backbone supports either reading.

**Representative tasks**

- Given target properties \+ TPP constraints, recommend feasible modalities with a justification, scored against an expert-labeled key.  
- Check modality-specific feasibility gates: surface accessibility/epitope (antibody, CAR-T), ligandable surface \+ E3 co-expression (degrader), accessible transcript \+ hepatic/GalNAc delivery \+ conservation (oligo), internalization (ADC).

**Tools commonly used:** Human Protein Atlas, GTEx (expression/surface-ome), structure & ligandability tools (fpocket, DoGSiteScorer), sequence conservation utilities.

---

## 3\. Structure determination & modeling

Small-molecule and protein core shown here; modality-specific structure/design variants are in section 7\.

**Representative tasks**

- Predict a protein structure and report TM-score / RMSD versus a reference.  
- Build a homology model and validate geometry against quality thresholds.  
- Process a cryo-EM map (refine/fit) and return a resolution or fit metric.  
- Run a molecular dynamics simulation and compute an observable (RMSF, cryptic-pocket occupancy).  
- Introduce a mutation and report a predicted stability change (ΔΔG). 

**Tools commonly used:** AlphaFold2/3, ColabFold, MODELLER, Rosetta, RELION, cryoSPARC, GROMACS, OpenMM, AMBER, MDAnalysis, mdtraj, FoldX.

---

## 4\. Hit discovery / screening

Small-molecule branch shown here; modality-specific hit discovery is in section 7\.

**Representative tasks**

- Standardize and filter a compound library (salts, valence, PAINS/Lipinski) and return the passing count.  
- Dock a compound set into a binding site and report pose RMSD or top-N enrichment.  
- Build a pharmacophore from known actives, screen a library, and recover seeded actives.  
- Train a QSAR model on an activity dataset and report held-out AUC / RMSE against a threshold.  
- Generate novel molecules under property constraints and validate that outputs meet them.  
- Grow or link fragment hits and return scored, chemically valid products. 

**Tools commonly used:** RDKit, Open Babel, AutoDock Vina, Smina, DOCK, Pharmit, scikit-learn, DeepChem, Chemprop, REINVENT, GuacaMol / MOSES, GROMACS, Boltz-2 

---

## 5\. Hit-to-lead & lead optimization

Binding affinity is necessary but not sufficient; series ranking must connect target engagement to function. Efficacy readouts are assay-driven (see section 8, assay development).

**Representative tasks**

- Run relative free-energy calculations on a congeneric series and match the experimental affinity ranking.  
- Compute a reaction barrier or covalent-warhead energetics with QM / QM-MM.  
- Estimate a k\_off-related observable (residence time) from enhanced-sampling trajectories.  
- Apply matched-molecular-pair transforms and predict the resulting activity shift.  
- Score a candidate against an off-target/selectivity panel and flag liabilities.  
- Predict a functional / phenotypic response (e.g., transcriptomic signature reversal) and rank leads on it, not on affinity alone. 

**Tools commonly used:** OpenFE, Amber TI, Psi4, ORCA, xtb, GROMACS, PLUMED, mmpdb, SwissTargetPrediction, SEA; connectivity/signature tools (e.g., LINCS/L1000 analysis)., alphafold and MD simulation  
---

## 6\. ADMET, PK/PD & safety

**Representative tasks**

- Predict an ADMET property (solubility, permeability, clearance) and report a metric versus a holdout set.  
- Classify a safety liability (hERG, hepatotoxicity) and return AUC / confusion statistics.  
- Parameterize a PBPK model, simulate a dose, and match target Cmax / AUC.  
- Fit a dose–response curve and recover PK/PD parameters (EC50, Emax).  
- Predict site of metabolism and match the annotated position. Modality-specific safety surrogates: immunogenicity (biologics), payload systemic tox (ADC), immunostimulation/TLR (oligo), cross-reactivity & CRS risk (CAR-T) \- see section 7\.  
- Iteratively optimize molecular structures and validate predicted ADMET profile enhancements.  
- Improve on multiple ADMET properties without losing too much target binding affinity

**Tools commonly used:** ADMET-AI, admetSAR, pkCSM, SwissADME, DeepChem, PK-Sim / MoBi, Simcyp, Monolix, nlmixr2, FAME.

---

## 7\. Modality-specific pipelines

Five example branches mapped onto the backbone, listing the in-silico, verifiable tasks for each modality.

### Antibody \- *e.g., HER2*

- Model the Fv/CDR and dock the paratope–epitope interface; report interface quality vs. reference.  
- Predict developability/aggregation liability from sequence and flag hotspots.  
- Score humanization and remove liability motifs while preserving predicted binding.  
- Predict MHC-II immunogenicity epitopes.

**Tools:** ABodyBuilder2, IgFold, AlphaFold-Multimer, RosettaAntibody, TAP (developability), BioPhi/Sapiens (humanization), NetMHCIIpan.

### Antibody–drug conjugate (ADC) \- *e.g., TROP2*

- Predict plasma linker stability from structure.  
- Build a payload-potency QSAR and report held-out performance.  
- Model the DAR distribution and select a conjugation site under stability/efficacy constraints.

**Tools:** RDKit, DeepChem, Chemprop, cheminformatics stability models.

### Degrader / PROTAC \- *e.g., BRD4 via CRBN*

- Model the ternary complex (target–PROTAC–E3) and estimate cooperativity (α).  
- Generatively design linkers under geometric/length constraints and validate chemistry.  
- Build a DC50/Dmax predictive model and rank candidates.

**Tools:** PRosettaC, Rosetta / ICM (ternary), RDKit, DeLinker / Link-INVENT (linker generation).

### Oligonucleotide (siRNA / ASO) \- *e.g., PCSK9 mRNA*

- Predict mRNA secondary structure and accessible regions; compute duplex thermodynamics.  
- Run a genome-wide off-target hybridization search and quantify seed-mediated risk.  
- Score 2′\-modification / phosphorothioate patterns against design rules.

**Tools:** ViennaRNA (RNAfold, RNAplfold), mfold / RNAstructure, Bowtie / BLAST (off-target), siRNA design utilities (siDESIGN, DSIR).

### Cell therapy (CAR-T) \- *e.g., CD19*

- Model the scFv binder and tune the affinity window vs. on-target/off-tumor risk.  
- Predict normal-tissue antigen cross-reactivity from expression atlases and sequence/structure similarity.  
- Design the CAR construct (hinge / TM / costim) in silico and check expression determinants.

**Tools:** IgFold / ABodyBuilder2, AlphaFold-Multimer, Human Protein Atlas / GTEx, sequence-similarity tooling.

---

## 8\. Cross-cutting capabilities

Shared work that supports every stage. Two capabilities, each with stage hooks.

### 8a. Data / ML / infrastructure

- Build an ML baseline on a bio/chem dataset and clear a defined performance floor.  
- Clean a messy assay-data export and return a validated schema (types, ranges, deduped IDs).  
- Fix a broken analysis pipeline and reproduce a previously reported number.  
- Generate molecular fingerprints or embeddings and verify their shape and properties.

**Tools:** scikit-learn, PyTorch, XGBoost, pandas, Polars, Snakemake, Nextflow, MLflow, DVC, RDKit / Mordred / molfeat, Modal.

### 8b. Assay development

Assay development recurs rather than sitting at one point: screening assays feed hit discovery, potency/selectivity assays feed lead optimization, PD/biomarker assays feed translational.

- Fit dose–response and recover IC50 / EC50 / DC50 with quality flags.  
- Analyze a screen (normalization, Z′-factor, hit-calling) and return QC-passing hits.  
- Predict an assay readout (e.g., cytotoxicity, knockdown) and report a metric vs. holdout.  
- Build a plate-QC / normalization pipeline and validate against expected controls.

**Tools:** scikit-learn, statsmodels, R (drc, dr4pl), pandas, plate-QC utilities.

---

## 9\. Translational / clinical-adjacent

Bridging discovery to the clinic \- biomarkers, trial data, and safety signals. Modality-specific PD biomarkers apply (e.g., target-protein knockdown for degraders/oligos; antigen-escape surveillance for CAR-T).

**Representative tasks**

- Identify predictive biomarkers from omics data and report classification/regression performance.  
- Run a survival or regression analysis on trial data and match an expected estimate.  
- Mine an adverse-event database and return a disproportionality statistic (PRR / ROR). 

**Tools commonly used:** scikit-learn, lifelines, statsmodels, R (survival, limma), FAERS / OpenVigil, PharmGKB.
