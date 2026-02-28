---
created: 2026-02-24 00:52
source_url: https://github.com/Yufeng98/CENT
title: "Yufeng98/CENT: Artifact for paper "PIM is All You Need"
search_query: "University of Michigan PIM simulator 'Centra' or 'Sentre' or 'Centaur'"
source_index: 1
relevance_score: 0.99583375
content_source: tavily_snippet
category: web_research
tags: [web_research, auto_generated, tavily_snippet]
---

# Yufeng98/CENT: Artifact for paper "PIM is All You Need

**Source**: [Yufeng98/CENT: Artifact for paper "PIM is All You Need](https://github.com/Yufeng98/CENT)

## Snippet (via Tavily)

```
@inproceedings{cent, title={PIM is All You Need: A CXL-Enabled GPU-Free System for LLM Inference}, author={Gu, Yufeng and Khadem, Alireza and Umesh, Sumanth, and Liang, Ning and Servot, Xavier and Mutlu, Onur and Iyer, Ravi and and Das, Reetuparna}, booktitle={2025 International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS)}, year={2025} } 
```

## Issues and bug reporting

We appreciate any feedback and suggestions from the community. Feel free to raise an issue or submit a pull request on Github. For assistance in using CENT, please contact: Yufeng Gu (yufenggu@umich.edu) and Alireza Khadem (arkhadem@umich.edu)

This repository is available under a MIT license. [...] ## Repository files navigation

# Artifact of the CENT Paper, ASPLOS 2025

This repository provides the following artifact required for the evaluation of CENT, "PIM is All You Need: A CXL-Enabled GPU-Free System for LLM Inference" paper published in ASPLOS 2025.

CENT

## Dependencies

AiM Simulator is tested and verified with `g++-11/12/13` and `clang++-15`. Python infrastructure requires `pandas`, `matplotlib`, `torch`, and `scipy` packages.

## Build

Clone the repository recursively:

```
cd
```

Install the Python packages locally or create a conda environment:

```
conda create -n cent python=3.10 -y conda activate cent pip install -r requirements.txt
```

Build the AiM simulator:

```
# use g++-11/12/13. e.g. (export CXX=/usr/bin/g++-12) # cd cd cd
```

## Artifact Scripts [...] | Name | Name | Last commit message | Last commit date |
 ---  --- |
| Latest commit   History50 Commits 50 Commits |
| aim\_simulator @ 2eb1ee0 | aim\_simulator @ 2eb1ee0 |  |  |
| cent\_simulation | cent\_simulation |  |  |
| cost\_model | cost\_model |  |  |
| data | data |  |  |
| figure\_scripts | figure\_scripts |  |  |
| figure\_source\_data | figure\_source\_data |  |  |
| figures | figures |  |  |
| trace | trace |  |  |
| .gitignore | .gitignore |  |  |
| .gitmodules | .gitmodules |  |  |
| CENT.png | CENT.png |  |  |
| LICENSE | LICENSE |  |  |
| README.md | README.md |  |  |
| generate\_figures.sh | generate\_figures.sh |  |  |
| remove\_old\_results.sh | remove\_old\_results.sh |  |  |
| requirements.txt | requirements.txt |  |  |
| utils.py | utils.py |  |  |
|  |
