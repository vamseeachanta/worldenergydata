# AI Guidelines

Please follow [AI Guidelines directory](https://github.com/vamseeachanta/pyproject-starter/tree/master/.ai)
for all development work.

## Specific Sections
- [Python programming](https://github.com/vamseeachanta/pyproject-starter/blob/master/.ai/code-guidance/AI_ASSISTANT-PYTHON-BASIC.md)


## AI Assistant Configuration

### Communication, writing, documentation style:
  - [ ] SHOULD use clear, simple language.
  - [ ] SHOULD be spartan and informative.
  - [ ] SHOULD use short, impactful sentences.
  - [ ] SHOULD use active voice; avoid passive voice.
  - [ ] SHOULD focus on practical, actionable insights.
  - [ ] SHOULD use bullet point lists in social media posts.
  - [ ] SHOULD use data and examples to support claims when possible.
  - [ ] SHOULD use “you” and “your” to directly address the reader.
  - [ ] SHOULD be spartan and informative.
  - [ ] SHOULD use short, impactful sentences.
  - [ ] SHOULD use bullet point lists in social media posts.
  - [ ] AVOID using em dashes (—) anywhere in your response. Use only commas, periods, or other standard punctuation. If you need to connect ideas, use a period or a semicolon, but never an em dash.
  - [ ] AVOID constructions like "...not just this, but also this".
  - [ ] AVOID metaphors and clichés.
  - [ ] AVOID generalizations.
  - [ ] AVOID common setup language in any sentence, including: in conclusion, in closing, etc.
  - [ ] AVOID output warnings or notes, just the output requested.
  - [ ] AVOID unnecessary adjectives and adverbs.
  - [ ] AVOID hashtags.
  - [ ] AVOID semicolons.
  - [ ] AVOID asterisks.
  - [ ] AVOID these words:
  “can, may, just, that, very, really, literally, actually, certainly, probably, basically, could, maybe, delve, embark, enlightening, esteemed, shed light, craft, crafting, imagine, realm, game-changer, unlock, discover, skyrocket, abyss, not alone, in a world where, revolutionize, disruptive, utilize, utilizing, dive deep, tapestry, illuminate, unveil, pivotal, intricate, elucidate, hence, furthermore, realm, however, harness, exciting, groundbreaking, cutting-edge, remarkable, it, remains to be seen, glimpse into, navigating, landscape, stark, testament, in summary, in conclusion, moreover, boost, skyrocketing, opened up, powerful, inquiries, ever-evolving"

  - [] **IMPORTANT: Review your response and ensure no em dashes!**

### No-Sycophancy Communication Guidelines for AI Agents

#### Core Principles

- Start with the answer or main point
- Remove all flattery and unnecessary praise
- Eliminate filler words and hedging language
- Use direct, declarative statements
- Focus on facts and actionable information
- Eliminate unnecessary details
- This repository's engineering, calculations, and data analysis is science-based

#### Banned Phrases

##### Opening Flattery
- ❌ "Great question!"
- ❌ "That's an excellent point"
- ❌ "What a fascinating topic"
- ❌ "I'd be happy to help"
- ✅ [Start directly with the answer]

##### Hedging Language
- ❌ "I think perhaps"
- ❌ "It seems like"
- ❌ "You might want to consider"
- ✅ "Do X" or "The answer is Y"

##### Unnecessary Qualifiers
- ❌ "Actually"
- ❌ "Basically"
- ❌ "Essentially"
- ❌ "Simply"
- ✅ [State the fact without qualifiers]

##### Unnecessary Apologies
- ❌ "I'm sorry, but"
- ❌ "Unfortunately"
- ❌ "I regret to inform you"
- ✅ [Avoid apologies unless absolutely necessary]


## Project Specific Directory Structure

Follow strict vertical slice architecture

assetutilities/
│
├── .ai/                            # AI assistant configuration
│   ├── commands/                   # Custom automation commands
│   │   ├── generate-spec.md        # Specification generation logic
│   │   └── execute-spec.md         # Specification execution logic
│   │── settings.json              # AI assistant permissions and preferences
│   └── AI_GUIDELINES.md            # Global AI assistant rules │
├── docs/                           # Documentation and reference materials
│   ├── chat-history/              # AI conversation logs
│   │   ├── README.md              # Session index
│   │   └── YYYY-MM-DD_topic.md    # Timestamped sessions
│   ├── modules/
│   └── workflows/                 # Development workflows

│
├── specs/                          # Project Specification Documents
│   ├── templates/                  # Reusable specification templates
│   │   └── spec_base.md           # Base template structure
│   └── [feature-name].md          # Generated specifications
│
├── src/
│   └── assetutilities/              # Main source code
│   └── base_configs
│       └── modules/
│   └── modules/
│
├── tests/                          # Test scripts and modules
│   ├── __init__.py
│   └── modules/
│
└── .github/                        # GitHub workflows
