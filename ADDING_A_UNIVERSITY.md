# Adding a university

Each university is one small file in `src/universities/`. The app's dropdown, the
model prompt and the PDF all read from the selected profile, so nothing else needs to
change.

## What a profile holds

| Field | What it is | Where it comes from |
|---|---|---|
| `name`, `short`, `issued_by` | Dropdown label, heading text, closing note | the university |
| `rubric` | Criteria and weights, used only if the uploaded guidelines have no readable rubric | the guidelines |
| `scale` | Grading bands (label, min, max, meaning) | the guidelines / marking sheet |
| `pass_mark`, `scale_name` | Pass threshold and scale name in the heading | the guidelines |
| `header_image`, `footer_image` | Full-width page letterhead and footer (PNG) | the sample report |
| `calibration` | Optional worked example of how this university marks (levels and total) | a marked thesis |
| `strict_integrity` | `True` if integrity failures cap marks and force a fail (EIU does). `False` lists findings but changes no marks | the guidelines |

## Steps

1. Copy `src/universities/eiu.py` to `src/universities/<key>.py` (for example `azteca.py`,
   `lincoln.py`, `paiu.py`).
2. Fill in the fields above from the university's guidelines and its sample feedback report.
3. Put the letterhead images in `assets/` (any file name) and point `header_image` /
   `footer_image` at them. Heights are taken from the image proportions.
4. Register it in `src/universities/__init__.py`: import the module and add
   `<module>.PROFILE` to the tuple that builds `UNIVERSITIES`.
5. Run `python tests/test_marking_rules.py` and generate a sample report to compare with the
   university's own.

## Calibrating the marks

EIU's marks were tuned against one marked thesis (university 44%, agent 45%). For a new
university, get at least one thesis that the university has already marked, run it, and
compare criterion by criterion. Put the university's own marks in `calibration` so the model
sees how that university grades. Marks stay indicative until an examiner confirms them.

## Layout differences

The report layout (student details, weighted marks, integrity findings, criterion feedback,
fix list, grading scale) is shared. If a university needs a different layout, send the sample
report and the PDF builder (`src/feedback_pdf.py`) can be given a layout option per profile.
