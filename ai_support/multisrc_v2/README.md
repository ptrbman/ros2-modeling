# multisrc_v2 minimal handoff bundle

This folder is a minimal, self-contained bundle for running experiments with `multisrc_v2.xml`.

## Included files

- `multisrc_v2.xml`: current v2 template (with AggregateSubscriber and AggregateTimer)
- `generate_xml_multisrc_v2.py`: JSON -> XML instantiator
- `instantiate.sh`: convenience wrapper that pins `UPPAAL_TEMPLATE_PATH` to local `multisrc_v2.xml`
- `spec_validation_ss_v2_aggregate.json`
- `spec_validation_st_v2_aggregate.json`
- `spec_validation_ts_v2_aggregate.json`
- `spec_validation_tt_v2_aggregate.json`

## Quick use

From this folder:

```bash
chmod +x instantiate.sh
./instantiate.sh spec_validation_ss_v2_aggregate.json validation_ss_v2_from_json.xml
```

Repeat for `st`, `ts`, `tt`.

## Optional: quick MRT check (if verifyta is available)

```bash
/path/to/verifyta --query-index 3 validation_ss_v2_from_json.xml
/path/to/verifyta --query-index 3 validation_st_v2_from_json.xml
/path/to/verifyta --query-index 3 validation_ts_v2_from_json.xml
/path/to/verifyta --query-index 3 validation_tt_v2_from_json.xml
```

In this template, query index `3` is:

- `sup{monitor.measure}: monitor.x[lm]`

## Notes

- The JSON specs include aggregate subscriber/timer patterns used to match the validation originals.
- The generator supports:
  - subscriber aggregates via `src`, `data_source`, `subprocesses`
  - timer aggregates via `src`, `data_source`, `subprocesses`
- If your environment uses a different Python command, replace `python3` in `instantiate.sh`.
