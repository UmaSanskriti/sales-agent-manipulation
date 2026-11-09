# Saved conversation traces and activation replay

Anthony's stated handoff request is the full conversations. The existing JSONL files contain the complete customer-visible dialogue, not just isolated agent answers.

## What is saved

Each file starts with a metadata record identifying the conversation, scenario, persona, objective condition, model names/settings, seed, prompt hashes, protocol, actual agent-turn count, stopping reason, and customer decision. Subsequent records contain `role` (`customer` or `agent`), `content`, and `turn`. The terminal customer closing message is retained. The scenario inventories and versioned prompt code supply the agent system prompt, and the run manifests identify source revisions/input hashes.

The files do **not** contain the original target reasoning-channel text, generation-time activations, exact prompt/response token IDs, or a raw copy of the tokenized model input. New generation runs also store the complete agent system prompt in metadata as `agent_system_prompt`; the earlier pilot files have only its hash. A hash verifies a known prompt but cannot reconstruct one: retain the matching source revision and scenario inventory for older files. Customer prompt versions also differ between the original pilot and the consistency check.

## How full conversations can be used for extraction

1. Load the same open-weight model and tokenizer on suitable hardware, with model weights fixed.
2. For an agent turn, reconstruct its system prompt and preceding dialogue. Map saved customer messages to `user` and agent messages to `assistant`. Include only messages available at that turn, not later dialogue or the terminal customer remark.
3. Apply a documented chat template/channel format to that prefix and the already-recorded agent reply. Feed this fixed sequence through the model in a forward pass with hidden states enabled. No new reply needs to be sampled; this is commonly called teacher forcing.
4. Read the hidden-state vectors at the chosen prompt/response positions and layers. Train the probe on those replay vectors using the corresponding behavioral labels and grouped splits.

This produces legitimate **replay activations for the selected tokenization and context**. It is not guaranteed to reproduce the activations from original generation. In particular, gpt-oss generated hidden reasoning before the visible answer, and replaying only the visible transcript omits that conditioning. Whitespace normalization, template versions and channel delimiters also matter.

## Difference from the original TRD

TRD M1/M8 proposes replay over exact stored prompt/response token IDs, including the original analysis channel, and a `cot_last` probe position. Visible conversation files alone cannot implement that exact protocol or recover the missing original reasoning. Anthony can choose visible-text replay and document that protocol; if the team keeps exact reasoning-aware extraction, generation must additionally save those records.

There is currently no extraction entry point in this repository, so this document explains the options and saved format rather than claiming Anthony's implementation has been tested. The original pilot conversation files have not been modified.
