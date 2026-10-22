# Reference Transcription — "The Mysterious Letter"

**Source images:** `mysterious-letter_page-1.jpeg`, `mysterious-letter_page-2.jpeg`
**Transcribed by:** manual human review (ground truth for prototype evaluation)
**Date:** 2026-10-22

> This is the **gold reference** used to measure handwriting-pipeline accuracy.
> Rules applied while transcribing:
> - Student spelling/grammar/punctuation errors are **preserved exactly** (never corrected).
> - Crossed-out text is captured with `~~strikethrough~~` and **excluded** from the active composition / word count.
> - Illegible or ambiguous passages are marked `[?: best-guess]`.
> - Printed material (task + story intro) is recorded separately and is **not** student-authored.

---

## Printed material (NOT student writing — context only)

**Header:** WRITING A STORY

**Instruction:** Continue the story in 150–180 words, making your story creative, logical, and detailed, with correct grammar and punctuation.

**Title:** The Mysterious Letter

**Printed intro:** One rainy afternoon, Emma finds a mysterious letter with her name on it, warning her not to go home and asking her to visit an old house before sunset. Just as she wonders who sent the letter and why, her phone rings from an unknown number.

---

## Student composition — ACTIVE text (errors preserved)

### Page 1
She answered the phone after the ~~fifth~~ third ring. She put the phone to her ear and waited for the person to say something. There was no voice coming from the call, ~~only static~~ the only thing she could hear was ~~a~~ heavy breathing. As she went to end the call she heard a loud scream which starteld her, the scream sounded close by, almost like it was behind her. The voice that came ~~out of~~ after the scream was the voice of her mom. telling her to come home. She quickly ended the call and looked around her, it was almost sunset and the rain hadn't stopped pouring. She had two choices, ~~to~~ she could go home and act like she never saw the letter or she could ~~[?: tisen]~~ go to the old house and see if there is anyone ~~[?: explanation]~~ there who could explain the wierd things that are happening. She checked the time, it read 6 PM, she had about 30 minutes ~~to check the~~ before the ~~suns~~ sunset. Emma decided to go check out her house, even tho the call scared her she thought it would be best to not make her mom mad. On ~~the~~ walk home she kept replaying the call on her head, the longer she kept thinking about it

### Page 2 (continuation of the same sentence)
the ~~more~~ wierder the call got. Why did her mom call her and then not say anything? Why ~~dit~~ wds there a scream? Was her mom watching TV or maybe she was ~~heart~~? Why was her moms raspy? Maybe she got sick. As she got closer to her house ~~the rain had stopped it~~ things started to feel wierd. Her neighbour ~~[?: scribbled words]~~ who owns a flower shop and grows beautiful flowers in her ~~k~~ garden usually ~~is~~ stands outside in the rain trying to protect her garden from the wind. ~~Today she~~ even tho ~~the rain is poor~~ its ~~rainy~~ raining ~~and her flowes look like they are holding on for dear life so the wind doesn't ruin them~~ her neighbour hasn't stepped outside. ~~Nobody~~ Looks like nobody is home. When she sees her house in the distance. she noticed two 7feet men in ~~[?: scribble]~~

---

## Notable features the pipeline must handle

| Feature | Example in sample |
|---|---|
| Printed vs handwritten separation | Printed intro ends "...unknown number." then handwriting begins mid-line "She answered..." |
| Single-stroke word deletions | ~~fifth~~, ~~to~~, ~~dit~~, ~~is~~ |
| Multi-word / multi-line deletions | ~~and her flowes look like they are holding on for dear life...~~ |
| Heavy scribble-outs (undetermined content) | neighbour line on p.2, final word on p.2 |
| Insertions / replacements | "~~only static~~ the only thing", "~~out of~~ after" |
| Preserved spelling errors | wierd, tho, starteld, wds, moms (missing apostrophe), flowes, neighbour (UK sp.) |
| Sentence continues across page break | p.1 "...thinking about it" → p.2 "the wierder the call got" |
| Incomplete ending | p.2 ends abruptly "...two 7feet men in" |

## Approximate active word count
~250 words active (over the 150–180 target). **Exact count is a prototype deliverable** — to be computed by deterministic word-count logic after crossed-out text is removed, then compared to this reference.
