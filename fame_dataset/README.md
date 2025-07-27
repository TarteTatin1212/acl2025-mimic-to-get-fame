# FAME Dataset

800 synthetic meeting transcripts for conversational AI and meeting summarization research.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Version](https://img.shields.io/badge/Version-0.9%20%7C%20Full%20Release%20Soon-blue.svg)]()
 [![Languages](https://img.shields.io/badge/Languages-English%20%7C%20German-navy.svg)]() [![Total Meetings](https://img.shields.io/badge/Meetings-500%20%7C%20300-green.svg)]() [![Topics](https://img.shields.io/badge/Topics-28-orange.svg)]() [![Meeting Types](https://img.shields.io/badge/Meeting%20Types-14-red.svg)]()

## Quick Start

### 🚀 Download & Setup
```bash
# Clone repository
git clone https://github.com/FKIRSTE/acl2025-mimic-to-get-fame.git
cd acl2025-mimic-to-get-fame/fame_dataset
```

### 📊 Load Data
```python
import pandas as pd
import glob

# Load all English meetings
en_files = glob.glob('English/*.csv')
meetings_en = pd.concat([pd.read_csv(f) for f in en_files])

# Load all German meetings
de_files = glob.glob('German/*.csv')
meetings_de = pd.concat([pd.read_csv(f) for f in de_files])

print(f"English meetings: {len(meetings_en)}")
print(f"German meetings: {len(meetings_de)}")
```

## Overview

The **FAME Dataset** addresses the scarcity of meeting data for research in meeting summarization and conversational AI. All 800 meeting transcripts are synthetically generated using the MIMIC framework, ensuring no privacy concerns while providing realistic conversational patterns.

<!-- ### Dataset Statistics

| Metric | English | German | Total |
|--------|---------|---------|-------|
| **Meetings** | 500 | 300 | 800 |
| **Participants** | 2,000+ | 1,200+ | 3,200+ |
| **Meeting Types** | 14 | 14 | 14 |
| **Topic Domains** | 28 | 28 | 28 |
| **Avg Duration** | 22 min | 21 min | 21.6 min | -->

## Dataset Structure

```
fame_dataset/
├── English/                        # English meeting transcripts
│   ├── Brainstorming_Session_Anthropology_English_Biological_Anthropology.csv
│   ├── Brainstorming_Session_Arts_and_Literature_English_Ballet.csv
│   ├── Brainstorming_Session_Complex_Systems_English_Agent-Based_Modeling.csv
│   └── ... (497 more files)
├── German/                         # German meeting transcripts
│   ├── Brainstorming_Session_Anthropology_German_Biological_Anthropology.csv
│   └── ... (297 more files)
├── schema/
│   └── meeting_schema.json         # CSV column specifications
├── README.md                       # This file
└── metadata.yaml                  # Dataset metadata
```

## Data Fields

Each CSV file contains the following columns:

- **Title**: Meeting topic/title
- **Article**: Background article or context
- **Tags**: Comma-separated topic tags
- **Personas**: Comma-separated participant personas
- **Summary**: Human-written meeting summary
- **Meeting_Plan**: Planned agenda or structure
- **Meeting**: Full transcript with speaker labels

## Data Generation Process

1. **Pre-production**: Topic extraction from Wikipedia articles
2. **Casting**: Psychological profiling of participants
3. **Production**: Multi-agent conversation generation
4. **Post-production**: Quality assurance and inclusion of special effects


## Citation

If you use this dataset, please cite our ACL 2025 paper:

```bibtex
@inproceedings{kirstein2025mimic,
  title={You need to MIMIC to get FAME: Solving Meeting Transcript Scarcity with Multi-Agent Conversations},
  author={Kirstein, Frederic and Khan, Muneeb and Wahle, Jan Philip and Ruas, Terry and Gipp, Bela},
  booktitle={Findings of the Association for Computational Linguistics: ACL 2025},
  pages={11482--11525},
  year={2025},
  address={Vienna, Austria},
  publisher={Association for Computational Linguistics}
}
```

## Support & Updates

### Getting Help
1. **Issues**: Open a GitHub issue for technical problems
2. **Questions**: Email kirstein@gipplab.org
3. **Community**: Join discussions in GitHub Discussions

### Future Updates
- **Version 0.9**: ACL 2025 pre-release

### Current Version: 0.9
- Release Date: 2025-07-28
- Changes: Initial public release

---

**Need more help?** Contact us at kirstein@gipplab.org or open an issue on GitHub.
