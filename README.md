# English to IPA

A small command-line program that transcribes English text to broad Canadian English IPA.
It looks words up in CMUdict first and predicts pronunciations for missing words with
the `g2p-en` grapheme-to-phoneme model.

## Install

Use Python 3.9 or newer:

```sh
python -m pip install -r requirements.txt
```

The Python packages include the CMU Pronouncing Dictionary data and the G2P model.
The first G2P use may take longer while its model resources initialize.

## Acknowledgments and third-party resources

- **CMU Pronouncing Dictionary (CMUdict):** Maintained by Carnegie Mellon University.
  This project uses it through the `cmudict` Python package for dictionary lookups.
  CMU requests acknowledgment when its dictionary is used or redistributed. See the
  [CMUdict repository and license](https://github.com/cmusphinx/cmudict).
- **g2p-en:** Grapheme-to-phoneme model by Kyubyong Park and Jongseok Kim, distributed
  under the Apache License 2.0. See the [upstream project](https://github.com/Kyubyong/g2p)
  and [PyPI package metadata](https://pypi.org/project/g2p-en/).

These are third-party dependencies installed from PyPI; their source and model files are
not copied into this repository. Each dependency remains under its own license.

## Use

```sh
python3 transcribe.py "The quick brown fox jumps over the lazy dog."
echo "A word that may not be in the dictionary" | python transcribe.py
python3 transcribe.py --sources "hello qzxyword"
python3 transcribe.py --epenthetic-t "sense and essence"
```

`--sources` labels each word with `dictionary` or `g2p` so predictions are easy to spot.

The output is enclosed in `[` and `]`. It marks estimated syllable boundaries with `.`;
commas, semicolons, and colons become minor phrase boundaries (`|`), while sentence
punctuation and blank lines become major phrase boundaries (`‖`).

## Pronunciation choices and limits

There is no single dialect-free pronunciation of English. This tool uses a broad,
rhotic North American target intended to be a practical Canadian English approximation.
CMUdict is a large General American lexicon, not a Canadian English dictionary, and
`g2p-en` is trained to predict pronunciations in the same ARPAbet-style North American
convention. Canadian pronunciations overlap substantially, but differ by speaker and
region (including vowel mergers and raising). The program does not model those differences
or sentence-level reductions, and alternate dictionary pronunciations are not selectable
yet. Treat unknown-word output as a plausible prediction, not an authoritative pronunciation.

IPA output is broad phonemic transcription with primary and secondary stress marks.
Unstressed `AH` is rendered as schwa, and English `R` is rendered as the North American
approximant /ɹ/.
Diphthongs use a non-syllabic mark: /aɪ̯, aʊ̯, ɔɪ̯, əɪ̯, oʊ̯/.

## Added phonetic rules

The transcription applies the requested broad allophonic rules to the ARPAbet sequence:

- /p t k/ are aspirated at word onset and before an indicated stressed vowel, except after /s/.
- Approximants immediately after an aspirated onset are marked voiceless.
- Word-final stops are marked unreleased, including phrase-final stops.
- /l/ is clear before a following vowel and dark /ɫ/ elsewhere.
- /t, d/ become /ɾ/ between vowels before an unstressed vowel. In that same environment,
  /n/ and /nt, nd/ become the nasalized flap /ɾ̃/.
- Alveolars before /θ, ð/ receive dentalization.
- Vowels before /m, n, ŋ/ are nasalized; for diphthongs the tilde is placed on the second vowel symbol.
- Stressed /aɪ, aʊ/ before a voiceless consonant are raised to /ʌɪ̯, ʌʊ̯/.

Syllable boundaries are estimated from the phones using a longest-legal-onset heuristic;
they are not supplied by the dictionary/model, so these markers are useful guides rather
than guaranteed syllabifications. Phrase boundaries are inferred from punctuation. The
other phonetic rules use the phones and stress supplied by the dictionary/model. The
program inserts [ʔ] between adjacent vowel nuclei
and before vowel-initial words by default. It does not model syllable-level prosody. The
suggested word-final `-nce/-nse` epenthetic [t] remains optional and is enabled with
`--epenthetic-t`; it inserts [t] before final /s/ in words spelled with those endings.
These are spelling/context heuristics and may need exceptions for particular words or
speaking styles.
