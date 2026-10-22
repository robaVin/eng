# Test Data

Real, anonymized handwriting samples used to validate the document-recognition and
handwriting-transcription pipelines **before** building the full application.

## Contents

```
test-data/
  handwriting-samples/
    mysterious-letter_page-1.jpeg   # printed task + story intro + start of handwritten answer
    mysterious-letter_page-2.jpeg   # continuation of the composition (same response, page 2)
    reference-transcription.md      # manually verified ground truth (errors preserved)
```

## Provenance

These are the two reference photographs described in the project brief ("The Mysterious Letter"
writing task). They were located in the user's Downloads folder and copied here on 2026-10-22.

## If the images are missing

If you clone this repo on another machine and the `.jpeg` files are absent, the handwriting
feasibility prototype will report the missing files and exit without fabricating results.
To restore them, place the two photographs at the exact paths above. Any two photos of a
single multi-page handwritten composition (page 1 containing the printed task) will work for
a smoke test, but accuracy numbers are only meaningful against a matching
`reference-transcription.md`.

> ⚠️ Treat all student work as sensitive data. Do not commit additional real student
> submissions to version control. These two samples are retained deliberately as fixtures.
