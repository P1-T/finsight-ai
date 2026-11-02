# Intent routing and response templates

## What is registered

`backend/app/intent_catalog.py` is the single source of truth for 100 intent patterns. Every entry contains a stable identifier, a reusable response schema, an intent group, one canonical example prompt, phrase cues, and keywords. Representative examples include:

- **Company and competition:** “Explain the business model and main revenue streams”; “Does the company have a durable competitive moat?”
- **Financial performance:** “How fast is revenue growing year over year?”; “Are gross margins expanding or shrinking?”; “How strong is free cash flow?”
- **Valuation and returns:** “What is intrinsic value?”; “How does its P/E compare with peers?”; “Is the dividend sustainable?”
- **Balance sheet and risk:** “Can the company cover near-term obligations?”; “How volatile has the stock been?”; “What could tariffs mean for the company?”
- **Technicals:** “Is it in an uptrend or downtrend?”; “Is RSI overbought?”; “Is volume confirming the breakout?”; “Where are support and resistance areas?”
- **Macro and sectors:** “How could Fed policy affect the company?”; “Is the business defensive or cyclical?”; “How is the company positioned in the AI industry?”
- **Events and market expectations:** “How did the latest quarter perform?”; “What should I watch in upcoming earnings?”; “Why did the stock move after the announcement?”
- **Positioning and derivatives:** analyst revisions, insider transactions, institutional ownership, short interest, and options positioning.

The registry covers exactly 100 patterns. Each pattern maps into a smaller set of response layouts already supported by the API and frontend, such as `company_analysis`, `quarterly_performance`, `technical_analysis`, `valuation_analysis`, `risk_analysis`, `sector_analysis`, `news_analysis`, and `stock_comparison`. Intent patterns guide answer focus; response layouts choose stable typed data blocks. Adding an intent usually requires only a catalog entry and, when needed, a focused synthesis instruction—not a new React component.

## Routing algorithm

1. **Capture the current question and context.** Resolve company candidates from the current turn. Add recent conversation text only when the current message is a context-dependent follow-up.
2. **Score all registered intents.** A boundary-aware phrase match is worth 4–6 points. Keyword overlap uses inverse document frequency so distinctive terms count more than generic terms, normalized by template size. Context phrase and keyword evidence contributes 25% of its direct-prompt score.
3. **Apply structural company evidence.** A company-comparison intent receives a 3-point boost when two or more companies resolve. It receives a 2-point penalty when only one company resolves. A single-company benchmark comparison remains valid.
4. **Send a bounded candidate list to Claude.** The planner receives the top eight candidates, canonical examples, and tool constraints. It must return a valid candidate ID in the strict `ResearchPlan` schema. It cannot supply executable instructions or arbitrary response component names.
5. **Reconcile the model choice.** A valid Claude candidate contributes at most 1.6 points to the score. Explicit phrase and entity evidence can therefore beat an unrelated model preference. Structural checks then preserve a validated template if, for example, a requested comparison lacks a second resolved company.
6. **Execute only the required providers.** The selected template determines the bounded market-data, web, and news requests. Existing provider result and failure handling remains independent by source.
7. **Synthesize and compose.** Claude produces the answer from retrieved evidence, and the backend validates it before composing the corresponding typed response blocks. Mock values remain a UI-demo fallback and must not be represented as fetched facts.

## Confidence and fallback behavior

`intent_confidence` is calculated from two signals: the selected intent's evidence score and its score margin over the runner-up. It describes routing confidence only; it is not a measure of factual accuracy, future performance, or investment confidence. If no catalog cue matches, the planner receives generic company/market candidates. If Claude is unavailable, deterministic ranking chooses a fallback intent. If a company cannot be resolved, the workflow asks for a ticker/name clarification rather than running tools on a guessed company.

## Extension rules

- Add a catalog row with a specific example, discriminative phrase cues, keywords, and an existing response layout.
- Add a new response schema only when the information architecture genuinely differs; avoid one layout per prompt wording.
- Keep provider selection and company validation server-side.
- Do not let mock fixture values support factual narrative claims or citations.
- Keep stable intent IDs because response payloads and diagnostics expose the selected ID.
