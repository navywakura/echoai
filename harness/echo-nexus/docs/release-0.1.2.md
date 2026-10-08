# echo-nexus 0.1.2

Make development progress and the selected ECHO backend visible, with streamed
chat responses and real screenshots on the website.

- `/agent` selects engine profiles independently of saved language-model connections.
  The backend manifest is reloaded before each development run.
- A persistent sidebar counts processes, cases, solved cases, steps, levels and
  resets when the backend reports them. The activity line records the stop reason.
- `/cell X Y`, coordinate labels, an actor arrow and compass display optional
  observer metadata. This is a viewer overlay and is never sent to the engine.
- Chat shows request phases, elapsed time and public response text as it arrives.
  `/why` presents received observations, recorded criteria, actions and outcomes.
  Missing explanations remain missing; hidden model reasoning is not displayed.
- Interrupted streams fail explicitly. Reasoning and tool-call fields do not enter
  displayed answers or chat history. Cancellation stops the activity indicator.
- Custom Open Graph, thumbnail and actual TUI captures; guides in ES/EN/CA.

Validation: 18 harness tests, including connection persistence, streaming,
cancellation, profile selection and observer overlays. A private development
adapter also exercised a custom navigation world, public ARC training tasks,
ARC3-GYM and archived official ARC-1/2/3 replays. The custom world reached its goal
in 56 steps without a reset. Three gym scenarios exhausted 600 steps each without
solving a scenario. These are development observations, not new ARC scores or S6
certification. Archived ARC-3 replay frames were checked against saved hashes.

The open package contains only the harness. Engine profiles, custom laboratory
worlds, private adapters, weights, credentials and research evidence are not
included. Live updates require a backend that starts the current installed engine;
updating the harness alone does not upgrade ECHO's capabilities.
