# Drug discovery pipeline - workflow patterns, task components & tools

The drug discovery pipeline with in-silico workflows is represented below:


![Drug discovery pipeline: target ID & validation, modality/TPP decision node, modality-specific pipeline (structure/design, hit discovery, hit-to-lead, lead opt), safety/in vivo, translational, with data/ML/infrastructure and assay development as cross-cutting capabilities](assets/drug-discovery-pipeline.png)

## How to use this catalog

The short computational operations in this catalog are ingredients, not necessarily complete benchmark tasks. "Predict a structure," "dock a library," or "report ΔΔG" can test tool use, but each leaves out the judgment that determines whether the result is useful.

A strong task starts with a scientific or experimental decision and includes the upstream and parallel work needed to support it. Depending on the question, the agent may need to:

- establish the relevant biological context, state, construct, population, or assay;
- inspect candidate inputs and decide which are fit for the intended use;
- choose and validate an analysis, with quality checks focused on the region or property that affects the decision;
- reconcile independent evidence and separate direct evidence from inference and speculation;
- recommend what to advance, stop, redesign, purchase, synthesize, or test next.

The stages should be connected: an intermediate finding should be able to change a later choice. Appending unrelated analyses does not make a workflow realistic. Evaluation should reward the decision-relevant result and its supporting evidence rather than an easy global proxy or a long report.

### Control for target familiarity

Canonical targets such as HER2 and PCSK9 are useful teaching examples, but weak defaults for evaluation. An agent may recall the accepted mechanism, common structures, standard liabilities, or even a familiar experimental conclusion without doing much work on the supplied data. Agreement with that familiar story can also make a model artifact look convincing.

Use less-canonical proteins as controls. When a well-known target is scientifically useful, pair it, in the same task or elsewhere in the campaign, with a lesser-studied target that has comparable data quality. Run the same workflow on both. Build the answer from supplied measurements or a held-out dataset, and require outputs that have to be computed for this task. Renaming a famous protein does not remove what the model may know about its sequence or structure.

Obscurity is not difficulty. A control target still needs enough evidence for an expert to solve the task and for the verifier to distinguish a defensible answer from a guess.

### Cover different kinds of proteins

A collection built entirely around soluble, well-folded monomers covers only a narrow part of protein biology. Across the task set, include:

- stable monomers and flexible multi-domain proteins;
- obligate and condition-dependent oligomers or complexes;
- membrane proteins and proteins whose state depends on a ligand, cofactor, partner, or modification;
- intrinsically disordered proteins and regions, including disorder-to-order transitions;
- metastable, aggregation-prone, or poorly soluble proteins.

The category must change the work. A multimer task should make stoichiometry and assembly state matter. A disorder task may require an ensemble or a conclusion that no single stable structure is justified. An aggregation-prone target should affect construct design, purification, formulation, or advancement. Do not force all of these proteins through the same structure-and-docking template; some need class-specific methods or new tools.


## 1\. Target identification & validation

Establishing and confirming a target \- on biology **and** on tractability, competition, and patient evidence. A biologically ideal target with six clinical-stage competitors or blocking composition-of-matter claims is not a viable target.

**Representative components - biology**

- Call variants from a BAM file, filter to high-confidence sites, and report the count of pathogenic variants against a truth set.  
- Run differential expression on bulk RNA-seq and return a ranked gene list scored against a reference.  
- Cluster a single-cell dataset and recover annotated cell-type marker genes.  
- Score a CRISPR knockout screen and confirm recovery of known essential genes.  
- Run pathway/GO enrichment on a gene set and return the top enriched terms.  
- Detect binding pockets on a target structure and report a druggability score. 

**Representative components - human genetics**

- Run MR / GWAS colocalization and recover known gene–trait links.  
- Score loss-of-function tolerance for a candidate target.

**Representative components - clinical precedent & tractability**

- Score a target's clinical precedent and assign a tractability bucket.  
- Map a target to historical trial outcomes; infer a safety prior from human LoF data. 

**Representative components - biomarker & patient fraction**

- Identify a stratifying biomarker and estimate the addressable patient fraction. 


**Tools commonly used:** GATK, bcftools, samtools, DESeq2, edgeR, Scanpy, Seurat, MAGeCK, GSEA, g:Profiler, STRING, fpocket; Open Targets & Open Targets Genetics, GWAS Catalog, gnomAD, ChEMBL, DGIdb, Pharos/IDG; ClinicalTrials.gov, SureChEMBL / patent databases; TCGA, GTEx.

---

## 2\. Modality & Target Product Profile (TPP) decision node

This is the point where the pipeline diverges. It carries the Target Product Profile (route, exposure, target tissue, safety window, PD readout) and selects the modality that best addresses the target. In an idealized, modality-agnostic pipeline this follows Target ID; in the common real-world case modality is fixed upfront and instead *constrains* target selection \- the backbone supports either reading.

**Representative workflow components**

- Given target properties \+ TPP constraints, recommend feasible modalities with a justification, scored against an expert-labeled key.  
- Check modality-specific feasibility gates: surface accessibility/epitope (antibody, CAR-T), ligandable surface \+ E3 co-expression (degrader), accessible transcript \+ hepatic/GalNAc delivery \+ conservation (oligo), internalization (ADC).

**Tools commonly used:** Human Protein Atlas, GTEx (expression/surface-ome), structure & ligandability tools (fpocket, DoGSiteScorer), sequence conservation utilities.

---

## 3\. Structure determination & modeling

Small-molecule and protein core shown here; modality-specific structure/design variants are in section 7\. Structure prediction, refinement, molecular dynamics, RMSD, TM-score, and ΔΔG are useful components. The task should usually ask whether a model supports a particular use, which state should be analyzed, or what mechanism and experiment best explain a result.

### Structure-quality triage

Ask the agent to audit experimental and predicted structures before using one downstream:

- Classify the structural regime first: stable monomer, flexible multi-domain protein, biological assembly, membrane protein, disordered ensemble, or aggregation-prone system. Decide whether the application needs one structure, several conformational states, an explicit assembly, or an ensemble.
- Identify domain boundaries, construct differences, missing or unresolved regions, alternate conformations, cofactors, ligands, relevant post-translational modifications, membrane context, and biological oligomeric state.
- Check experimental quality and predicted confidence at residue level. A good global resolution, TM-score, or predicted confidence score can hide a poor binding pocket, interface, catalytic loop, or mutation site.
- Compare coverage and local quality across candidates. Mark residues or regions that should not be repaired automatically or trusted in docking, mutational analysis, epitope design, or simulation.
- Select and prepare the model that matches the application, or conclude that none of the available structures is adequate.

Predicted coordinates are not proof of a stable fold. AlphaFold 2 models with low pLDDT often correspond to regions that are disordered in isolation, and the coordinates do not represent a conformational ensemble. AlphaFold 3 can also produce rare, low-confidence hallucinations in disordered regions, sometimes as apparently ordered alpha helices. See the [AlphaFold human-proteome study](https://www.nature.com/articles/s41586-021-03828-1) and [EMBL-EBI guidance on AlphaFold 3 limitations](https://www.ebi.ac.uk/training/online/courses/alphafold/alphafold-3-and-alphafold-server/introducing-alphafold-3/what-alphafold-3-struggles-with/).

A predicted helix in a disordered region may be real, conditionally formed, or spurious; the coordinate alone cannot decide. Check confidence, sequence-based disorder, interaction context, and experimental evidence before using such a region as a pocket or interface.

Example workflow: select a model for designing inhibitors of a protein-protein interface. Determine whether the available experimental and predicted structures capture the relevant complex and interface, map uncertainty on both partners, choose a model and preparation protocol, and make a proceed/stop recommendation for docking.

### Conformational-state selection

Many targets have several relevant states. Give the agent apo and ligand-bound, active and inactive, or open and closed structures and ask it to:

- establish which state is biologically relevant to the proposed intervention;
- compare local geometry and pocket or interface accessibility across states;
- determine whether a target site is persistent, transient, or state-dependent;
- choose the conformation or ensemble appropriate for docking, simulation, or design, with a rationale tied to the mechanism.

The best "druggable" structure may be an ATP-bound state, an apo state, a specific oligomer, or an ensemble. It is not necessarily the structure with the best global quality metric.

### Mechanistic mutation analysis

Replace a bare "introduce a mutation and report ΔΔG" task with a mechanistic investigation. Based on supplied literature, sequence evidence, and suitable structures, ask the agent to prioritize whether a disease-associated mutation changes:

- global folding stability or local flexibility;
- a ligand, protein, nucleic-acid, or membrane-binding interface;
- a catalytic site or an allosteric network;
- oligomerization;
- membrane trafficking or cellular localization.

The workflow can combine local structural contacts, conservation, stability calculations, interface analysis, state comparisons, and focused dynamics. The final result should rank plausible mechanisms, distinguish evidence from speculation, and propose an experiment that discriminates among them, such as thermal-stability measurements, binding kinetics, an activity assay, oligomer-state measurements, or cellular-localization imaging.

### Experimental construct design and purification

Connect modeling to a construct that could be tested in the laboratory. A task can ask the agent to rank candidate proteins or construct boundaries, assess expression and solubility risk, and design a purification strategy. Relevant checks include:

- signal peptides, transmembrane segments, domain boundaries, disordered tails, aggregation-prone regions, disulfides, and required cofactors or modifications;
- truncations or stabilizing mutations that preserve the active site, interface, oligomeric state, and intended conformation;
- tag placement, linkers, and protease-cleavage sites, favoring termini or disordered tails and using accessible loops only when the structure supports it;
- predicted expression and solubility risks, plus experiments to confirm folding, oligomerization, and function.

The output should recommend a small number of testable constructs and explain the trade-offs rather than select a sequence from a solubility score alone.

**Tools commonly used:** RCSB PDB / PDBe, UniProt, AlphaFold DB, AlphaFold2/3, ColabFold, MODELLER, Rosetta, PDBFixer, MolProbity, Phenix, RELION, cryoSPARC, ChimeraX, PyMOL, PISA, fpocket, GROMACS, OpenMM, AMBER, MDAnalysis, mdtraj, FoldX, DisProt, MobiDB, IUPred2A, SignalP, TMHMM, CamSol, Protein-Sol.

---

## 4\. Hit discovery / screening

Small-molecule branch shown here; modality-specific hit discovery is in section 7\.

A docking score is evidence, not an advancement decision. A virtual hit still has to be chemically credible, obtainable, compatible with the assay, and worth spending money or synthesis time on.

Use medicinal and synthetic chemistry judgment when defining tractability. A generic synthetic-accessibility score is a useful warning signal, but it does not replace a plausible route, available starting materials, and review by someone who could make the compound.

**Representative workflows**

- Audit and standardize a screening library, enumerate relevant protonation and tautomer states, remove duplicates and chemically invalid entries, and flag reactive or assay-interfering compounds. Report how the filtering affects chemical diversity, not only the passing count.
- Select an appropriate receptor state and validate a docking protocol by redocking, decoy enrichment, or recovery of known interactions. Screen the library, inspect pose plausibility and strain, and test whether the ranking is robust to receptor state or an orthogonal scoring method.
- Build a pharmacophore or QSAR model, evaluate it with a scaffold-aware or temporal split, define its applicability domain, and use it alongside structure-based evidence. The workflow should explain disagreements between methods rather than average scores blindly.
- For generated molecules or fragment-growing/linking proposals, check chemical validity, novelty, route plausibility, starting-material availability, and the property constraints that matter for the target and assay.
- Triage virtual hits on selectivity, solubility, aggregation, permeability where relevant, chemical stability, storage and formulation, supplier availability, cost, and synthetic accessibility. A compound that needs a solvent concentration that damages the protein or cells is not an experimentally useful hit.
- Recommend a diverse purchase, synthesis, and testing set. Specify assay concentrations, solvent constraints, controls, and orthogonal or counter-screens that can distinguish binding from aggregation, fluorescence interference, nonspecific reactivity, or another assay artifact.

Example workflow: reduce a virtual screen to a small panel that a project team should purchase or synthesize. Use validated pose evidence, ligand-based evidence, chemical and formulation liabilities, availability or route feasibility, and assay compatibility. Explain every rejection and advancement, then propose the first experimental screen and its controls.

**Tools commonly used:** RDKit, Open Babel, AutoDock Vina, Smina, DOCK, Pharmit, scikit-learn, DeepChem, Chemprop, REINVENT, GuacaMol / MOSES, GROMACS, Boltz-2, AiZynthFinder, ASKCOS, vendor catalogs and retrosynthesis tools.

---

## 5\. Hit-to-lead & lead optimization

Binding affinity is necessary but not sufficient; series ranking must connect target engagement to function. Efficacy readouts are assay-driven (see section 8, assay development).

**Representative components**

- Run relative free-energy calculations on a congeneric series and match the experimental affinity ranking.  
- Compute a reaction barrier or covalent-warhead energetics with QM / QM-MM.  
- Estimate a k\_off-related observable (residence time) from enhanced-sampling trajectories.  
- Apply matched-molecular-pair transforms and predict the resulting activity shift.  
- Score a candidate against an off-target/selectivity panel and flag liabilities.  
- Predict a functional / phenotypic response (e.g., transcriptomic signature reversal) and rank leads on it, not on affinity alone. 

**Tools commonly used:**

OpenFE, Amber TI, Psi4, ORCA, xtb, GROMACS, PLUMED, mmpdb, SwissTargetPrediction, SEA; connectivity/signature tools (e.g., LINCS/L1000 analysis), AlphaFold, and MD simulation.

---

## 6\. ADMET, PK/PD & safety

**Representative components**

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

Five example branches mapped onto the backbone. In each case, the task should end in a multi-criterion advancement or redesign decision. The strongest binding, ternary-complex, or hybridization score is rarely the answer by itself.

### Antibody

Give the agent a panel of variants and the intended product mechanism, then ask it to integrate:

- recognition of the relevant membrane-bound, soluble, active, or inactive antigen form and epitope accessibility in that state;
- species cross-reactivity needed for preclinical studies and the risk of cross-reactivity with related human proteins;
- affinity and binding kinetics, including pH-dependent binding when recycling or intracellular trafficking matters;
- expression and sequence liabilities, chemical modification sites, aggregation, viscosity, self-association, and polyspecificity;
- the intended Fc activity, specificity, immunogenicity risk, and routes of antigen escape.

Example workflow: rank antibody variants using binding and kinetic data, expression, aggregation, polyspecificity, epitope/state data, and sequence liabilities. Recommend a small set for experimental advancement, explain the trade-offs, and name the assays that would resolve the remaining uncertainty.

**Tools:** ABodyBuilder2, IgFold, AlphaFold-Multimer, RosettaAntibody, TAP (developability), BioPhi/Sapiens (humanization), NetMHCIIpan.

### Antibody–drug conjugate (ADC)

- Confirm that the relevant antigen state has sufficient tumor-selective expression, epitope accessibility, and internalization.
- Integrate linker plasma stability, intracellular release, payload potency and bystander effect, conjugation-site effects, and the drug-to-antibody-ratio distribution.
- Rank designs on expected efficacy, manufacturability, and systemic payload exposure, then recommend experiments that test the largest uncertainty.

**Tools:** RDKit, DeepChem, Chemprop, cheminformatics stability models.

### Degrader / PROTAC

Ternary-complex stability or cooperativity alone does not establish productive degradation. An integrated workflow can evaluate:

- expression of the selected E3 ligase in the relevant tissue and cell type, plus its subcellular colocalization with the target;
- target accessibility and presentation of lysines that can support productive ubiquitination;
- binary target and E3 engagement, ternary-complex geometry and dynamics, and cooperativity without treating any one metric as decisive;
- linker length, exit vectors, geometry, and conformational behavior;
- permeability, solubility, efflux risk, and metabolic stability;
- degradation kinetics, DC50, Dmax, and a possible hook effect across concentration;
- proteome-wide degradation selectivity and resistance mechanisms involving the target, E3 ligase, or other degradation machinery.

Example workflow: diagnose why a compound binds its target but produces little cellular degradation. Decide whether the limiting factor is exposure, E3 context, localization, ternary geometry, ubiquitination competence, or degradation kinetics, then recommend the next linker, ligand, E3, or assay change.

**Tools:** PRosettaC, Rosetta / ICM (ternary), RDKit, DeLinker / Link-INVENT (linker generation).

### Oligonucleotide (siRNA / ASO)

Start from the therapeutic mechanism and tissue rather than from duplex thermodynamics. Ask the agent to:

- select the relevant transcript and isoform and decide whether the goal is allele-specific or total knockdown, splice correction, or another RNA effect;
- choose among siRNA, gapmer ASO, splice-switching ASO, or another mechanism based on the desired RNA change and cellular compartment;
- evaluate target-site accessibility, RNA structure, duplex thermodynamics, and isoform coverage;
- choose a chemical modification pattern and assess nuclease stability and innate immune activation motifs;
- evaluate seed-mediated and hybridization-dependent off-targets;
- account for tissue and cell delivery, species conservation for preclinical studies, dose-dependent toxicity, and a relevant pharmacodynamic readout.

Example workflow: rank oligonucleotide candidates for an in vivo program using isoform coverage, mechanism, accessibility, off-targets, chemistry, delivery, conservation, safety, and PD evidence. A sequence should not advance solely because its predicted duplex is favorable.

**Tools:** ViennaRNA (RNAfold, RNAplfold), mfold / RNAstructure, Bowtie / BLAST (off-target), siRNA design utilities (siDESIGN, DSIR).

### Cell therapy (CAR-T)

- Confirm the disease-relevant antigen state, density, heterogeneity, normal-tissue expression, and plausible escape routes.
- Tune the scFv affinity and kinetic window against on-target/off-tumor risk and cross-reactivity.
- Compare hinge, transmembrane, and costimulatory designs for epitope geometry, expression, tonic signaling, and the intended persistence or activation profile.
- Recommend constructs and experiments that test specificity, function across antigen density, exhaustion, and antigen escape.

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

**Representative components**

- Identify predictive biomarkers from omics data and report classification/regression performance.  
- Run a survival or regression analysis on trial data and match an expected estimate.  
- Mine an adverse-event database and return a disproportionality statistic (PRR / ROR). 

**Tools commonly used:** scikit-learn, lifelines, statsmodels, R (survival, limma), FAERS / OpenVigil, PharmGKB.
