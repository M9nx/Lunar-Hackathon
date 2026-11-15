# Release reproduction from the candidate revision

Revision `f534f8c-dirty`, code digest `8c819792f2b36135dfde5aeac0b5fdb7abacae161fe81b79f9a83b47cbd02434`. 24/24 steps passed in 163 s.
Browser checks: run. Saved inputs from `/home/m9nx/Lunar-Hackathon/data/horizons`.

| Step | Result | Command | Detail |
| --- | --- | --- | --- |
| source HEAD matches the manifest | pass | `` | f534f8c9447b vs f534f8c9447b |
| overlay applied | pass | `git clone + overlay` | 274 changed/untracked files copied, 0 deletions |
| saved Horizons inputs copied | pass | `` | /home/m9nx/Lunar-Hackathon/data/horizons |
| every manifest file matches in the copy | pass | `sha256 of each file in docs/release/manifest.json` | 216/216 files match |
| copy reports the manifest revision and code digest | pass | `python3 builder/scripts/record_revision.py` | f534f8c-dirty 8c819792f2b36135dfde5aeac0b5fdb7abacae161fe81b79f9a83b47cbd02434 vs f534f8c-dirty 8c819792f2b36135dfde5aeac0b5fdb7abacae161fe81b79f9a83b47cbd02434 |
| copy imports its own engine | pass | `` | /tmp/lunar-release-4s575mpb/candidate/src/lunar_navigator/__init__.py |
| input files (Manual 4.1) | pass | `python3 lunar_offline_pack.py check-horizons` | rc=0  OK    721 rows  /tmp/lunar-release-4s575mpb/candidate/data/horizons/site04-p02-practice-30d/earth-67a08fde71c1/angles.csv /  OK    721 rows  /tmp/lunar-re |
| scenario fit site04_p02_practice (Manual 4.2) | pass | `python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/site04_p02_practice_scenario.json` | rc=0 site=site04-p02-practice pass=True |
| scenario fit malapert_practice (Manual 4.2) | pass | `python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/malapert_practice_scenario.json` | rc=0 site=malapert-practice pass=True |
| scenario fit site04_p02_practice_30d (Manual 4.2) | pass | `python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/site04_p02_practice_30d_scenario.json` | rc=0 site=site04-p02-practice-30d pass=True |
| scenario fit malapert_practice_30d (Manual 4.2) | pass | `python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/malapert_practice_30d_scenario.json` | rc=0 site=malapert-practice-30d pass=True |
| raw digest provenance (Manual 4.3) | pass | `python3 builder/scripts/horizons_digest_check.py --check` | rc=0 raw_mismatch_vs_appendix_b=4/4 provenance_broken=0 |
| package --pair practice-48h (Manual 6) | pass | `python3 -m lunar_navigator.cli --revision f534f8c-dirty package --pair practice-48h --out <temp>` | rc=0 run_id_b=malapert-practice-q4-centre-0deg-88b9b3cfef57 / package=/tmp/lunar-release-4s575mpb/fresh-practice-48h |
| practice-48h package equals the saved package (ignoring code_revision) | pass | `` | all JSON files equal |
| package --pair practice-30d (Manual 6) | pass | `python3 -m lunar_navigator.cli --revision f534f8c-dirty package --pair practice-30d --out <temp>` | rc=0 run_id_b=malapert-practice-30d-q4-centre-0deg-2ee148c7ee51 / package=/tmp/lunar-release-4s575mpb/fresh-practice-30d |
| practice-30d package equals the saved package (ignoring code_revision) | pass | `` | all JSON files equal |
| test suite | pass | `.venv/bin/python -m pytest tests -q -p no:cacheprovider` | rc=0 ................................................................         [100%] / 136 passed in 6.87s |
| notebook trace | pass | `python3 builder/scripts/run_notebook.py --check docs/notebooks/01_trace_observation_to_interval_total.ipynb` | rc=0 executed 7 code cells OK (not written) |
| release manifest check | pass | `python3 builder/scripts/make_release_manifest.py --check` | rc=0 manifest matches disk (216 files) |
| guide walk (User Guide quick start, literal command) | pass | `/home/m9nx/Lunar-Hackathon/.venv/bin/python builder/scripts/s3_guide_walk.py --evidence-dir /home/m9nx/Lunar-H` | rc=0 PASS step 6: clicking a window selects it :: 2 / 8/8 guide-walk checks passed |
| live stream trace | pass | `/home/m9nx/Lunar-Hackathon/.venv/bin/python builder/scripts/live_stream_trace.py --out /home/m9nx/Lunar-Hackat` | rc=0 PASS restart is a new comparison id / 28 passed, 0 failed |
| browser check | pass | `/home/m9nx/Lunar-Hackathon/.venv/bin/python builder/scripts/review_candidate_browser_check.py --base http://12` | rc=0 PASS 390 px QA fixture: no overflow, Unknown span selectable :: {'cw': 375, 'sw': 375, 'utc': '2024-06-01T00:15:00Z'} / 139 passed, 0 failed |
| flow check | pass | `/home/m9nx/Lunar-Hackathon/.venv/bin/python builder/scripts/s2_flow_check.py --base http://127.0.0.1:44167/rev` | rc=0 PASS live run: decision verdict matches the saved case (Yes, both sites) :: Yes. Both sites have a Sun-centre clearance window. / 39 passed, 0 failed |
| web/replay identical in source and copy | pass | `` | bf0ad7f906324f9039547d5740f649d66ef90d4bf6c776710afa333332c45e4a |
