---
created: 2026-02-24 00:52
source_url: https://www.nature.com/articles/s44335-024-00004-2
title: "PIM GPT a hybrid process in memory accelerator for ..."
search_query: "'SENTRE' PIM simulator University of Michigan"
source_index: 3
relevance_score: 0.79310596
content_source: tavily_snippet
category: web_research
tags: [web_research, auto_generated, tavily_snippet]
---

# PIM GPT a hybrid process in memory accelerator for ...

**Source**: [PIM GPT a hybrid process in memory accelerator for ...](https://www.nature.com/articles/s44335-024-00004-2)

## Snippet (via Tavily)

Download references

## Acknowledgements

This work was supported in part by the Semiconductor Research Corporation (SRC) and Defense Advanced Research Projects Agency (DARPA) through the Applications Driving Architectures (ADA) Research Center and in part by the National Science Foundation under Grant CCF-1900675 and ECCS-1915550.

## Author information

Author notes

1. These authors contributed equally: Yuting Wu, Ziyu Wang.

### Authors and Affiliations

1. Department of Electrical Engineering and Computer Science, The University of Michigan, Ann Arbor, MI, 48109, USA

   Yuting Wu, Ziyu Wang & Wei D. Lu

Authors

1. Yuting Wu

   View author publications

   Search author on:PubMed Google Scholar
2. Ziyu Wang

   View author publications [...] The transition of states follows the timing constraints. At every clock cycle, the simulator checks the status of the ASIC and the PIM package. If both are in Idle state, the current instruction is completely consumed. It then fetches the next instruction, which will be decoded into command sequences. The ASIC chip or the PIM chip will be put into Process state after the instruction is issued. The simulator will compute the time next\_time that the ASIC or relevant PIM banks will take to complete the triggered events based on the latency model. The simulator keeps track of the status of all hardware components. If the CLK reaches the next\_time, the status of the corresponding node will be changed back to Idle.

### Benchmark analysis [...] ### Simulation configuration

To evaluate the PIM-GPT system performance, we developed an event-driven clock-cycle accurate simulator in C++ that models the system behavior at token generation runtime. The simulator takes the GPT model and system configuration as inputs for model mapping. The computation graph is compiled into an instruction sequence following the hardware constraints.
