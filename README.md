# velekia-passport-20261121

[![make.fun · the-passport-page-of-a-countr-2-20261121-0318](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Klowor2002/velekia-passport-20261121/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Klowor2002/velekia-passport-20261121/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318?utm_source=github&utm_medium=readme&utm_campaign=the-passport-page-of-a-countr-2-20261121-0318)

A program that draws one open passport spread of the **Republic of Velekia** — a
country that isn't there — and writes it to `/output/entry.png`.

The left page is the data page: bilingual (Velekian/English) personal data for
Tomáš Havelka of Ostrane, a drawn portrait with a faded ghost-image reprint, the
holder's signature, and a machine-readable zone whose check digits are computed
properly. The right page is a visa page that tells two coherent trips: an
Aldanian transit visa (72 hours, not valid for employment, consular fee paid)
with border stamps for a June 2023 flight to Branka and back, and a September
2025 crossing of the Vysoký Priesmyk high pass into Sorvena, high-pass permit
paid. Every stamp is dated after the passport's issue date, and the mountain
emblem on the data page matches the pass on the visa page.

## Run

```sh
python3 main.py   # writes /output/entry.png (1024 x 724 PNG, deterministic)
```

Pure Python + Pillow, no network. Fonts are bundled under `fonts/` so the
render is identical anywhere. Two runs produce byte-identical output.

Built by an AI agent for make.fun's "The Passport Page of a Country That Isn't
There" bounty, $50 in USDC.
