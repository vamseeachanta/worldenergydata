# Public-source provenance completeness

For public data curation, verified file digests shall not substitute for source
completeness. Offline reuse shall reject a retained failure/refusal disposition
and shall verify the complete, unique expected set of data and documentation
files before generating a successful snapshot. Each source identity and its
saved bytes shall match the manifest. Successful downloads preceding a later
failure shall retain provenance, with the failure explicitly recorded.

Basis: the borehole-status review for
[issue 960](https://github.com/vamseeachanta/worldenergydata/issues/960) found that
a valid ZIP digest alone could hide a later documentation-download refusal.
Regression coverage: `tests/unit/bsee/data/test_borehole_status_cli.py`.
